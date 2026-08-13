import { useState } from 'react';
import { X, Star, ArrowLeft, ArrowRight, GripVertical } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Reorderable image grid for the brand's own product-edit view.
 *
 * The parent owns the images array via `value` / `onChange` — we don't
 * fetch or persist here; the parent's existing Save button hits
 * `PUT /api/products/{id}` with the reordered array.
 *
 * Ordering interactions supported:
 *   - Drag-and-drop (desktop mouse; some laptop touchpads emit these too)
 *   - Explicit "move left / right" arrow buttons on every tile — the
 *     accessible, mobile-safe fallback. Drag-only is unreliable on touch.
 *
 * The first tile is clearly labelled as the cover / hero image with the
 * neon-green (#39FF14) accent already used across the app.
 */
export function ProductImageReorder({ value = [], onChange, allowRemove = true }) {
  const [dragIndex, setDragIndex] = useState(null);
  const [overIndex, setOverIndex] = useState(null);

  const move = (from, to) => {
    if (from === to || from < 0 || to < 0 || from >= value.length || to >= value.length) return;
    const next = value.slice();
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    onChange(next);
  };

  const remove = (i) => {
    if (!allowRemove) return;
    onChange(value.filter((_, idx) => idx !== i));
  };

  const onDragStart = (e, i) => {
    setDragIndex(i);
    // Set required data for Firefox drag to actually fire.
    try { e.dataTransfer.setData('text/plain', String(i)); } catch { /* not fatal */ }
    e.dataTransfer.effectAllowed = 'move';
  };
  const onDragOver = (e, i) => { e.preventDefault(); setOverIndex(i); };
  const onDrop = (e, i) => {
    e.preventDefault();
    if (dragIndex !== null) move(dragIndex, i);
    setDragIndex(null); setOverIndex(null);
  };
  const onDragEnd = () => { setDragIndex(null); setOverIndex(null); };

  if (value.length === 0) return null;

  return (
    <div data-testid="image-reorder">
      <p className="text-xs text-[#9CA3AF] mb-3">
        The first image is your <span className="text-[#39FF14]">cover image</span> — it&apos;s what buyers see first
        in the shop and on cards. Drag to reorder, or use the arrow buttons on each image.
      </p>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
        {value.map((img, i) => {
          const isCover = i === 0;
          const isOver = overIndex === i && dragIndex !== null && dragIndex !== i;
          return (
            <div
              key={img + i}
              draggable
              onDragStart={(e) => onDragStart(e, i)}
              onDragOver={(e) => onDragOver(e, i)}
              onDrop={(e) => onDrop(e, i)}
              onDragEnd={onDragEnd}
              className={`relative aspect-square overflow-hidden bg-[#0F0F0F] cursor-grab active:cursor-grabbing transition-all ${
                isCover
                  ? 'border-2 border-[#39FF14] ring-1 ring-[#39FF14]/30'
                  : isOver
                    ? 'border-2 border-[#39FF14]/60'
                    : 'border border-white/10 hover:border-white/30'
              }`}
              data-testid={`reorder-tile-${i}`}
              aria-label={`Image ${i + 1}${isCover ? ' — cover' : ''}`}
            >
              <img
                src={img.startsWith('/api/') ? `${API}${img}` : img}
                alt={`Image ${i + 1}`}
                className="w-full h-full object-cover pointer-events-none"
                draggable={false}
              />

              {isCover && (
                <span
                  className="absolute top-1 left-1 flex items-center gap-1 bg-[#39FF14] text-black text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wider"
                  data-testid="cover-badge"
                >
                  <Star className="w-2.5 h-2.5" />
                  Cover
                </span>
              )}

              <span className="absolute top-1 right-1 bg-black/70 text-white text-[9px] font-bold px-1.5 py-0.5"
                    data-testid={`reorder-position-${i}`}>
                {i + 1}
              </span>

              {/* Drag handle hint — subtle on desktop, ignored on touch */}
              <span className="absolute bottom-1 left-1 p-0.5 bg-black/50 text-white/70 hidden sm:block">
                <GripVertical className="w-3 h-3" />
              </span>

              {/* Left / right / remove — touch-safe fallback controls. */}
              <div className="absolute bottom-1 right-1 flex gap-1">
                <button
                  type="button"
                  onClick={() => move(i, i - 1)}
                  disabled={i === 0}
                  aria-label="Move earlier"
                  className="p-1 bg-black/70 text-white disabled:opacity-30 hover:text-[#39FF14]"
                  data-testid={`reorder-left-${i}`}
                >
                  <ArrowLeft className="w-3 h-3" />
                </button>
                <button
                  type="button"
                  onClick={() => move(i, i + 1)}
                  disabled={i === value.length - 1}
                  aria-label="Move later"
                  className="p-1 bg-black/70 text-white disabled:opacity-30 hover:text-[#39FF14]"
                  data-testid={`reorder-right-${i}`}
                >
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              {allowRemove && (
                <button
                  type="button"
                  onClick={() => remove(i)}
                  aria-label="Remove image"
                  className="absolute top-6 right-1 p-1 bg-black/70 text-white hover:text-red-400 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                  data-testid={`reorder-remove-${i}`}
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
