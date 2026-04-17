import { useState, useRef } from 'react';
import axios from 'axios';
import { Upload, X, Loader2, ImageIcon } from 'lucide-react';
import { Button } from './ui/button';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ImageUpload({ onUpload, multiple = false, label = 'Upload Image', className = '' }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    setError('');
    setUploading(true);

    try {
      const uploadedUrls = [];
      for (const file of files) {
        // Validate file type
        if (!['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(file.type)) {
          setError('Only JPEG, PNG, WebP and GIF images are allowed.');
          setUploading(false);
          return;
        }
        // Validate file size (5MB)
        if (file.size > 5 * 1024 * 1024) {
          setError('Each image must be under 5MB.');
          setUploading(false);
          return;
        }

        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post(`${API}/api/upload/image`, formData, {
          withCredentials: true,
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        uploadedUrls.push(response.data.url);
      }

      if (onUpload) {
        onUpload(multiple ? uploadedUrls : uploadedUrls[0]);
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
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

      <Button
        type="button"
        variant="outline"
        className="btn-secondary w-full flex items-center justify-center gap-2"
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        data-testid="image-upload-button"
      >
        {uploading ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</>
        ) : (
          <><Upload className="w-4 h-4" /> {label}</>
        )}
      </Button>

      {error && (
        <p className="text-red-400 text-xs mt-2" data-testid="image-upload-error">{error}</p>
      )}

      <p className="text-[#9CA3AF] text-xs mt-2">
        Use clear, well-lit photos. JPEG, PNG, WebP or GIF. Max 5MB each.
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
