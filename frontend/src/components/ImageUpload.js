import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Upload, X, Loader2 } from 'lucide-react';
import { Button } from './ui/button';

const API = process.env.REACT_APP_BACKEND_URL;

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
const MAX_FILE_BYTES = 8 * 1024 * 1024; // 8MB per image

/**
 * Image uploader that talks to the existing /api/upload/image endpoint.
 *
 * MODES
 * -----
 * Default (stageBeforeUpload=false):
 *   File picker → immediate upload → onUpload(url|urls). Preserved for
 *   simple one-shot cases (banner, community post, etc).
 *
 * stageBeforeUpload=true:
 *   File picker → previews rendered from URL.createObjectURL(), each
 *   removable → the brand clicks "Upload N" to actually POST. Lets a
 *   brand pick 5 photos on their phone, drop the 2 they don't want, and
 *   only spend bandwidth on the 3 they keep. Matches the mobile UX brands
 *   expect from Shopify/Depop/Vinted.
 *
 * SECURITY / PRIVACY
 * ------------------
 * Uses a native <input type="file" accept="image/*"> — the browser only
 * hands over the files the user picks. We NEVER request permissions like
 * `navigator.mediaDevices` or read arbitrary paths, so we can't see (and
 * therefore can't leak) anything the brand didn't explicitly select.
 */
export default function ImageUpload({
  onUpload,
  multiple = false,
  label = 'Upload Image',
  className = '',
  stageBeforeUpload = false,
  maxImages,               // hard cap for multi-select (e.g. 10 for products)
}) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [staged, setStaged] = useState([]);   // [{ file, previewUrl }]
  const fileInputRef = useRef(null);

  // Release object URLs when a stage is cleared or the component unmounts.
  useEffect(() => {
    return () => {
      staged.forEach((s) => URL.revokeObjectURL(s.previewUrl));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const validate = (file) => {
    if (!ALLOWED_TYPES.includes(file.type)) return 'Only JPEG, PNG, WebP and GIF images are allowed.';
    if (file.size > MAX_FILE_BYTES) return 'Each image must be under 8MB.';
    return null;
  };

  const uploadOne = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${API}/api/upload/image`, formData, {
      withCredentials: true,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data.url;
  };

  // --- Immediate upload mode (legacy) ---
  const handleImmediate = async (files) => {
    setError('');
    setUploading(true);
    try {
      const uploadedUrls = [];
      for (const file of files) {
        const err = validate(file);
        if (err) { setError(err); return; }
        uploadedUrls.push(await uploadOne(file));
      }
      if (onUpload) onUpload(multiple ? uploadedUrls : uploadedUrls[0]);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // --- Staged mode: previews first, upload on confirm ---
  const handleStage = (files) => {
    setError('');
    const additions = [];
    for (const file of files) {
      const err = validate(file);
      if (err) { setError(err); if (fileInputRef.current) fileInputRef.current.value = ''; return; }
      additions.push({ file, previewUrl: URL.createObjectURL(file), id: `${file.name}-${file.size}-${file.lastModified}` });
    }
    // Enforce max cap across the currently-staged batch.
    const combined = [...staged, ...additions];
    if (typeof maxImages === 'number' && combined.length > maxImages) {
      const trimmed = combined.slice(0, maxImages);
      // Release the URLs we're about to throw away.
      combined.slice(maxImages).forEach((s) => URL.revokeObjectURL(s.previewUrl));
      setStaged(trimmed);
      setError(`Only ${maxImages} images allowed — extras were dropped.`);
    } else {
      setStaged(combined);
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeStaged = (id) => {
    setStaged((prev) => {
      const removed = prev.find((s) => s.id === id);
      if (removed) URL.revokeObjectURL(removed.previewUrl);
      return prev.filter((s) => s.id !== id);
    });
  };

  const clearStaged = () => {
    staged.forEach((s) => URL.revokeObjectURL(s.previewUrl));
    setStaged([]);
    setError('');
  };

  const confirmStaged = async () => {
    if (staged.length === 0) return;
    setError('');
    setUploading(true);
    const uploaded = [];
    try {
      for (const s of staged) {
        uploaded.push(await uploadOne(s.file));
      }
      if (onUpload) onUpload(multiple ? uploaded : uploaded[0]);
      clearStaged();
    } catch (err) {
      const detail = err.response?.data?.detail;
      // Surface the exact reason (moderation flag, size, etc) so the brand
      // knows which image to drop, rather than a generic "upload failed".
      setError(typeof detail === 'string' ? detail : 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    if (stageBeforeUpload) {
      handleStage(files);
    } else {
      handleImmediate(files);
    }
  };

  return (
    <div className={className}>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        multiple={multiple}
        onChange={handleFileChange}
        className="hidden"
        data-testid="image-upload-input"
      />

      {/* Staged previews (only in preview-then-confirm mode) */}
      {stageBeforeUpload && staged.length > 0 && (
        <div className="mb-3" data-testid="image-upload-staged">
          <p className="text-xs uppercase tracking-wider text-[#9CA3AF] mb-2">
            {staged.length} photo{staged.length === 1 ? '' : 's'} ready — remove any you don't want, then confirm
          </p>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2 mb-3">
            {staged.map((s) => (
              <div
                key={s.id}
                className="relative aspect-square overflow-hidden border border-white/10 bg-[#0F0F0F] group"
                data-testid={`image-upload-preview-${s.id}`}
              >
                <img src={s.previewUrl} alt={s.file.name} className="w-full h-full object-cover" />
                <button
                  type="button"
                  onClick={() => removeStaged(s.id)}
                  disabled={uploading}
                  className="absolute top-1 right-1 bg-black/80 border border-white/20 text-white p-1 hover:bg-red-500/80 transition-colors"
                  aria-label="Remove"
                  data-testid={`image-upload-remove-${s.id}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              onClick={confirmStaged}
              disabled={uploading}
              className="btn-primary flex-1"
              data-testid="image-upload-confirm"
            >
              {uploading ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Uploading {staged.length}…</>
              ) : (
                <><Upload className="w-4 h-4 mr-2" /> Upload {staged.length} photo{staged.length === 1 ? '' : 's'}</>
              )}
            </Button>
            <Button
              type="button"
              onClick={clearStaged}
              disabled={uploading}
              variant="ghost"
              className="text-[#9CA3AF] hover:text-white border border-white/10 rounded-none"
              data-testid="image-upload-clear"
            >
              Clear
            </Button>
          </div>
        </div>
      )}

      <Button
        type="button"
        variant="outline"
        className="btn-secondary w-full flex items-center justify-center gap-2"
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        data-testid="image-upload-button"
      >
        {uploading && !stageBeforeUpload ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</>
        ) : (
          <><Upload className="w-4 h-4" /> {stageBeforeUpload && staged.length > 0 ? 'Add more from device' : label}</>
        )}
      </Button>

      {error && (
        <p className="text-red-400 text-xs mt-2" data-testid="image-upload-error">{error}</p>
      )}

      <p className="text-[#9CA3AF] text-xs mt-2">
        Choose photos from your device — camera roll or files. JPEG, PNG, WebP or GIF. Max 8MB each.
      </p>
    </div>
  );
}

export function ImagePreview({ src, onRemove, alt = 'Uploaded image' }) {
  const fullSrc = src.startsWith('/api/') ? `${API}${src}` : src;

  return (
    <div className="relative group aspect-square overflow-hidden border border-white/10 bg-[#0F0F0F]">
      <img src={fullSrc} alt={alt} className="w-full h-full object-cover" />
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="absolute top-1 right-1 bg-black/70 text-white p-1 opacity-0 group-hover:opacity-100 transition-opacity"
          data-testid="image-remove-button"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
