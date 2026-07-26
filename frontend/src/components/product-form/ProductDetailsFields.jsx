import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';

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

const COLOURS = ['Black', 'White', 'Grey', 'Navy', 'Green', 'Olive', 'Brown', 'Beige', 'Cream', 'Red', 'Blue', 'Purple', 'Orange', 'Yellow', 'Pink', 'Multi'];
const MATERIALS = ['Cotton', 'Organic Cotton', 'Polyester', 'Nylon', 'Fleece', 'Denim', 'Leather', 'Wool', 'Linen', 'Canvas', 'Corduroy', 'Mesh', 'Mixed'];
const FITS = ['Oversized', 'Regular', 'Slim', 'Relaxed', 'Cropped', 'Boxy'];

/**
 * Name / description / category / colour / material / gender / condition / fit.
 * Pure controlled inputs — parent owns `form` and passes an update callback.
 */
export function ProductDetailsFields({ form, setForm }) {
  return (
    <div className="border border-white/10 bg-[#0A0A0A] p-6 mb-6">
      <h2 className="text-lg font-bold text-white uppercase mb-4" style={{ fontFamily: 'Clash Display, sans-serif' }}>
        Product Details
      </h2>

      <div className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
            Product Name *
          </label>
          <Input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="input-brutalist"
            placeholder="e.g. Oversized Graphic Hoodie - Black"
            data-testid="product-name-input"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
            Description *
          </label>
          <Textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="input-brutalist min-h-[140px] resize-none"
            placeholder="Describe your product — materials, fit, inspiration, care instructions..."
            data-testid="product-description-input"
          />
          <p className="text-xs text-[#9CA3AF] mt-1">{form.description.length}/500 characters</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
            Category *
          </label>
          <Select value={form.category} onValueChange={(value) => setForm({ ...form, category: value })}>
            <SelectTrigger className="w-full bg-transparent border-white/20 rounded-none text-white" data-testid="product-category-select">
              <SelectValue placeholder="Select category" />
            </SelectTrigger>
            <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
              {CATEGORIES.map((cat) => (
                <SelectItem key={cat.id} value={cat.id} className="text-white hover:bg-white/10 rounded-none">
                  {cat.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">Colour</label>
          <div className="flex flex-wrap gap-2">
            {COLOURS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setForm({ ...form, colour: form.colour === c ? '' : c })}
                className={`px-3 py-1.5 text-xs border transition-all ${
                  form.colour === c
                    ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                    : 'border-white/20 text-[#9CA3AF] hover:border-white/40'
                }`}
                data-testid={`colour-${c}`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">Material</label>
          <Select value={form.material} onValueChange={(value) => setForm({ ...form, material: value })}>
            <SelectTrigger className="w-full bg-transparent border-white/20 rounded-none text-white" data-testid="product-material-select">
              <SelectValue placeholder="Select material" />
            </SelectTrigger>
            <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
              {MATERIALS.map((m) => (
                <SelectItem key={m} value={m} className="text-white hover:bg-white/10 rounded-none">
                  {m}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">Gender</label>
            <Select value={form.gender} onValueChange={(value) => setForm({ ...form, gender: value })}>
              <SelectTrigger className="w-full bg-transparent border-white/20 rounded-none text-white" data-testid="product-gender-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                <SelectItem value="unisex" className="text-white hover:bg-white/10 rounded-none">Unisex</SelectItem>
                <SelectItem value="mens" className="text-white hover:bg-white/10 rounded-none">Mens</SelectItem>
                <SelectItem value="womens" className="text-white hover:bg-white/10 rounded-none">Womens</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">Condition</label>
            <Select value={form.condition} onValueChange={(value) => setForm({ ...form, condition: value })}>
              <SelectTrigger className="w-full bg-transparent border-white/20 rounded-none text-white" data-testid="product-condition-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                <SelectItem value="new" className="text-white hover:bg-white/10 rounded-none">New</SelectItem>
                <SelectItem value="like_new" className="text-white hover:bg-white/10 rounded-none">Like New</SelectItem>
                <SelectItem value="used" className="text-white hover:bg-white/10 rounded-none">Used</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">Fit</label>
            <Select value={form.fit || 'none'} onValueChange={(value) => setForm({ ...form, fit: value === 'none' ? '' : value })}>
              <SelectTrigger className="w-full bg-transparent border-white/20 rounded-none text-white" data-testid="product-fit-select">
                <SelectValue placeholder="Select fit" />
              </SelectTrigger>
              <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                <SelectItem value="none" className="text-white hover:bg-white/10 rounded-none">Not specified</SelectItem>
                {FITS.map((f) => (
                  <SelectItem key={f} value={f} className="text-white hover:bg-white/10 rounded-none">
                    {f}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
    </div>
  );
}
