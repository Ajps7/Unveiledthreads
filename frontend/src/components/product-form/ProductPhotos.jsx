import { Upload, X } from 'lucide-react';
import ImageUpload from '../ImageUpload';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Image upload + preview grid for the AddProduct form.
 * Pure presentational — the parent owns `images` state.
 */
export function ProductPhotos({ images, onUpload, onRemove }) {
  return (
    <div className="border border-white/10 bg-[#0A0A0A] p-6 mb-6">
      <h2 className="text-lg font-bold text-white uppercase mb-1" style={{ fontFamily: 'Clash Display, sans-serif' }}>
        <Upload className="w-5 h-5 inline mr-2" />
        Photos
      </h2>
      <p className="text-xs text-[#9CA3AF] mb-4">
        Upload clear, well-lit photos on a plain background. First image is the cover. Max 5MB each, JPEG/PNG/WebP.
      </p>

      {images.length > 0 && (
        <div className="grid grid-cols-4 md:grid-cols-6 gap-3 mb-4">
          {images.map((img, i) => (
            <div key={img} className="relative group aspect-square overflow-hidden border border-white/10 bg-[#0F0F0F]">
              <img src={img.startsWith('/api/') ? `${API}${img}` : img} alt={`Product ${i + 1}`} className="w-full h-full object-cover" />
              {i === 0 && (
                <span className="absolute top-1 left-1 bg-[#39FF14] text-black text-[8px] font-bold px-1.5 py-0.5">COVER</span>
              )}
              <button
                type="button"
                onClick={() => onRemove(i)}
                className="absolute top-1 right-1 bg-black/70 text-white p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                data-testid={`remove-image-${i}`}
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      <ImageUpload
        multiple
        label={images.length > 0 ? 'Upload More Photos' : 'Upload Photos'}
        onUpload={onUpload}
      />
    </div>
  );
}
