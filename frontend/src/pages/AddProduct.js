import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Button } from '../components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import Header from '../components/Header';
import ImageUpload from '../components/ImageUpload';
import { ArrowLeft, Plus, X, Loader2, Upload, Trash2 } from 'lucide-react';

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
const COLOURS = ["Black", "White", "Grey", "Navy", "Green", "Olive", "Brown", "Beige", "Cream", "Red", "Blue", "Purple", "Orange", "Yellow", "Pink", "Multi"];
const MATERIALS = ["Cotton", "Organic Cotton", "Polyester", "Nylon", "Fleece", "Denim", "Leather", "Wool", "Linen", "Canvas", "Corduroy", "Mesh", "Mixed"];
const FITS = ["Oversized", "Regular", "Slim", "Relaxed", "Cropped", "Boxy"];

export default function AddProduct() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    name: '',
    description: '',
    price: '',
    shipping_cost: '3.99',
    category: '',
    stock: '',
    images: [],
    sizes: [],
    colour: '',
    material: '',
    gender: 'unisex',
    condition: 'new',
    fit: '',
  });

  useEffect(() => {
    if (authLoading) return;
    if (!user) { navigate('/login'); return; }
    if (user.role !== 'brand' && user.role !== 'admin') { navigate('/apply'); return; }
  }, [user, authLoading, navigate]);

  const toggleSize = (size) => {
    setForm(prev => ({
      ...prev,
      sizes: prev.sizes.includes(size)
        ? prev.sizes.filter(s => s !== size)
        : [...prev.sizes, size]
    }));
  };

  const handleImageUpload = (urls) => {
    setForm(prev => ({ ...prev, images: [...prev.images, ...urls] }));
  };

  const removeImage = (index) => {
    setForm(prev => ({ ...prev, images: prev.images.filter((_, i) => i !== index) }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!form.name.trim()) { setError('Product name is required'); return; }
    if (!form.description.trim()) { setError('Description is required'); return; }
    if (!form.price || parseFloat(form.price) <= 0) { setError('Valid price is required'); return; }
    if (!form.category) { setError('Category is required'); return; }
    if (form.sizes.length === 0) { setError('Select at least one size'); return; }
    if (form.images.length === 0) { setError('Upload at least one photo'); return; }
    if (!form.stock || parseInt(form.stock) < 0) { setError('Stock quantity is required'); return; }

    setSubmitting(true);
    try {
      await axios.post(`${API}/api/products`, {
        name: form.name.trim(),
        description: form.description.trim(),
        price: parseFloat(form.price),
        shipping_cost: parseFloat(form.shipping_cost) || 0,
        category: form.category,
        sizes: form.sizes,
        images: form.images,
        stock: parseInt(form.stock),
        colour: form.colour || null,
        material: form.material || null,
        gender: form.gender,
        condition: form.condition,
        fit: form.fit || null,
      }, { withCredentials: true });

      navigate('/brand/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create product');
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="w-8 h-8 text-[#39FF14] animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-4xl mx-auto px-6 md:px-12 py-8">
        <Link to="/brand/dashboard" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to dashboard
        </Link>

        <h1 className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-2 text-white" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="add-product-title">
          LIST A PRODUCT
        </h1>
        <p className="text-[#9CA3AF] mb-10">
          Add clear, well-lit photos and detailed descriptions to attract buyers. Quality listings get more views.
        </p>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 mb-6" data-testid="product-form-error">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Photos Section */}
          <div className="border border-white/10 bg-[#0A0A0A] p-6 mb-6">
            <h2 className="text-lg font-bold text-white uppercase mb-1" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              <Upload className="w-5 h-5 inline mr-2" />
              Photos
            </h2>
            <p className="text-xs text-[#9CA3AF] mb-4">
              Upload clear, well-lit photos on a plain background. First image is the cover. Max 5MB each, JPEG/PNG/WebP.
            </p>

            {form.images.length > 0 && (
              <div className="grid grid-cols-4 md:grid-cols-6 gap-3 mb-4">
                {form.images.map((img, i) => (
                  <div key={i} className="relative group aspect-square overflow-hidden border border-white/10 bg-[#0F0F0F]">
                    <img src={img.startsWith('/api/') ? `${API}${img}` : img} alt={`Product ${i+1}`} className="w-full h-full object-cover" />
                    {i === 0 && (
                      <span className="absolute top-1 left-1 bg-[#39FF14] text-black text-[8px] font-bold px-1.5 py-0.5">COVER</span>
                    )}
                    <button
                      type="button"
                      onClick={() => removeImage(i)}
                      className="absolute top-1 right-1 bg-black/70 text-white p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <ImageUpload
              multiple
              label={form.images.length > 0 ? 'Upload More Photos' : 'Upload Photos'}
              onUpload={handleImageUpload}
            />
          </div>

          {/* Details Section */}
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
                      <SelectItem key={cat.id} value={cat.id} className="text-white hover:bg-white/10 rounded-none">{cat.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Colour */}
              <div>
                <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">Colour</label>
                <div className="flex flex-wrap gap-2">
                  {COLOURS.map((c) => (
                    <button key={c} type="button" onClick={() => setForm({ ...form, colour: form.colour === c ? '' : c })}
                      className={`px-3 py-1.5 text-xs border transition-all ${form.colour === c ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]' : 'border-white/20 text-[#9CA3AF] hover:border-white/40'}`}
                      data-testid={`colour-${c}`}
                    >{c}</button>
                  ))}
                </div>
              </div>

              {/* Material */}
              <div>
                <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">Material</label>
                <Select value={form.material} onValueChange={(value) => setForm({ ...form, material: value })}>
                  <SelectTrigger className="w-full bg-transparent border-white/20 rounded-none text-white" data-testid="product-material-select">
                    <SelectValue placeholder="Select material" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                    {MATERIALS.map((m) => (
                      <SelectItem key={m} value={m} className="text-white hover:bg-white/10 rounded-none">{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Gender & Condition & Fit */}
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
                        <SelectItem key={f} value={f} className="text-white hover:bg-white/10 rounded-none">{f}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </div>

          {/* Sizes Section */}
          <div className="border border-white/10 bg-[#0A0A0A] p-6 mb-6">
            <h2 className="text-lg font-bold text-white uppercase mb-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Available Sizes *
            </h2>
            <p className="text-xs text-[#9CA3AF] mb-4">Select all sizes you have in stock</p>

            <div className="flex flex-wrap gap-2" data-testid="size-selector">
              {ALL_SIZES.map((size) => (
                <button
                  key={size}
                  type="button"
                  onClick={() => toggleSize(size)}
                  className={`px-5 py-2.5 border text-sm font-medium transition-all ${
                    form.sizes.includes(size)
                      ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                      : 'border-white/20 text-[#9CA3AF] hover:border-white/40 hover:text-white'
                  }`}
                  data-testid={`size-toggle-${size}`}
                >
                  {size}
                </button>
              ))}
            </div>
            {form.sizes.length > 0 && (
              <p className="text-xs text-[#39FF14] mt-3">Selected: {form.sizes.join(', ')}</p>
            )}
          </div>

          {/* Pricing & Stock Section */}
          <div className="border border-white/10 bg-[#0A0A0A] p-6 mb-6">
            <h2 className="text-lg font-bold text-white uppercase mb-4" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Pricing & Stock
            </h2>

            <div className="grid md:grid-cols-3 gap-5">
              <div>
                <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
                  Price (£) *
                </label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={form.price}
                  onChange={(e) => setForm({ ...form, price: e.target.value })}
                  className="input-brutalist"
                  placeholder="49.99"
                  data-testid="product-price-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
                  Shipping Cost (£)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.shipping_cost}
                  onChange={(e) => setForm({ ...form, shipping_cost: e.target.value })}
                  className="input-brutalist"
                  placeholder="3.99"
                  data-testid="product-shipping-input"
                />
                <p className="text-xs text-[#9CA3AF] mt-1">Set to 0 for free shipping</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
                  Total Stock *
                </label>
                <Input
                  type="number"
                  min="1"
                  value={form.stock}
                  onChange={(e) => setForm({ ...form, stock: e.target.value })}
                  className="input-brutalist"
                  placeholder="50"
                  data-testid="product-stock-input"
                />
              </div>
            </div>

            {form.price && (
              <div className="mt-5 p-4 bg-[#0F0F0F] border border-white/5">
                <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-2">Buyer sees</p>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-white">£{parseFloat(form.price || 0).toFixed(2)}</span>
                  <span className="text-sm text-[#9CA3AF]">
                    + £{(parseFloat(form.price || 0) * 0.10).toFixed(2)} platform fee
                    {parseFloat(form.shipping_cost || 0) > 0 ? ` + £${parseFloat(form.shipping_cost).toFixed(2)} shipping` : ' + free shipping'}
                  </span>
                </div>
                <p className="text-xs text-[#39FF14] mt-1">
                  You receive: £{(parseFloat(form.price || 0) + parseFloat(form.shipping_cost || 0)).toFixed(2)} per sale
                </p>
              </div>
            )}
          </div>

          {/* Submit */}
          <div className="flex gap-4">
            <Button
              type="submit"
              className="btn-primary flex-1 py-4 text-lg"
              disabled={submitting}
              data-testid="submit-product-button"
            >
              {submitting ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Creating Listing...</>
              ) : (
                <><Plus className="w-5 h-5 mr-2" /> LIST PRODUCT</>
              )}
            </Button>
            <Link to="/brand/dashboard">
              <Button type="button" className="btn-secondary py-4">Cancel</Button>
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
