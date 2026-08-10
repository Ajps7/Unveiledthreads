import { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

const COLLAPSED_CHAR_LIMIT = 280;

function _parseBlocks(text) {
  const paragraphs = String(text || '')
    .replace(/\r\n/g, '\n')
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
  return paragraphs.map((para) => {
    const lines = para.split('\n').map((l) => l.trim()).filter(Boolean);
    const isList = lines.length > 1 && lines.every((l) => /^[-•*]\s+/.test(l));
    if (isList) {
      return { type: 'list', items: lines.map((l) => l.replace(/^[-•*]\s+/, '')) };
    }
    return { type: 'para', text: para };
  });
}

export function ProductDescription({ product }) {
  const [expanded, setExpanded] = useState(false);
  const blocks = useMemo(() => _parseBlocks(product?.description), [product?.description]);
  const rawLength = (product?.description || '').length;
  const needsCollapse = rawLength > COLLAPSED_CHAR_LIMIT;

  const visibleBlocks = useMemo(() => {
    if (!needsCollapse || expanded) return blocks;
    const first = blocks[0];
    if (!first) return [];
    if (first.type === 'para' && first.text.length > COLLAPSED_CHAR_LIMIT) {
      return [{ type: 'para', text: first.text.slice(0, COLLAPSED_CHAR_LIMIT).trimEnd() + '…' }];
    }
    return [first];
  }, [blocks, expanded, needsCollapse]);

  const attrs = [
    product?.colour && { label: 'Colour', value: product.colour },
    product?.material && { label: 'Material', value: product.material },
    product?.gender && product.gender !== 'unisex' && { label: 'Gender', value: product.gender },
    product?.condition && product.condition !== 'new' && { label: 'Condition', value: product.condition.replace(/_/g, ' ') },
    product?.fit && { label: 'Fit', value: product.fit },
  ].filter(Boolean);

  // Structured description sections (all optional — hidden if empty).
  const details = Array.isArray(product?.details) ? product.details.filter(Boolean) : [];
  const specRows = [
    product?.materials && { label: 'Materials', value: product.materials },
    product?.fit_notes && { label: 'Fit', value: product.fit_notes },
    product?.care && { label: 'Care', value: product.care },
  ].filter(Boolean);
  const hasStructured =
    !!product?.story || details.length > 0 || specRows.length > 0;

  if (!product?.description && attrs.length === 0 && !hasStructured) return null;

  return (
    <div className="mb-8" data-testid="product-description-section">
      {product?.story && (
        <div className="mb-6 border-l-2 border-[#39FF14] pl-4" data-testid="product-story">
          <p className="text-white/90 leading-relaxed italic">{product.story}</p>
        </div>
      )}

      <h3 className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF] mb-3">Details</h3>

      {attrs.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-5" data-testid="product-attribute-chips">
          {attrs.map((a) => (
            <span
              key={a.label}
              className="text-[10px] uppercase tracking-wider px-2.5 py-1 border border-white/10 bg-[#0F0F0F] text-[#C0C0C0]"
              data-testid={`attribute-${a.label.toLowerCase()}`}
            >
              <span className="text-[#9CA3AF] mr-1">{a.label}</span>
              <span className="text-white capitalize">{a.value}</span>
            </span>
          ))}
        </div>
      )}

      {details.length > 0 && (
        <ul
          className="list-disc list-outside pl-5 space-y-1.5 marker:text-[#39FF14] text-[#C0C0C0] mb-5"
          data-testid="product-details-bullets"
        >
          {details.map((item, i) => (
            <li key={i} className="pl-1">{item}</li>
          ))}
        </ul>
      )}

      {specRows.length > 0 && (
        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 mb-5 text-sm" data-testid="product-spec-rows">
          {specRows.map((r) => (
            <div key={r.label} className="contents">
              <dt className="text-[#9CA3AF] uppercase text-xs tracking-wider">{r.label}</dt>
              <dd className="text-white">{r.value}</dd>
            </div>
          ))}
        </dl>
      )}

      {product?.description && (
        <div className="text-[#9CA3AF] leading-relaxed space-y-4" data-testid="product-description">
          {visibleBlocks.map((b, i) =>
            b.type === 'list' ? (
              <ul key={i} className="list-disc list-outside pl-5 space-y-1.5 marker:text-[#39FF14]">
                {b.items.map((item, j) => (
                  <li key={j} className="pl-1">{item}</li>
                ))}
              </ul>
            ) : (
              <p key={i} className="whitespace-pre-line">{b.text}</p>
            )
          )}
        </div>
      )}

      {needsCollapse && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-3 inline-flex items-center gap-1 text-xs uppercase tracking-wider text-[#39FF14] hover:text-white transition-colors"
          data-testid="toggle-description-button"
        >
          {expanded ? (<>Show less <ChevronUp className="w-3 h-3" /></>) : (<>Show more <ChevronDown className="w-3 h-3" /></>)}
        </button>
      )}
    </div>
  );
}
