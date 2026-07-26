import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import Header from '../components/Header';
import { EditListingDialog } from '../components/my-listings/EditListingDialog';
import { MoveToDeadStockDialog } from '../components/my-listings/MoveToDeadStockDialog';
import { RequestQuotaDialog } from '../components/my-listings/RequestQuotaDialog';
import {
  Plus, Package, Edit, Trash2, ExternalLink, Eye, Loader2, ArrowLeft, Search, X, Tag, RotateCcw
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

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

  const fetchData = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { navigate('/login'); return; }
    if (user.role !== 'brand' && user.role !== 'admin') { navigate('/apply'); return; }
    fetchData();
  }, [user, authLoading, navigate, fetchData]);

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
            <p className="text-[#9CA3AF]">No listings match &quot;{searchQuery}&quot;</p>
          </div>
        )}
      </div>

      <EditListingDialog
        editProduct={editProduct}
        editForm={editForm}
        setEditForm={setEditForm}
        saving={saving}
        onSave={handleSaveEdit}
        onClose={() => setEditProduct(null)}
      />

      <MoveToDeadStockDialog
        dialog={deadStockDialog}
        price={deadStockPrice}
        setPrice={setDeadStockPrice}
        moving={movingToDeadStock}
        onConfirm={handleMoveToDeadStock}
        onClose={() => { setDeadStockDialog(null); setDeadStockPrice(''); }}
      />

      <RequestQuotaDialog
        open={requestDialogOpen}
        onOpenChange={setRequestDialogOpen}
        quota={quota}
        requestedQuota={requestedQuota}
        setRequestedQuota={setRequestedQuota}
        reason={requestReason}
        setReason={setRequestReason}
        onSubmit={handleRequestQuota}
      />
    </div>
  );
}
