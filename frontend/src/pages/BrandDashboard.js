import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import Header from '../components/Header';
import ImageUpload from '../components/ImageUpload';
import { 
  LayoutDashboard, 
  Package, 
  Plus, 
  Zap, 
  TrendingUp,
  Edit,
  Trash2,
  ExternalLink,
  Loader2,
  Upload,
  ShoppingCart
} from 'lucide-react';

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

export default function BrandDashboard() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [brandData, setBrandData] = useState(null);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addProductOpen, setAddProductOpen] = useState(false);
  const [productForm, setProductForm] = useState({
    name: '',
    description: '',
    price: '',
    category: '',
    sizes: '',
    images: [],
    stock: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      navigate('/login');
      return;
    }
    if (user.role !== 'brand' && user.role !== 'admin') {
      navigate('/apply');
      return;
    }
    fetchBrandData();
  }, [user, authLoading, navigate]);

  const fetchBrandData = async () => {
    try {
      const response = await axios.get(`${API}/api/brands/my-application`, { withCredentials: true });
      if (response.data && response.data.brand_profile) {
        setBrandData(response.data.brand_profile);
        // Fetch products and orders
        const [prodRes, ordersRes] = await Promise.all([
          axios.get(`${API}/api/products?brand_id=${response.data.brand_profile.id}`),
          axios.get(`${API}/api/orders/brand-orders`, { withCredentials: true }).catch(() => ({ data: [] }))
        ]);
        setProducts(prodRes.data);
        setOrders(ordersRes.data);
      }
    } catch (error) {
      console.error('Error fetching brand data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddProduct = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      const productData = {
        name: productForm.name,
        description: productForm.description,
        price: parseFloat(productForm.price),
        category: productForm.category,
        sizes: productForm.sizes.split(',').map(s => s.trim()).filter(Boolean),
        images: productForm.images,
        stock: parseInt(productForm.stock) || 0
      };

      await axios.post(`${API}/api/products`, productData, { withCredentials: true });
      setAddProductOpen(false);
      setProductForm({
        name: '',
        description: '',
        price: '',
        category: '',
        sizes: '',
        images: [],
        stock: ''
      });
      fetchBrandData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add product');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteProduct = async (productId) => {
    if (!window.confirm('Are you sure you want to delete this product?')) return;
    
    try {
      await axios.delete(`${API}/api/products/${productId}`, { withCredentials: true });
      fetchBrandData();
    } catch (err) {
      console.error('Error deleting product:', err);
    }
  };

  const handleBoostBrand = async (packageId) => {
    try {
      const response = await axios.post(
        `${API}/api/boost/checkout`,
        { package_id: packageId, origin_url: window.location.origin },
        { withCredentials: true }
      );
      window.location.href = response.data.url;
    } catch (err) {
      console.error('Error creating checkout:', err);
      alert('Failed to create checkout session');
    }
  };

  if (loading || authLoading) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="w-8 h-8 text-[#39FF14] animate-spin" />
        </div>
      </div>
    );
  }

  if (!brandData) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="max-w-2xl mx-auto px-6 py-24 text-center">
          <h1 className="text-2xl font-bold text-white mb-4">Brand Profile Not Found</h1>
          <p className="text-[#9CA3AF] mb-8">
            Your brand application may still be pending approval.
          </p>
          <Link to="/apply">
            <Button className="btn-primary">Apply as Brand</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      <div className="max-w-7xl mx-auto px-6 md:px-12 py-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full overflow-hidden bg-[#0F0F0F] border border-white/10">
              {brandData.logo_url ? (
                <img src={brandData.logo_url} alt={brandData.brand_name} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-2xl font-bold text-[#39FF14]">
                  {brandData.brand_name.charAt(0)}
                </div>
              )}
            </div>
            <div>
              <h1 
                className="text-2xl font-black tracking-tighter uppercase text-white"
                style={{ fontFamily: 'Clash Display, sans-serif' }}
                data-testid="dashboard-brand-name"
              >
                {brandData.brand_name}
              </h1>
              <div className="flex items-center gap-2 mt-1">
                {brandData.is_boosted && (
                  <span className="badge-boost text-[10px] flex items-center gap-1">
                    <Zap className="w-3 h-3" />
                    Boosted
                  </span>
                )}
                {brandData.is_brand_of_week && (
                  <span className="badge-boost text-[10px]">Brand of Week</span>
                )}
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <Link to={`/brands/${brandData.id}`}>
              <Button className="btn-secondary" data-testid="view-profile-button">
                <ExternalLink className="w-4 h-4 mr-2" />
                View Profile
              </Button>
            </Link>
            <Dialog open={addProductOpen} onOpenChange={setAddProductOpen}>
              <DialogTrigger asChild>
                <Button className="btn-primary" data-testid="add-product-button">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Product
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-[#0F0F0F] border-white/10 rounded-none max-w-lg">
                <DialogHeader>
                  <DialogTitle className="text-xl font-bold text-white uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
                    Add New Product
                  </DialogTitle>
                </DialogHeader>
                <form onSubmit={handleAddProduct} className="space-y-4 mt-4">
                  {error && (
                    <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-3 py-2 text-sm">
                      {error}
                    </div>
                  )}
                  <div>
                    <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Name *</label>
                    <Input
                      value={productForm.name}
                      onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
                      className="input-brutalist"
                      required
                      data-testid="product-name-input"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Description *</label>
                    <Textarea
                      value={productForm.description}
                      onChange={(e) => setProductForm({ ...productForm, description: e.target.value })}
                      className="input-brutalist min-h-[80px] resize-none"
                      required
                      data-testid="product-description-input"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Price (£) *</label>
                      <Input
                        type="number"
                        step="0.01"
                        value={productForm.price}
                        onChange={(e) => setProductForm({ ...productForm, price: e.target.value })}
                        className="input-brutalist"
                        required
                        data-testid="product-price-input"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Stock *</label>
                      <Input
                        type="number"
                        value={productForm.stock}
                        onChange={(e) => setProductForm({ ...productForm, stock: e.target.value })}
                        className="input-brutalist"
                        required
                        data-testid="product-stock-input"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Category *</label>
                    <Select 
                      value={productForm.category} 
                      onValueChange={(value) => setProductForm({ ...productForm, category: value })}
                    >
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
                    <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Sizes (comma separated)</label>
                    <Input
                      value={productForm.sizes}
                      onChange={(e) => setProductForm({ ...productForm, sizes: e.target.value })}
                      className="input-brutalist"
                      placeholder="S, M, L, XL"
                      data-testid="product-sizes-input"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Product Images</label>
                    <ImageUpload
                      multiple
                      label="Upload Product Photos"
                      onUpload={(urls) => setProductForm({ ...productForm, images: [...productForm.images, ...urls] })}
                    />
                    {productForm.images.length > 0 && (
                      <div className="grid grid-cols-4 gap-2 mt-2">
                        {productForm.images.map((img, i) => (
                          <div key={i} className="relative group aspect-square overflow-hidden border border-white/10 bg-[#0F0F0F]">
                            <img src={img.startsWith('/api/') ? `${API}${img}` : img} alt={`Product ${i+1}`} className="w-full h-full object-cover" />
                            <button
                              type="button"
                              onClick={() => setProductForm({ ...productForm, images: productForm.images.filter((_, idx) => idx !== i) })}
                              className="absolute top-1 right-1 bg-black/70 text-white p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <Button type="submit" className="btn-primary w-full" disabled={submitting} data-testid="submit-product-button">
                    {submitting ? 'Adding...' : 'Add Product'}
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
          <div className="border border-white/10 p-6 bg-[#0A0A0A]">
            <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-2">Products</p>
            <p className="text-3xl font-bold text-white" data-testid="products-count">{products.length}</p>
          </div>
          <div className="border border-white/10 p-6 bg-[#0A0A0A]">
            <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-2">Status</p>
            <p className="text-lg font-bold text-[#39FF14]">
              {brandData.is_boosted ? 'Boosted' : 'Active'}
            </p>
          </div>
          <div className="border border-white/10 p-6 bg-[#0A0A0A]">
            <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-2">Category</p>
            <p className="text-lg font-bold text-white capitalize">{brandData.category}</p>
          </div>
          <div className="border border-white/10 p-6 bg-[#0A0A0A]">
            <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-2">Location</p>
            <p className="text-lg font-bold text-white">{brandData.location}</p>
          </div>
        </div>

        {/* Brand Profile Images */}
        <div className="mb-12 border border-white/10 bg-[#0A0A0A] p-6">
          <h3 className="text-lg font-bold text-white uppercase mb-4" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            <Upload className="w-5 h-5 inline mr-2" />
            Brand Profile Images
          </h3>
          <div className="grid md:grid-cols-2 gap-6">
            {/* Logo Upload */}
            <div>
              <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">Brand Logo</label>
              {brandData.logo_url && (
                <div className="w-24 h-24 rounded-full overflow-hidden border border-white/10 mb-3">
                  <img
                    src={brandData.logo_url.startsWith('/api/') ? `${API}${brandData.logo_url}` : brandData.logo_url}
                    alt="Logo"
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <ImageUpload
                label="Upload Logo"
                onUpload={async (url) => {
                  // Upload via the brand logo endpoint
                  try {
                    const input = document.querySelector('[data-testid="logo-upload-input"]');
                    if (!input || !input.files[0]) return;
                    const formData = new FormData();
                    formData.append('file', input.files[0]);
                    await axios.post(`${API}/api/brands/upload-logo`, formData, { withCredentials: true, headers: { 'Content-Type': 'multipart/form-data' } });
                    fetchBrandData();
                  } catch (e) {
                    console.error(e);
                  }
                }}
              />
              <input
                type="file"
                data-testid="logo-upload-input"
                className="hidden"
                accept="image/*"
                onChange={async (e) => {
                  const file = e.target.files[0];
                  if (!file) return;
                  const formData = new FormData();
                  formData.append('file', file);
                  try {
                    await axios.post(`${API}/api/brands/upload-logo`, formData, { withCredentials: true, headers: { 'Content-Type': 'multipart/form-data' } });
                    fetchBrandData();
                  } catch (err) { console.error(err); }
                }}
              />
              <Button
                type="button"
                className="btn-secondary w-full mt-2 text-sm"
                onClick={() => document.querySelector('[data-testid="logo-upload-input"]').click()}
                data-testid="upload-logo-button"
              >
                <Upload className="w-4 h-4 mr-2" /> Upload Logo
              </Button>
            </div>

            {/* Banner Upload */}
            <div>
              <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">Brand Banner</label>
              {brandData.banner_url && (
                <div className="aspect-[3/1] overflow-hidden border border-white/10 mb-3">
                  <img
                    src={brandData.banner_url.startsWith('/api/') ? `${API}${brandData.banner_url}` : brandData.banner_url}
                    alt="Banner"
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <input
                type="file"
                data-testid="banner-upload-input"
                className="hidden"
                accept="image/*"
                onChange={async (e) => {
                  const file = e.target.files[0];
                  if (!file) return;
                  const formData = new FormData();
                  formData.append('file', file);
                  try {
                    await axios.post(`${API}/api/brands/upload-banner`, formData, { withCredentials: true, headers: { 'Content-Type': 'multipart/form-data' } });
                    fetchBrandData();
                  } catch (err) { console.error(err); }
                }}
              />
              <Button
                type="button"
                className="btn-secondary w-full text-sm"
                onClick={() => document.querySelector('[data-testid="banner-upload-input"]').click()}
                data-testid="upload-banner-button"
              >
                <Upload className="w-4 h-4 mr-2" /> Upload Banner
              </Button>
            </div>
          </div>
        </div>

        {/* Recent Orders */}
        {orders.length > 0 && (
          <div className="mb-12">
            <h3 className="text-lg font-bold text-white uppercase mb-4" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              <ShoppingCart className="w-5 h-5 inline mr-2" />
              Recent Orders
            </h3>
            <div className="space-y-3" data-testid="brand-orders">
              {orders.slice(0, 5).map((order) => (
                <div key={order.id} className="border border-white/10 bg-[#0A0A0A] p-4 flex items-center gap-4">
                  <div className="flex-1">
                    <h4 className="text-white font-medium">{order.product_name}</h4>
                    <p className="text-xs text-[#9CA3AF]">
                      Size: {order.size} · Buyer: {order.buyer_name} · {new Date(order.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[#39FF14] font-bold">£{order.brand_payout?.toFixed(2)}</p>
                    <p className="text-xs text-[#9CA3AF]">your payout</p>
                  </div>
                  <span className={`text-xs uppercase tracking-wider px-2 py-1 ${
                    order.status === 'paid' ? 'bg-green-500/10 text-green-400 border border-green-500/30' :
                    'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30'
                  }`}>
                    {order.status === 'paid' ? 'Confirmed' : order.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Boost Section */}
        {!brandData.is_boosted && (
          <div className="mb-12 border border-[#39FF14]/30 bg-[#39FF14]/5 p-6">
            <div className="flex items-start gap-4">
              <Zap className="w-8 h-8 text-[#39FF14] flex-shrink-0" />
              <div className="flex-1">
                <h3 className="text-xl font-bold text-white mb-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
                  BOOST YOUR BRAND
                </h3>
                <p className="text-[#9CA3AF] mb-4">
                  Get featured in the Boosted Brands section and increase your visibility to thousands of streetwear enthusiasts.
                </p>
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="border border-white/10 bg-[#0A0A0A] p-4">
                    <p className="text-lg font-bold text-white mb-1">Weekly</p>
                    <p className="text-2xl font-bold text-[#39FF14] mb-2">£9.99</p>
                    <p className="text-xs text-[#9CA3AF] mb-4">7 days featured</p>
                    <Button 
                      className="btn-secondary w-full text-sm" 
                      onClick={() => handleBoostBrand('weekly')}
                      data-testid="boost-weekly-button"
                    >
                      Select
                    </Button>
                  </div>
                  <div className="border border-[#39FF14]/50 bg-[#0A0A0A] p-4 relative">
                    <span className="absolute -top-3 left-4 bg-[#39FF14] text-black text-xs px-2 py-1 font-bold">POPULAR</span>
                    <p className="text-lg font-bold text-white mb-1">Monthly</p>
                    <p className="text-2xl font-bold text-[#39FF14] mb-2">£29.99</p>
                    <p className="text-xs text-[#9CA3AF] mb-4">30 days featured</p>
                    <Button 
                      className="btn-primary w-full text-sm" 
                      onClick={() => handleBoostBrand('monthly')}
                      data-testid="boost-monthly-button"
                    >
                      Select
                    </Button>
                  </div>
                  <div className="border border-white/10 bg-[#0A0A0A] p-4">
                    <p className="text-lg font-bold text-white mb-1">Quarterly</p>
                    <p className="text-2xl font-bold text-[#39FF14] mb-2">£69.99</p>
                    <p className="text-xs text-[#9CA3AF] mb-4">90 days featured</p>
                    <Button 
                      className="btn-secondary w-full text-sm" 
                      onClick={() => handleBoostBrand('quarterly')}
                      data-testid="boost-quarterly-button"
                    >
                      Select
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Products List */}
        <div>
          <h2 className="text-xl font-bold text-white uppercase mb-6" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            Your Products
          </h2>

          {products.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="brand-products-list">
              {products.map((product) => (
                <div key={product.id} className="border border-white/10 bg-[#0A0A0A] p-4 flex gap-4">
                  <div className="w-20 h-20 bg-[#0F0F0F] flex-shrink-0 overflow-hidden">
                    {product.images && product.images.length > 0 ? (
                      <img src={product.images[0]} alt={product.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#9CA3AF]">
                        <Package className="w-6 h-6" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-white font-medium truncate">{product.name}</h3>
                    <p className="text-[#39FF14] font-bold">£{product.price.toFixed(2)}</p>
                    <p className="text-xs text-[#9CA3AF]">Stock: {product.stock}</p>
                  </div>
                  <div className="flex flex-col gap-2">
                    <Link to={`/products/${product.id}`}>
                      <Button variant="ghost" size="sm" className="text-[#9CA3AF] hover:text-white p-2">
                        <ExternalLink className="w-4 h-4" />
                      </Button>
                    </Link>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-red-400 hover:text-red-300 p-2"
                      onClick={() => handleDeleteProduct(product.id)}
                      data-testid={`delete-product-${product.id}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="border border-white/10 bg-[#0A0A0A] p-12 text-center">
              <Package className="w-12 h-12 text-[#9CA3AF] mx-auto mb-4" />
              <p className="text-[#9CA3AF] mb-4">No products yet</p>
              <Button className="btn-primary" onClick={() => setAddProductOpen(true)}>
                Add Your First Product
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
