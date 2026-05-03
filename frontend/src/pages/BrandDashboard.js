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
  ShoppingCart,
  Truck
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
    stock: '',
    shipping_cost: '3.99'
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
        stock: parseInt(productForm.stock) || 0,
        shipping_cost: parseFloat(productForm.shipping_cost) || 0
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
        stock: '',
        shipping_cost: '3.99'
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

  const handlePrintLabel = async (orderId) => {
    try {
      const res = await axios.get(`${API}/api/orders/${orderId}/shipping-label`, { withCredentials: true });
      const label = res.data;
      
      // If Shippo generated a real label PDF, open it directly
      if (label.shippo_label_url) {
        window.open(label.shippo_label_url, '_blank');
        return;
      }
      
      // Otherwise generate mock printable label
      const printWindow = window.open('', '_blank', 'width=600,height=400');
      printWindow.document.write(`
        <html><head><title>Shipping Label - ${label.order_id}</title>
        <style>
          body { font-family: monospace; padding: 30px; background: #fff; color: #000; }
          .label { border: 3px solid #000; padding: 24px; max-width: 500px; margin: 0 auto; }
          .header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 12px; margin-bottom: 16px; }
          .header h1 { font-size: 18px; margin: 0; }
          .section { margin-bottom: 16px; }
          .section h3 { font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #666; margin-bottom: 4px; }
          .section p { font-size: 14px; margin: 2px 0; }
          .tracking { text-align: center; font-size: 18px; letter-spacing: 3px; padding: 12px; border: 2px dashed #000; margin-top: 16px; }
          .footer { text-align: center; font-size: 10px; color: #999; margin-top: 16px; }
          @media print { body { padding: 0; } }
        </style></head><body>
        <div class="label">
          <div class="header"><h1>UNVEILED THREADS</h1><p style="font-size:11px;">Shipping Label</p></div>
          <div class="section"><h3>From</h3><p><strong>${label.from.name}</strong></p><p>${label.from.location}</p></div>
          <div class="section"><h3>To</h3><p><strong>${label.to.name}</strong></p><p>${label.to.email}</p></div>
          <div class="section"><h3>Item</h3><p>${label.product} — Size: ${label.size}</p><p>Weight: ${label.weight}</p></div>
          ${label.tracking_number ? `<div class="tracking">${label.courier}: ${label.tracking_number}</div>` : ''}
          <div class="footer"><p>Date: ${label.date} · Order: ${label.order_id.slice(0,8)}</p></div>
        </div>
        <script>window.print();</script></body></html>
      `);
      printWindow.document.close();
    } catch (err) {
      alert('Failed to generate shipping label');
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
            <Link to="/brand/analytics">
              <Button className="btn-secondary" data-testid="view-analytics-button">
                <TrendingUp className="w-4 h-4 mr-2" />
                Analytics
              </Button>
            </Link>
            <Link to={`/brands/${brandData.id}`}>
              <Button className="btn-secondary" data-testid="view-profile-button">
                <ExternalLink className="w-4 h-4 mr-2" />
                View Profile
              </Button>
            </Link>
            <Link to="/brand/products">
              <Button className="btn-secondary" data-testid="my-listings-button">
                <Package className="w-4 h-4 mr-2" />
                My Listings
              </Button>
            </Link>
            <Link to="/brand/add-product">
              <Button className="btn-primary" data-testid="add-product-button">
                <Plus className="w-4 h-4 mr-2" />
                List Product
              </Button>
            </Link>
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
            <p className="text-lg font-bold text-[#39FF14]" data-testid="brand-status">
              {(() => {
                if (!brandData.is_boosted) return 'Active';
                const expiry = brandData.boosted_until ? new Date(brandData.boosted_until) : null;
                if (!expiry || expiry <= new Date()) return 'Active';
                const days = Math.max(1, Math.ceil((expiry - new Date()) / (1000 * 60 * 60 * 24)));
                return `Boosted · ${days}d left`;
              })()}
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
              Orders to Fulfil
            </h3>
            <div className="space-y-3" data-testid="brand-orders">
              {orders.slice(0, 10).map((order) => (
                <div key={order.id} className="border border-white/10 bg-[#0A0A0A] p-4">
                  <div className="flex items-center gap-4">
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
                      order.shipping_status === 'delivered' ? 'bg-green-500/10 text-green-400 border border-green-500/30' :
                      order.shipping_status === 'shipped' || order.shipping_status === 'in_transit' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30' :
                      order.status === 'paid' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30' :
                      'bg-[#9CA3AF]/10 text-[#9CA3AF] border border-[#9CA3AF]/30'
                    }`}>
                      {order.shipping_status === 'delivered' ? 'Delivered' :
                       order.shipping_status === 'shipped' ? 'Shipped' :
                       order.shipping_status === 'in_transit' ? 'In Transit' :
                       order.status === 'paid' ? 'Needs Shipping' : order.status}
                    </span>
                  </div>

                  {/* Ship action for paid orders without tracking */}
                  {order.status === 'paid' && !order.tracking_number && (
                    <ShipOrderForm orderId={order.id} onShipped={fetchBrandData} />
                  )}

                  {/* Tracking info if shipped */}
                  {order.tracking_number && (
                    <div className="mt-3 p-3 bg-[#0F0F0F] border border-white/5 flex items-center justify-between">
                      <div>
                        <p className="text-xs text-[#9CA3AF]">Tracking: <span className="text-white font-mono">{order.tracking_number}</span></p>
                        <p className="text-xs text-[#9CA3AF]">via {order.courier}</p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          className="btn-secondary text-[10px] py-1 px-2"
                          onClick={() => handlePrintLabel(order.id)}
                          data-testid={`print-label-${order.id}`}
                        >
                          Print Label
                        </Button>
                        {order.shipping_status !== 'delivered' && (
                          <ShippingStatusUpdate orderId={order.id} currentStatus={order.shipping_status} onUpdate={fetchBrandData} />
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Boost Section - always visible (supports initial boost + extend/renew) */}
        {(() => {
          const now = new Date();
          const expiry = brandData.boosted_until ? new Date(brandData.boosted_until) : null;
          const isActive = brandData.is_boosted && expiry && expiry > now;
          const daysLeft = isActive ? Math.max(1, Math.ceil((expiry - now) / (1000 * 60 * 60 * 24))) : 0;
          const formattedExpiry = expiry ? expiry.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : null;
          return (
            <div className="mb-12 border border-[#39FF14]/30 bg-[#39FF14]/5 p-6" data-testid="boost-section">
              <div className="flex items-start gap-4">
                <Zap className="w-8 h-8 text-[#39FF14] flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-white mb-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
                    {isActive ? 'EXTEND YOUR BOOST' : 'BOOST YOUR BRAND'}
                  </h3>
                  {isActive ? (
                    <div className="mb-4" data-testid="boost-active-info">
                      <p className="text-[#9CA3AF] mb-2">
                        Your brand is currently boosted. Top up now — new purchases stack on top of your current expiry date, you won't lose a day.
                      </p>
                      <div className="inline-flex items-center gap-2 border border-[#39FF14]/40 bg-[#0A0A0A] px-3 py-2">
                        <Zap className="w-4 h-4 text-[#39FF14]" />
                        <span className="text-sm text-white">
                          <span className="font-bold text-[#39FF14]">{daysLeft} day{daysLeft === 1 ? '' : 's'}</span> remaining · expires {formattedExpiry}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-[#9CA3AF] mb-4">
                      Get featured in the Boosted Brands section and increase your visibility to thousands of streetwear enthusiasts.
                    </p>
                  )}
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="border border-white/10 bg-[#0A0A0A] p-4">
                      <p className="text-lg font-bold text-white mb-1">Weekly</p>
                      <p className="text-2xl font-bold text-[#39FF14] mb-2">£9.99</p>
                      <p className="text-xs text-[#9CA3AF] mb-4">{isActive ? '+7 days added' : '7 days featured'}</p>
                      <Button
                        className="btn-secondary w-full text-sm"
                        onClick={() => handleBoostBrand('weekly')}
                        data-testid="boost-weekly-button"
                      >
                        {isActive ? 'Extend +7 Days' : 'Select'}
                      </Button>
                    </div>
                    <div className="border border-[#39FF14]/50 bg-[#0A0A0A] p-4 relative">
                      <span className="absolute -top-3 left-4 bg-[#39FF14] text-black text-xs px-2 py-1 font-bold">POPULAR</span>
                      <p className="text-lg font-bold text-white mb-1">Monthly</p>
                      <p className="text-2xl font-bold text-[#39FF14] mb-2">£29.99</p>
                      <p className="text-xs text-[#9CA3AF] mb-4">{isActive ? '+30 days added' : '30 days featured'}</p>
                      <Button
                        className="btn-primary w-full text-sm"
                        onClick={() => handleBoostBrand('monthly')}
                        data-testid="boost-monthly-button"
                      >
                        {isActive ? 'Extend +30 Days' : 'Select'}
                      </Button>
                    </div>
                    <div className="border border-white/10 bg-[#0A0A0A] p-4">
                      <p className="text-lg font-bold text-white mb-1">Quarterly</p>
                      <p className="text-2xl font-bold text-[#39FF14] mb-2">£69.99</p>
                      <p className="text-xs text-[#9CA3AF] mb-4">{isActive ? '+90 days added' : '90 days featured'}</p>
                      <Button
                        className="btn-secondary w-full text-sm"
                        onClick={() => handleBoostBrand('quarterly')}
                        data-testid="boost-quarterly-button"
                      >
                        {isActive ? 'Extend +90 Days' : 'Select'}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}

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

function ShipOrderForm({ orderId, onShipped }) {
  const [open, setOpen] = useState(false);
  const [trackingNumber, setTrackingNumber] = useState('');
  const [courier, setCourier] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleShip = async () => {
    if (!trackingNumber || !courier) return;
    setSubmitting(true);
    try {
      await axios.put(`${API}/api/orders/${orderId}/ship`, {
        tracking_number: trackingNumber,
        courier: courier
      }, { withCredentials: true });
      setOpen(false);
      onShipped();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to ship');
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) {
    return (
      <div className="mt-3">
        <Button className="btn-primary text-xs py-1 px-3" onClick={() => setOpen(true)} data-testid={`ship-order-${orderId}`}>
          <Truck className="w-3 h-3 mr-1" /> Mark as Shipped
        </Button>
      </div>
    );
  }

  return (
    <div className="mt-3 p-3 bg-[#0F0F0F] border border-white/10 space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Courier</label>
          <Select value={courier} onValueChange={setCourier}>
            <SelectTrigger className="w-full bg-transparent border-white/20 rounded-none text-white text-sm">
              <SelectValue placeholder="Select courier" />
            </SelectTrigger>
            <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
              {['Royal Mail', 'Evri', 'DPD', 'Yodel', 'UPS', 'FedEx', 'Other'].map((c) => (
                <SelectItem key={c} value={c} className="text-white hover:bg-white/10 rounded-none">{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">Tracking Number</label>
          <Input
            value={trackingNumber}
            onChange={(e) => setTrackingNumber(e.target.value)}
            className="input-brutalist text-sm"
            placeholder="e.g. RM123456789GB"
            data-testid={`tracking-input-${orderId}`}
          />
        </div>
      </div>
      <div className="flex gap-2">
        <Button className="btn-primary text-xs py-1 px-3" onClick={handleShip} disabled={submitting || !trackingNumber || !courier} data-testid={`confirm-ship-${orderId}`}>
          {submitting ? 'Shipping...' : 'Confirm Shipment'}
        </Button>
        <Button className="btn-secondary text-xs py-1 px-3" onClick={() => setOpen(false)}>Cancel</Button>
      </div>
    </div>
  );
}

function ShippingStatusUpdate({ orderId, currentStatus, onUpdate }) {
  const statuses = ['in_transit', 'out_for_delivery', 'delivered'];
  const labels = { in_transit: 'In Transit', out_for_delivery: 'Out for Delivery', delivered: 'Delivered' };
  const currentIdx = statuses.indexOf(currentStatus);
  const nextStatuses = statuses.filter((_, i) => i > currentIdx);

  if (nextStatuses.length === 0) return null;

  const handleUpdate = async (status) => {
    try {
      await axios.put(`${API}/api/orders/${orderId}/shipping-status`, { status }, { withCredentials: true });
      onUpdate();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update');
    }
  };

  return (
    <div className="flex gap-2">
      {nextStatuses.map((status) => (
        <Button
          key={status}
          className="btn-secondary text-[10px] py-1 px-2"
          onClick={() => handleUpdate(status)}
          data-testid={`status-${status}-${orderId}`}
        >
          {labels[status]}
        </Button>
      ))}
    </div>
  );
}
