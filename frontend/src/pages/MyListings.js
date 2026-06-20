import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import Header from '../components/Header';
import ImageUpload from '../components/ImageUpload';
import {
  Plus, Package, Edit, Trash2, ExternalLink, Eye, Loader2, ArrowLeft, Search, X, Tag, RotateCcw
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

const ALL_SIZES = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'One Size'];

export default function MyListings() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [brandData, setBrandData] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [editProduct, setEditProduct] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'dead-stock'
  const [quota, setQuota] = useState(null);
  const [deadStockDialog, setDeadStockDialog] = useState(null); // {product, mode}
  const [deadStockPrice, setDeadStockPrice] = useState('');
  const [movingToDeadStock, setMovingToDeadStock] = useState(false);
  const [requestDialogOpen, setRequestDialogOpen] = useState(false);
  const [requestedQuota, setRequestedQuota] = useState('20');
  const [requestReason, setRequestReason] = useState('');

  useEffect(() => {
    if (authLoading) return;
    if (!user) { navigate('/login'); return; }
    if (user.role !== 'brand' && user.role !== 'admin') { navigate('/apply'); return; }
    fetchData();
  }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const appRes = await axios.get(`${API}/api/brands/my-application`, { withCredentials: true });
      if (appRes.data?.brand_profile) {
        setBrandData(appRes.data.brand_profile);
        const prodRes = await axios.get(`${API}/api/products?brand_id=${appRes.data.brand_profile.id}`);
        setProducts(prodRes.data);
        // Quota for dead stock
        try {
          const qRes = await axios.get(`${API}/api/dead-stock/my-quota`, { withCredentials: true });
          setQuota(qRes.data);
        } catch (qe) {
          console.warn('Failed to load quota:', qe);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const openMoveToDeadStock = (product) => {
    setDeadStockDialog({ product, mode: 'add' });
    setDeadStockPrice(product.price.toString());
  };

  const handleMoveToDeadStock = async () => {
    if (!deadStockDialog?.product) return;
    const newPrice = parseFloat(deadStockPrice);
    if (!newPrice || newPrice <= 0) {
      alert('Enter a valid price');
      return;
    }
    setMovingToDeadStock(true);
    try {
      await axios.post(
        `${API}/api/products/${deadStockDialog.product.id}/dead-stock`,
        { new_price: newPrice },
        { withCredentials: true }
      );
      setDeadStockDialog(null);
      setDeadStockPrice('');
      await fetchData();
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to move to dead stock');
    } finally {
      setMovingToDeadStock(false);
    }
  };

  const handleRemoveFromDeadStock = async (product) => {
    if (!window.confirm(`Restore "${product.name}" to the main shop at £${(product.original_price || product.price).toFixed(2)}?`)) return;
    try {
      await axios.delete(`${API}/api/products/${product.id}/dead-stock`, { withCredentials: true });
      await fetchData();
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to restore product');
    }
  };

  const handleRequestQuota = async () => {
    const n = parseInt(requestedQuota, 10);
    if (!n || n <= (quota?.quota || 10)) {
      alert(`Requested quota must be greater than current (${quota?.quota || 10})`);
      return;
    }
    try {
      await axios.post(
        `${API}/api/dead-stock/quota-request`,
        { requested_quota: n, reason: requestReason },
        { withCredentials: true }
      );
      setRequestDialogOpen(false);
      setRequestReason('');
      await fetchData();
      alert('Quota request submitted. We will email you once reviewed.');
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to submit request');
    }
  };

  const handleDelete = async (productId) => {
    if (!window.confirm('Delete this listing? This cannot be undone.')) return;
    try {
      await axios.delete(`${API}/api/products/${productId}`, { withCredentials: true });
      setProducts(products.filter(p => p.id !== productId));
    } catch (e) {
      alert('Failed to delete');
    }
  };

  const openEdit = (product) => {
    setEditProduct(product);
    setEditForm({
      name: product.name,
      description: product.description,
      price: product.price.toString(),
      shipping_cost: (product.shipping_cost || 0).toString(),
      category: product.category,
      stock: product.stock.toString(),
      sizes: product.sizes || [],
      images: product.images || [],
    });
  };

  const handleSaveEdit = async () => {
    if (!editProduct) return;
    setSaving(true);
    try {
      await axios.put(`${API}/api/products/${editProduct.id}`, {
        name: editForm.name,
        description: editForm.description,
        price: parseFloat(editForm.price),
        shipping_cost: parseFloat(editForm.shipping_cost) || 0,
        category: editForm.category,
        stock: parseInt(editForm.stock),
        sizes: editForm.sizes,
        images: editForm.images,
      }, { withCredentials: true });
      setEditProduct(null);
      fetchData();
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const filteredProducts = products
    .filter((p) => (activeTab === 'dead-stock' ? p.is_dead_stock : !p.is_dead_stock))
    .filter((p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.category.toLowerCase().includes(searchQuery.toLowerCase())
    );

  const deadStockCount = products.filter((p) => p.is_dead_stock).length;
  const liveCount = products.filter((p) => !p.is_dead_stock).length;

  if (authLoading || loading) {
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
      <div className="max-w-6xl mx-auto px-6 md:px-12 py-8">
        <Link to="/brand/dashboard" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to dashboard
        </Link>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl md:text-3xl font-black tracking-tighter uppercase text-white" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="listings-title">
              MY LISTINGS
            </h1>
            <p className="text-sm text-[#9CA3AF]">
              {liveCount} live · {deadStockCount} in dead stock
            </p>
          </div>
          <Link to="/brand/add-product">
            <Button className="btn-primary" data-testid="add-new-product-button">
              <Plus className="w-4 h-4 mr-2" /> List New Product
            </Button>
          </Link>
        </div>

        {/* Dead Stock Quota Banner */}
        {quota && (
          <div
            className={`mb-6 border p-4 flex items-center justify-between gap-3 flex-wrap ${
              quota.remaining === 0
                ? 'border-yellow-500/40 bg-yellow-500/5'
                : 'border-[#39FF14]/30 bg-[#39FF14]/5'
            }`}
            data-testid="dead-stock-quota-banner"
          >
            <div className="flex items-center gap-3">
              <Tag className={`w-5 h-5 ${quota.remaining === 0 ? 'text-yellow-300' : 'text-[#39FF14]'}`} />
              <div>
                <p className="text-xs uppercase tracking-wider text-[#C0C0C0] font-bold mb-0.5">
                  Dead Stock Slots
                </p>
                <p className="text-sm text-white">
                  <span className="font-bold" data-testid="quota-used">{quota.used}</span>
                  <span className="text-[#9CA3AF]"> / </span>
                  <span data-testid="quota-total">{quota.quota}</span>
                  <span className="text-[#9CA3AF] text-xs ml-2">
                    {quota.remaining > 0
                      ? `(${quota.remaining} available)`
                      : '— at capacity'}
                  </span>
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {quota.pending_request?.status === 'pending' ? (
                <span className="text-xs text-yellow-300 uppercase tracking-wider px-3 py-1 bg-yellow-500/10 border border-yellow-500/30">
                  Request pending: {quota.pending_request.requested_quota}
                </span>
              ) : (
                <Button
                  variant="ghost"
                  className="text-[#39FF14] hover:bg-[#39FF14]/10 text-xs uppercase tracking-wider rounded-none"
                  onClick={() => setRequestDialogOpen(true)}
                  data-testid="request-quota-button"
                >
                  Request more slots
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 border-b border-white/10 mb-6" data-testid="listings-tabs">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-5 py-3 text-xs uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'all' ? 'border-[#39FF14] text-[#39FF14]' : 'border-transparent text-[#9CA3AF] hover:text-white'
            }`}
            data-testid="tab-all"
          >
            Active ({liveCount})
          </button>
          <button
            onClick={() => setActiveTab('dead-stock')}
            className={`px-5 py-3 text-xs uppercase tracking-wider transition-colors border-b-2 flex items-center gap-2 ${
              activeTab === 'dead-stock' ? 'border-[#39FF14] text-[#39FF14]' : 'border-transparent text-[#9CA3AF] hover:text-white'
            }`}
            data-testid="tab-dead-stock"
          >
            <Tag className="w-3 h-3" /> Dead Stock ({deadStockCount})
          </button>
        </div>

        {/* Search */}
        {products.length > 0 && (
          <div className="flex gap-2 mb-6 max-w-md">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-brutalist"
              placeholder="Search your listings..."
              data-testid="listings-search"
            />
            {searchQuery && (
              <Button variant="ghost" onClick={() => setSearchQuery('')} className="text-[#9CA3AF] hover:text-white">
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>
        )}

        {/* Products Grid */}
        {filteredProducts.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="listings-grid">
            {filteredProducts.map((product) => {
              const imgSrc = product.images?.[0]
                ? (product.images[0].startsWith('/api/') ? `${API}${product.images[0]}` : product.images[0])
                : null;

              return (
                <div key={product.id} className="border border-white/10 bg-[#0A0A0A] overflow-hidden" data-testid={`listing-${product.id}`}>
                  <div className="aspect-[4/3] overflow-hidden bg-[#0F0F0F] relative">
                    {imgSrc ? (
                      <img src={imgSrc} alt={product.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#9CA3AF]">
                        <Package className="w-8 h-8" />
                      </div>
                    )}
                    <div className="absolute top-2 right-2 flex gap-1">
                      <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 ${
                        product.stock > 0 ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'
                      }`}>
                        {product.stock > 0 ? `${product.stock} in stock` : 'Out of stock'}
                      </span>
                    </div>
                  </div>

                  <div className="p-4">
                    <h3 className="text-white font-medium mb-1 line-clamp-1">{product.name}</h3>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-baseline gap-2 flex-wrap">
                        <span className="text-[#39FF14] font-bold">£{product.price.toFixed(2)}</span>
                        {product.is_dead_stock && product.original_price && product.original_price > product.price && (
                          <span className="text-xs text-[#6B7280] line-through">£{Number(product.original_price).toFixed(2)}</span>
                        )}
                        {product.is_dead_stock && (product.discount_percent || 0) > 0 && (
                          <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 bg-[#39FF14] text-black font-bold">
                            -{product.discount_percent}%
                          </span>
                        )}
                      </div>
                      <span className="badge-category text-[10px]">{product.category}</span>
                    </div>
                    <p className="text-xs text-[#9CA3AF] mb-3">
                      Sizes: {product.sizes?.join(', ') || 'None'}
                      {product.shipping_cost > 0 ? ` · Shipping: £${product.shipping_cost.toFixed(2)}` : ' · Free shipping'}
                    </p>

                    <div className="flex gap-2 mb-2">
                      <Button
                        className="btn-secondary flex-1 text-xs py-1"
                        onClick={() => openEdit(product)}
                        data-testid={`edit-${product.id}`}
                      >
                        <Edit className="w-3 h-3 mr-1" /> Edit
                      </Button>
                      <Link to={`/products/${product.id}`} className="flex-1">
                        <Button className="btn-secondary w-full text-xs py-1">
                          <Eye className="w-3 h-3 mr-1" /> View
                        </Button>
                      </Link>
                      <Button
                        variant="ghost"
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10 px-2"
                        onClick={() => handleDelete(product.id)}
                        data-testid={`delete-${product.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                    {product.is_dead_stock ? (
                      <Button
                        variant="ghost"
                        className="w-full text-xs py-1 text-[#9CA3AF] hover:text-white hover:bg-white/5 rounded-none border border-white/10"
                        onClick={() => handleRemoveFromDeadStock(product)}
                        data-testid={`restore-${product.id}`}
                      >
                        <RotateCcw className="w-3 h-3 mr-1" /> Restore to Main Shop
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        className="w-full text-xs py-1 text-[#39FF14] hover:bg-[#39FF14]/10 rounded-none border border-[#39FF14]/30"
                        onClick={() => openMoveToDeadStock(product)}
                        disabled={quota && quota.remaining <= 0}
                        data-testid={`move-dead-stock-${product.id}`}
                      >
                        <Tag className="w-3 h-3 mr-1" />
                        {quota && quota.remaining <= 0 ? 'Dead Stock Full' : 'Move to Dead Stock'}
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : products.length === 0 ? (
          <div className="border border-white/10 bg-[#0A0A0A] p-16 text-center">
            <Package className="w-16 h-16 text-[#9CA3AF] mx-auto mb-4" />
            <h3 className="text-lg text-white font-bold mb-2">No listings yet</h3>
            <p className="text-[#9CA3AF] mb-6">Start selling by creating your first product listing</p>
            <Link to="/brand/add-product">
              <Button className="btn-primary" data-testid="first-listing-button">
                <Plus className="w-4 h-4 mr-2" /> List Your First Product
              </Button>
            </Link>
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-[#9CA3AF]">No listings match "{searchQuery}"</p>
          </div>
        )}
      </div>

      {/* Edit Dialog */}
      <Dialog open={!!editProduct} onOpenChange={(open) => { if (!open) setEditProduct(null); }}>
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
              {(editForm.images || []).length > 0 && (
                <div className="grid grid-cols-4 gap-2 mb-2">
                  {editForm.images.map((img, i) => (
                    <div key={img} className="relative group aspect-square overflow-hidden border border-white/10 bg-[#0F0F0F]">
                      <img src={img.startsWith('/api/') ? `${API}${img}` : img} alt="" className="w-full h-full object-cover" />
                      <button type="button" onClick={() => setEditForm({ ...editForm, images: editForm.images.filter((_, idx) => idx !== i) })} className="absolute top-1 right-1 bg-black/70 text-white p-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <ImageUpload multiple label="Upload More" onUpload={(urls) => setEditForm({ ...editForm, images: [...(editForm.images || []), ...urls] })} />
            </div>
            <div className="flex gap-3 pt-2">
              <Button className="btn-primary flex-1" onClick={handleSaveEdit} disabled={saving} data-testid="save-edit-button">
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
              <Button className="btn-secondary" onClick={() => setEditProduct(null)}>Cancel</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Move to Dead Stock Dialog */}
      <Dialog open={!!deadStockDialog} onOpenChange={(open) => { if (!open) { setDeadStockDialog(null); setDeadStockPrice(''); } }}>
        <DialogContent className="bg-[#0F0F0F] border-white/10 rounded-none max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-white uppercase flex items-center gap-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              <Tag className="w-5 h-5 text-[#39FF14]" /> Move to Dead Stock
            </DialogTitle>
          </DialogHeader>
          {deadStockDialog?.product && (
            <div className="space-y-4 mt-4">
              <div className="border border-white/10 bg-[#0A0A0A] p-3">
                <p className="text-xs uppercase tracking-wider text-[#9CA3AF] mb-1">Product</p>
                <p className="text-white text-sm">{deadStockDialog.product.name}</p>
                <p className="text-xs text-[#9CA3AF] mt-1">Current price: £{deadStockDialog.product.price.toFixed(2)}</p>
              </div>
              <div>
                <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">
                  New Dead Stock Price (£)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  value={deadStockPrice}
                  onChange={(e) => setDeadStockPrice(e.target.value)}
                  className="input-brutalist"
                  data-testid="dead-stock-price-input"
                  placeholder="Leave as current to keep price the same"
                />
                <p className="text-xs text-[#9CA3AF] mt-2">
                  The original price (£{deadStockDialog.product.price.toFixed(2)}) will be shown
                  alongside the new one with a &quot;-X%&quot; badge so buyers can see the saving.
                  Set the same price to keep it unchanged.
                </p>
              </div>
              <div className="flex gap-3 pt-2">
                <Button
                  className="btn-primary flex-1"
                  onClick={handleMoveToDeadStock}
                  disabled={movingToDeadStock}
                  data-testid="confirm-dead-stock-button"
                >
                  {movingToDeadStock ? 'Moving…' : 'Move to Dead Stock'}
                </Button>
                <Button className="btn-secondary" onClick={() => { setDeadStockDialog(null); setDeadStockPrice(''); }}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Request Quota Dialog */}
      <Dialog open={requestDialogOpen} onOpenChange={setRequestDialogOpen}>
        <DialogContent className="bg-[#0F0F0F] border-white/10 rounded-none max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-white uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Request More Slots
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <p className="text-sm text-[#9CA3AF]">
              Default Dead Stock cap is <span className="text-white font-semibold">{quota?.quota || 10}</span> items.
              Ask the admin team for more if you&apos;ve got a bigger archive to shift.
            </p>
            <div>
              <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">
                Requested quota
              </label>
              <Input
                type="number"
                value={requestedQuota}
                onChange={(e) => setRequestedQuota(e.target.value)}
                className="input-brutalist"
                data-testid="requested-quota-input"
                min={(quota?.quota || 10) + 1}
                max={200}
              />
            </div>
            <div>
              <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">
                Reason (optional)
              </label>
              <Textarea
                value={requestReason}
                onChange={(e) => setRequestReason(e.target.value)}
                className="input-brutalist min-h-[80px] resize-none"
                placeholder="e.g. clearing out three past collections..."
                data-testid="quota-reason-input"
              />
            </div>
            <div className="flex gap-3 pt-2">
              <Button className="btn-primary flex-1" onClick={handleRequestQuota} data-testid="submit-quota-request-button">
                Submit Request
              </Button>
              <Button className="btn-secondary" onClick={() => setRequestDialogOpen(false)}>Cancel</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
