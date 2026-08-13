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
import { X } from 'lucide-react';

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
];

const ALL_SIZES = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'One Size'];

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
          <div>
            <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">Sizes</label>
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
          <div>
            <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">Images</label>
            <ProductImageReorder
              value={editForm.images || []}
              onChange={(next) => setEditForm({ ...editForm, images: next })}
            />
            <div className="mt-3">
              <ImageUpload multiple label="Upload More" onUpload={(urls) => setEditForm({ ...editForm, images: [...(editForm.images || []), ...urls] })} />
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
