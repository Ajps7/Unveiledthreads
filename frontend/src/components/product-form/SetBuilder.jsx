import { Plus, X, Info } from 'lucide-react';

const ALL_SIZES = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'One Size'];
const ROLES = [
  { id: 'top', label: 'Top' },
  { id: 'bottom', label: 'Bottom' },
  { id: 'accessory', label: 'Accessory' },
];

/**
 * SetBuilder — only rendered when listing_type === 'set'.
 *
 * Shape it owns on the form:
 *   set_components: [{ label: 'Jacket', role: 'top' }, ...]
 *   sizing_mode:    'unified' | 'split'   (default 'split' for tracksuits)
 *   sizes:          ['S','M',...]         when sizing_mode='unified'
 *   top_sizes:      ['M','L',...]         when sizing_mode='split'
 *   bottom_sizes:   ['M','L',...]
 */
export function SetBuilder({ form, setForm }) {
  const components = form.set_components || [];
  const sizingMode = form.sizing_mode || 'split';

  const updateComponent = (i, patch) => {
    const next = components.map((c, idx) => (idx === i ? { ...c, ...patch } : c));
    setForm((prev) => ({ ...prev, set_components: next }));
  };

  const addComponent = () => {
    setForm((prev) => ({
      ...prev,
      set_components: [...(prev.set_components || []), { label: 'Accessory', role: 'accessory' }],
    }));
  };

  const removeComponent = (i) => {
    if (components.length <= 2) return; // min 2 enforced
    setForm((prev) => ({
      ...prev,
      set_components: (prev.set_components || []).filter((_, idx) => idx !== i),
    }));
  };

  const toggleUnifiedSize = (size) => {
    setForm((prev) => ({
      ...prev,
      sizes: (prev.sizes || []).includes(size)
        ? prev.sizes.filter((s) => s !== size)
        : [...(prev.sizes || []), size],
    }));
  };

  const toggleTopSize = (size) => {
    setForm((prev) => ({
      ...prev,
      top_sizes: (prev.top_sizes || []).includes(size)
        ? prev.top_sizes.filter((s) => s !== size)
        : [...(prev.top_sizes || []), size],
    }));
  };

  const toggleBottomSize = (size) => {
    setForm((prev) => ({
      ...prev,
      bottom_sizes: (prev.bottom_sizes || []).includes(size)
        ? prev.bottom_sizes.filter((s) => s !== size)
        : [...(prev.bottom_sizes || []), size],
    }));
  };

  return (
    <div className="border border-[#39FF14]/30 bg-[#39FF14]/5 p-6 mb-6" data-testid="set-builder">
      <h2 className="text-lg font-bold text-white uppercase mb-1" style={{ fontFamily: 'Clash Display, sans-serif' }}>
        Set Builder <span className="text-[#39FF14] text-xs font-normal normal-case ml-2">(for tracksuits & co-ords)</span>
      </h2>
      <p className="text-xs text-[#9CA3AF] mb-5">
        A set lists as one product but sells as a bundle. Add the pieces, pick sizing, and you&rsquo;re done.
      </p>

      {/* Components */}
      <div className="mb-6">
        <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-2">
          What&rsquo;s in the set?
        </label>
        <div className="space-y-2" data-testid="set-components">
          {components.map((c, i) => (
            <div key={i} className="flex items-center gap-2" data-testid={`set-component-${i}`}>
              <input
                type="text"
                maxLength={40}
                value={c.label}
                onChange={(e) => updateComponent(i, { label: e.target.value })}
                placeholder="Hoodie / Trousers / Cap"
                className="input-brutalist flex-1"
                data-testid={`component-label-${i}`}
              />
              <select
                value={c.role}
                onChange={(e) => updateComponent(i, { role: e.target.value })}
                className="input-brutalist w-32"
                data-testid={`component-role-${i}`}
              >
                {ROLES.map((r) => (
                  <option key={r.id} value={r.id}>{r.label}</option>
                ))}
              </select>
              {components.length > 2 && (
                <button
                  type="button"
                  onClick={() => removeComponent(i)}
                  className="p-2 text-[#9CA3AF] hover:text-red-400 border border-white/10 hover:border-red-400/40 transition-colors"
                  aria-label="Remove component"
                  data-testid={`remove-component-${i}`}
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={addComponent}
          className="mt-3 text-xs text-[#39FF14] hover:underline inline-flex items-center gap-1"
          data-testid="add-component"
        >
          <Plus className="w-3 h-3" /> Add another piece
        </button>
      </div>

      {/* Sizing mode toggle */}
      <div className="mb-6">
        <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-2">
          Sizing
        </label>
        <div className="grid grid-cols-2 gap-2 mb-2" data-testid="sizing-mode-toggle">
          <button
            type="button"
            onClick={() => setForm((prev) => ({ ...prev, sizing_mode: 'split' }))}
            className={`px-4 py-3 border text-sm font-medium transition-all text-left ${
              sizingMode === 'split'
                ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                : 'border-white/20 text-[#9CA3AF] hover:border-white/40 hover:text-white'
            }`}
            data-testid="sizing-mode-split"
          >
            <span className="block uppercase tracking-wider text-xs">Split</span>
            <span className="block text-[11px] font-normal normal-case mt-1 opacity-80">Top + bottom sizes separately</span>
          </button>
          <button
            type="button"
            onClick={() => setForm((prev) => ({ ...prev, sizing_mode: 'unified' }))}
            className={`px-4 py-3 border text-sm font-medium transition-all text-left ${
              sizingMode === 'unified'
                ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                : 'border-white/20 text-[#9CA3AF] hover:border-white/40 hover:text-white'
            }`}
            data-testid="sizing-mode-unified"
          >
            <span className="block uppercase tracking-wider text-xs">Same size</span>
            <span className="block text-[11px] font-normal normal-case mt-1 opacity-80">One size for the whole set</span>
          </button>
        </div>
        {sizingMode === 'split' && (
          <p className="text-[11px] text-[#39FF14] flex items-start gap-1.5 mt-2">
            <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
            Recommended for tracksuits — reduces returns from mismatched fits.
          </p>
        )}
      </div>

      {/* Size selectors adapt to the mode */}
      {sizingMode === 'unified' ? (
        <div>
          <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-2">
            Set sizes you stock
          </label>
          <div className="flex flex-wrap gap-2" data-testid="unified-size-selector">
            {ALL_SIZES.map((size) => (
              <button
                key={size}
                type="button"
                onClick={() => toggleUnifiedSize(size)}
                className={`px-4 py-2 border text-sm font-medium transition-all ${
                  (form.sizes || []).includes(size)
                    ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                    : 'border-white/20 text-[#9CA3AF] hover:border-white/40 hover:text-white'
                }`}
                data-testid={`unified-size-${size}`}
              >
                {size}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-2">
              Top sizes
            </label>
            <div className="flex flex-wrap gap-2" data-testid="top-size-selector">
              {ALL_SIZES.map((size) => (
                <button
                  key={size}
                  type="button"
                  onClick={() => toggleTopSize(size)}
                  className={`px-3 py-2 border text-xs font-medium transition-all ${
                    (form.top_sizes || []).includes(size)
                      ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                      : 'border-white/20 text-[#9CA3AF] hover:border-white/40 hover:text-white'
                  }`}
                  data-testid={`top-size-${size}`}
                >
                  {size}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-2">
              Bottom sizes
            </label>
            <div className="flex flex-wrap gap-2" data-testid="bottom-size-selector">
              {ALL_SIZES.map((size) => (
                <button
                  key={size}
                  type="button"
                  onClick={() => toggleBottomSize(size)}
                  className={`px-3 py-2 border text-xs font-medium transition-all ${
                    (form.bottom_sizes || []).includes(size)
                      ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                      : 'border-white/20 text-[#9CA3AF] hover:border-white/40 hover:text-white'
                  }`}
                  data-testid={`bottom-size-${size}`}
                >
                  {size}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
