import { useState, useRef, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// A touch move on the main image counts as a swipe only if the finger
// travels further than this many px. Anything shorter is treated as a tap
// so accidental jitter never advances the gallery on tall product pages.
const SWIPE_THRESHOLD_PX = 40;

const _resolveUrl = (u) => (u && u.startsWith('/api/') ? `${API}${u}` : u);

export function ProductGallery({ images = [], productName = '' }) {
  const [index, setIndex] = useState(0);
  const count = images.length;

  // Guard: if the parent hot-swaps to a shorter images array (edit flow),
  // clamp the active index so we never point past the end.
  useEffect(() => {
    if (index >= count) setIndex(0);
  }, [count, index]);

  const wrap = useCallback((i) => ((i % count) + count) % count, [count]);
  const next = useCallback(() => setIndex((i) => wrap(i + 1)), [wrap]);
  const prev = useCallback(() => setIndex((i) => wrap(i - 1)), [wrap]);

  // Keyboard nav on the main image — free UX win, zero cost.
  const mainRef = useRef(null);
  useEffect(() => {
    if (count <= 1) return undefined;
    const onKey = (e) => {
      if (e.key === 'ArrowRight') next();
      else if (e.key === 'ArrowLeft') prev();
    };
    const el = mainRef.current;
    if (!el) return undefined;
    el.addEventListener('keydown', onKey);
    return () => el.removeEventListener('keydown', onKey);
  }, [count, next, prev]);

  // Touch-swipe: track only when there's more than one image. We use the
  // first touch's clientX as the origin and compare against the last touch
  // point on end — simpler and steadier than watching every move event.
  const touchStartX = useRef(null);
  const onTouchStart = (e) => {
    if (count <= 1) return;
    touchStartX.current = e.touches[0].clientX;
  };
  const onTouchEnd = (e) => {
    if (count <= 1 || touchStartX.current == null) return;
    const delta = e.changedTouches[0].clientX - touchStartX.current;
    if (Math.abs(delta) >= SWIPE_THRESHOLD_PX) {
      if (delta < 0) next(); else prev();
    }
    touchStartX.current = null;
  };

  if (count === 0) {
    return (
      <div className="aspect-[3/4] overflow-hidden border border-white/10 bg-[#0F0F0F] flex items-center justify-center text-[#9CA3AF]" data-testid="product-gallery-empty">
        No Image
      </div>
    );
  }

  const currentUrl = _resolveUrl(images[index]);

  return (
    <div className="space-y-4" data-testid="product-gallery">
      {/* Main image */}
      <div
        ref={mainRef}
        tabIndex={count > 1 ? 0 : -1}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        className="relative aspect-[3/4] overflow-hidden border border-white/10 bg-[#0F0F0F] focus:outline-none focus:border-[#39FF14]/40 select-none"
        data-testid="product-gallery-main"
      >
        <img
          src={currentUrl}
          alt={`${productName} — image ${index + 1} of ${count}`}
          className="w-full h-full object-cover"
          data-testid="product-main-image"
          draggable={false}
        />

        {count > 1 && (
          <>
            <button
              type="button"
              onClick={prev}
              aria-label="Previous image"
              className="absolute left-2 top-1/2 -translate-y-1/2 p-2 bg-black/60 border border-white/10 text-white hover:text-[#39FF14] hover:border-[#39FF14]/60 backdrop-blur-sm transition-colors"
              data-testid="gallery-prev"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              type="button"
              onClick={next}
              aria-label="Next image"
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-black/60 border border-white/10 text-white hover:text-[#39FF14] hover:border-[#39FF14]/60 backdrop-blur-sm transition-colors"
              data-testid="gallery-next"
            >
              <ChevronRight className="w-5 h-5" />
            </button>

            {/* Position pill (visible on all sizes; dots below for touch users). */}
            <span
              className="absolute top-2 right-2 text-[10px] uppercase tracking-wider px-2 py-0.5 bg-black/60 border border-white/10 text-[#C0C0C0]"
              data-testid="gallery-counter"
            >
              {index + 1} / {count}
            </span>

            {/* Dot indicators */}
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5" data-testid="gallery-dots">
              {images.map((_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setIndex(i)}
                  aria-label={`Show image ${i + 1}`}
                  className={`w-1.5 h-1.5 rounded-full transition-all ${
                    i === index ? 'bg-[#39FF14] w-4' : 'bg-white/40 hover:bg-white/70'
                  }`}
                  data-testid={`gallery-dot-${i}`}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Thumbnails */}
      {count > 1 && (
        <div
          className="grid gap-2"
          style={{ gridTemplateColumns: `repeat(${Math.min(count, 6)}, minmax(0, 1fr))` }}
          data-testid="gallery-thumbnails"
        >
          {images.map((img, i) => (
            <button
              type="button"
              key={img + i}
              onClick={() => setIndex(i)}
              aria-label={`Show image ${i + 1}`}
              aria-current={i === index ? 'true' : 'false'}
              className={`aspect-square overflow-hidden border bg-[#0F0F0F] transition-colors ${
                i === index ? 'border-[#39FF14]' : 'border-white/10 hover:border-white/30'
              }`}
              data-testid={`gallery-thumbnail-${i}`}
            >
              <img
                src={_resolveUrl(img)}
                alt={`${productName} thumbnail ${i + 1}`}
                className={`w-full h-full object-cover transition-opacity ${
                  i === index ? 'opacity-100' : 'opacity-70 hover:opacity-100'
                }`}
                draggable={false}
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
