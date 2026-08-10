import { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

/**
 * ProductDescription — a scannable, tidy renderer for seller-authored copy.
 *
 * Sellers paste whatever they like (some write novels, some write two lines).
 * We keep their words intact but structure the layout so long descriptions
 * don't become a wall of text:
 *
 *   - Blank lines split into real paragraphs (proper spacing between them)
 *   - Lines starting with "-", "•", or "*" become a bulleted list
 *   - Anything over `COLLAPSED_CHAR_LIMIT` chars is collapsed behind a
 *     "Show more" toggle so the buy button stays above the fold
 *   - A "Details" chip-row surfaces the structured product attributes
 *     (colour, material, gender, condition, fit) so buyers can scan them
 *     without hunting through the paragraph
 */

const COLLAPSED_CHAR_LIMIT = 280;

function _parseBlocks(text) {
  // Split on blank lines → paragraphs. Then within each paragraph, detect if
  // ALL lines are bullet-style; if so, promote to a list block.
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
    // Single-line bullet? Still render as paragraph text (no list of one).
    return { type: 'para', text: para };
  });
}

export function ProductDescription({ product }) {
  const [expanded, setExpanded] = useState(false);

  const blocks = useMemo(() => _parseBlocks(product?.description), [product?.description]);
  const rawLength = (product?.description || '').length;
  const needsCollapse = rawLength > COLLAPSED_CHAR_LIMIT;

  // When collapsed, show only the first paragraph (or a truncated slice of it
  // if the first paragraph itself is very long).
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
    product?.condition && product.condition !== 'new' && {
      label: 'Condition',
      value: product.condition.replace(/_/g, ' '),
    },
    product?.fit && { label: 'Fit', value: product.fit },
  ].filter(Boolean);

  if (!product?.description && attrs.length === 0) return null;

  return (
    <div className="mb-8" data-testid="product-description-section">
      <h3 className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF] mb-3">Details</h3>

      {/* Attribute chip row — always visible so buyers can scan the facts fast */}
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

      {/* Description body — paragraphs / lists honoured */}
      {product?.description && (
        <div
          className="text-[#9CA3AF] leading-relaxed space-y-4"
          data-testid="product-description"
        >
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
          {expanded ? (
            <>Show less <ChevronUp className="w-3 h-3" /></>
          ) : (
            <>Show more <ChevronDown className="w-3 h-3" /></>
          )}
        </button>
      )}
    </div>
  );
}
