import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import ImageUpload from '../ImageUpload';
import { ProductImageReorder } from '../product/ProductImageReorder';
import { Plus, X } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORIES = [
  { id: 'hoodies', name: 'Hoodies' },
  { id: 't-shirts', name: 'T-Shirts' },
  { id: 'jackets', name: 'Jackets & Coats' },
  { id: 'trousers', name: 'Trousers & Cargos' },
  { id: 'shorts', name: 'Shorts' },
  { id: 'accessories', name: 'Accessories' },
  { id: 'footwear', name: 'Footwear' },
  { id: 'caps', name: 'Caps & Hats' },
  { id: 'Tracksuits & Sets', name: 'Tracksuits & Sets' },
];

const ALL_SIZES = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'One Size'];
const ROLES = [
  { id: 'top', label: 'Top' },
  { id: 'bottom', label: 'Bottom' },
  { id: 'accessory', label: 'Accessory' },
];

/**
 * Edit-listing modal for MyListings.
 * Parent owns `editForm` state via `setEditForm`; opens when `editProduct` truthy.
 */
export function EditListingDialog({ editProduct, editForm, setEditForm, saving, onSave, onClose }) {
  return (
    <Dialog open={!!editProduct} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="bg-[#0F0F0F] border-white/10 rounded-none max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-white uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            Edit Listing
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <div>
            <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Name</label>
            <Input value={editForm.name || ''} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} className="input-brutalist" />
          </div>
          <div>
            <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Description</label>
            <Textarea value={editForm.description || ''} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} className="input-brutalist min-h-[80px] resize-none" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Price (£)</label>
              <Input type="number" step="0.01" value={editForm.price || ''} onChange={(e) => setEditForm({ ...editForm, price: e.target.value })} className="input-brutalist" />
            </div>
            <div>
              <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Shipping (£)</label>
              <Input type="number" step="0.01" value={editForm.shipping_cost || ''} onChange={(e) => setEditForm({ ...editForm, shipping_cost: e.target.value })} className="input-brutalist" />
            </div>
            <div>
              <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Stock</label>
              <Input type="number" value={editForm.stock || ''} onChange={(e) => setEditForm({ ...editForm, stock: e.target.value })} className="input-brutalist" />
            </div>
          </div>
          <div>
            <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Category</label>
            <Select value={editForm.category || ''} onValueChange={(v) => setEditForm({ ...editForm, category: v })}>
              <SelectTrigger className="w-full bg-transparent border-white/20 rounded-none text-white"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                {CATEGORIES.map((c) => <SelectItem key={c.id} value={c.id} className="text-white hover:bg-white/10 rounded-none">{c.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {/* Listing type convert — safe round-trip (shared fields preserved) */}
          <div className="border border-white/10 p-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[11px] uppercase tracking-wider text-[#C0C0C0]">Listing type</p>
                <p className="text-sm text-white">
                  {editForm.listing_type === 'set' ? 'Full set / Tracksuit' : 'Single item'}
                </p>
              </div>
              <Button
                type="button"
                className="btn-secondary text-xs"
                data-testid="edit-convert-type"
                onClick={() => {
                  const toSet = editForm.listing_type !== 'set';
                  const msg = toSet
                    ? 'Convert this to a Full Set? We\'ll keep your title, price, description, and photos, and reset the sizing section.'
                    : 'Convert this back to a Single item? We\'ll keep your title, price, description, and photos, and reset the set sizing.';
                  if (!window.confirm(msg)) return;
                  if (toSet) {
                    setEditForm({
                      ...editForm,
                      listing_type: 'set',
                      sizing_mode: editForm.sizing_mode || 'split',
                      set_components: (editForm.set_components && editForm.set_components.length)
                        ? editForm.set_components
                        : [{ label: 'Top', role: 'top' }, { label: 'Bottom', role: 'bottom' }],
                      top_sizes: editForm.top_sizes || [],
                      bottom_sizes: editForm.bottom_sizes || [],
                      sizes: [],
                    });
                  } else {
                    setEditForm({ ...editForm, listing_type: 'single', sizes: [] });
                  }
                }}
              >
                Convert to {editForm.listing_type === 'set' ? 'Single' : 'Set'}
              </Button>
            </div>
          </div>

          {/* Set components — only when editing a set */}
          {editForm.listing_type === 'set' && (
            <div>
              <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">Set components</label>
              <div className="space-y-2" data-testid="edit-set-components">
                {(editForm.set_components || []).map((c, i) => (
                  <div key={i} className="flex items-center gap-2" data-testid={`edit-component-${i}`}>
                    <Input
                      maxLength={40}
                      value={c.label || ''}
                      onChange={(e) => {
                        const next = editForm.set_components.map((x, idx) => idx === i ? { ...x, label: e.target.value } : x);
                        setEditForm({ ...editForm, set_components: next });
                      }}
                      placeholder="Hoodie / Trousers"
                      className="input-brutalist flex-1"
                      data-testid={`edit-component-label-${i}`}
                    />
                    <select
                      value={c.role}
                      onChange={(e) => {
                        const next = editForm.set_components.map((x, idx) => idx === i ? { ...x, role: e.target.value } : x);
                        setEditForm({ ...editForm, set_components: next });
                      }}
                      className="input-brutalist w-28 text-xs"
                      data-testid={`edit-component-role-${i}`}
                    >
                      {ROLES.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
                    </select>
                    {editForm.set_components.length > 2 && (
                      <button
                        type="button"
                        onClick={() => setEditForm({
                          ...editForm,
                          set_components: editForm.set_components.filter((_, idx) => idx !== i),
                        })}
                        className="p-2 text-[#9CA3AF] hover:text-red-400"
                        aria-label="Remove component"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <button
                type="button"
                className="mt-2 text-[11px] text-[#39FF14] hover:underline inline-flex items-center gap-1"
                data-testid="edit-add-component"
                onClick={() => setEditForm({
                  ...editForm,
                  set_components: [...(editForm.set_components || []), { label: 'Accessory', role: 'accessory' }],
                })}
              >
                <Plus className="w-3 h-3" /> Add piece
              </button>
            </div>
          )}

          {/* Sizing mode — only when editing a set */}
          {editForm.listing_type === 'set' && (
            <div>
              <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">Sizing</label>
              <div className="grid grid-cols-2 gap-2" data-testid="edit-sizing-mode-toggle">
                <button
                  type="button"
                  onClick={() => setEditForm({ ...editForm, sizing_mode: 'split' })}
                  className={`px-3 py-2 border text-xs ${editForm.sizing_mode === 'split' ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]' : 'border-white/20 text-[#9CA3AF]'}`}
                  data-testid="edit-sizing-split"
                >Split (top + bottom)</button>
                <button
                  type="button"
                  onClick={() => setEditForm({ ...editForm, sizing_mode: 'unified' })}
                  className={`px-3 py-2 border text-xs ${editForm.sizing_mode === 'unified' ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]' : 'border-white/20 text-[#9CA3AF]'}`}
                  data-testid="edit-sizing-unified"
                >Same size</button>
              </div>
            </div>
          )}

          {/* Size chips — one of three shapes depending on listing_type + sizing_mode */}
          {editForm.listing_type !== 'set' || editForm.sizing_mode === 'unified' ? (
            <div>
              <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">
                {editForm.listing_type === 'set' ? 'Set sizes' : 'Sizes'}
              </label>
              <div className="flex flex-wrap gap-1.5">
                {ALL_SIZES.map((size) => (
                  <button key={size} type="button" onClick={() => {
                    const sizes = editForm.sizes || [];
                    setEditForm({ ...editForm, sizes: sizes.includes(size) ? sizes.filter(s => s !== size) : [...sizes, size] });
                  }} className={`px-3 py-1 border text-xs ${(editForm.sizes || []).includes(size) ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]' : 'border-white/20 text-[#9CA3AF]'}`}>
                    {size}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">Top sizes</label>
                <div className="flex flex-wrap gap-1.5" data-testid="edit-top-sizes">
                  {ALL_SIZES.map((size) => (
                    <button key={size} type="button" onClick={() => {
                      const tops = editForm.top_sizes || [];
                      setEditForm({ ...editForm, top_sizes: tops.includes(size) ? tops.filter(s => s !== size) : [...tops, size] });
                    }} className={`px-2.5 py-1 border text-[11px] ${(editForm.top_sizes || []).includes(size) ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]' : 'border-white/20 text-[#9CA3AF]'}`}>
                      {size}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">Bottom sizes</label>
                <div className="flex flex-wrap gap-1.5" data-testid="edit-bottom-sizes">
                  {ALL_SIZES.map((size) => (
                    <button key={size} type="button" onClick={() => {
                      const bots = editForm.bottom_sizes || [];
                      setEditForm({ ...editForm, bottom_sizes: bots.includes(size) ? bots.filter(s => s !== size) : [...bots, size] });
                    }} className={`px-2.5 py-1 border text-[11px] ${(editForm.bottom_sizes || []).includes(size) ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]' : 'border-white/20 text-[#9CA3AF]'}`}>
                      {size}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
          <div>
            <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">Images</label>
            <ProductImageReorder
              value={editForm.images || []}
              onChange={(next) => setEditForm({ ...editForm, images: next })}
            />
            <div className="mt-3">
              <ImageUpload multiple stageBeforeUpload maxImages={Math.max(1, 10 - (editForm.images || []).length)} label="Choose photos from device" onUpload={(urls) => setEditForm({ ...editForm, images: [...(editForm.images || []), ...urls] })} />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <Button className="btn-primary flex-1" onClick={onSave} disabled={saving} data-testid="save-edit-button">
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
            <Button className="btn-secondary" onClick={onClose}>Cancel</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
