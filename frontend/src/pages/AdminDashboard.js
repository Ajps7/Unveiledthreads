import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import { AdminApplicationsPanel } from '../components/admin-dashboard/AdminApplicationsPanel';
import { AdminDisputesPanel } from '../components/admin-dashboard/AdminDisputesPanel';
import { AdminModerationPanel } from '../components/admin-dashboard/AdminModerationPanel';
import { AdminBotwImageQueue } from '../components/admin-dashboard/AdminBotwImageQueue';
import { AdminBotwRotationPanel } from '../components/admin-dashboard/AdminBotwRotationPanel';
import {
  Shield,
  Users,
  Package,
  ShoppingBag,
  Clock,
  Zap,
  Crown,
  Loader2,
  ExternalLink,
  Trash2,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AdminDashboard() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [sellerCap, setSellerCap] = useState(null);
  const [applications, setApplications] = useState([]);
  const [disputes, setDisputes] = useState([]);
  const [disputeProcessing, setDisputeProcessing] = useState(null);
  const [brands, setBrands] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [processing, setProcessing] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      navigate('/login');
      return;
    }
    if (user.role !== 'admin') {
      navigate('/');
      return;
    }
    fetchData();
  }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const [statsRes, brandsRes, productsRes, capRes, disputesRes] = await Promise.all([
        axios.get(`${API}/api/admin/stats`, { withCredentials: true }),
        axios.get(`${API}/api/brands`),
        axios.get(`${API}/api/products?limit=200`),
        axios.get(`${API}/api/admin/seller-cap`, { withCredentials: true }),
        axios.get(`${API}/api/admin/disputes?status=open`, { withCredentials: true }),
      ]);
      setStats(statsRes.data);
      setBrands(brandsRes.data);
      setProducts(productsRes.data);
      setSellerCap(capRes.data);
      setDisputes(disputesRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefundDispute = async (disputeId) => {
    if (!window.confirm('Issue a FULL REFUND and reverse funds from the seller? This cannot be undone.')) return;
    setDisputeProcessing(disputeId);
    try {
      const res = await axios.post(
        `${API}/api/admin/disputes/${disputeId}/refund`,
        { note: 'Approved under Buyer Protection (non-delivery).' },
        { withCredentials: true }
      );
      const errInfo = res.data?.stripe_error;
      alert(errInfo
        ? `Dispute marked refunded. ⚠️ Stripe refund failed: ${errInfo}. Process the refund manually in Stripe.`
        : 'Refund issued.');
      await fetchData();
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to refund');
    } finally {
      setDisputeProcessing(null);
    }
  };

  const handleCloseDispute = async (disputeId) => {
    const reason = window.prompt('Reason for closing (will be shown to the buyer):');
    if (!reason || reason.trim().length < 5) {
      alert('Please provide a closing reason of at least 5 characters.');
      return;
    }
    setDisputeProcessing(disputeId);
    try {
      await axios.post(
        `${API}/api/admin/disputes/${disputeId}/close`,
        { note: reason.trim() },
        { withCredentials: true }
      );
      await fetchData();
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to close dispute');
    } finally {
      setDisputeProcessing(null);
    }
  };

  const handleDeleteBrand = async (brand) => {
    const confirmText = `delete ${brand.brand_name}`;
    const answer = window.prompt(
      `HARD DELETE: This will permanently remove "${brand.brand_name}", its products & drafts, unpaid orders, reviews, AND the owner's user account, messages, notifications and files.\n\nType "${confirmText}" to confirm:`
    );
    if (answer !== confirmText) {
      if (answer !== null) alert('Confirmation text did not match. Brand was NOT deleted.');
      return;
    }
    setDeletingId(`brand-${brand.id}`);
    try {
      await axios.delete(`${API}/api/admin/brands/${brand.id}?delete_user=true`, { withCredentials: true });
      await fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete brand.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleToggleFounding = async (brand) => {
    const nextState = !brand.is_founding;
    const verb = nextState ? 'ADD' : 'REMOVE';
    if (!window.confirm(`${verb} the Founding Brand badge on "${brand.brand_name}"?`)) return;
    setDeletingId(`founding-${brand.id}`);
    try {
      await axios.post(`${API}/api/admin/brands/${brand.id}/toggle-founding`, {}, { withCredentials: true });
      await fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to toggle founding flag.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteProduct = async (product) => {
    if (!window.confirm(`Delete "${product.name}" (£${product.price}) by ${product.brand_name}?`)) return;
    setDeletingId(`product-${product.id}`);
    try {
      await axios.delete(`${API}/api/admin/products/${product.id}`, { withCredentials: true });
      await fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete product.');
    } finally {
      setDeletingId(null);
    }
  };

  const fetchApplications = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/api/admin/applications?status=${statusFilter}`, { withCredentials: true });
      setApplications(response.data);
    } catch (error) {
      console.error('Error fetching applications:', error);
    }
  }, [statusFilter]);

  useEffect(() => {
    if (!authLoading && user?.role === 'admin') {
      fetchApplications();
    }
  }, [user, authLoading, fetchApplications]);

  const handleApprove = async (applicationId) => {
    setProcessing(applicationId);
    try {
      await axios.post(`${API}/api/admin/applications/${applicationId}/approve`, {}, { withCredentials: true });
      fetchApplications();
      fetchData();
    } catch (error) {
      console.error('Error approving application:', error);
      alert('Failed to approve application');
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async (applicationId) => {
    if (!window.confirm('Are you sure you want to reject this application?')) return;
    
    setProcessing(applicationId);
    try {
      await axios.post(`${API}/api/admin/applications/${applicationId}/reject`, {}, { withCredentials: true });
      fetchApplications();
      fetchData();
    } catch (error) {
      console.error('Error rejecting application:', error);
      alert('Failed to reject application');
    } finally {
      setProcessing(null);
    }
  };

  const handleSetBrandOfWeek = async (brandId) => {
    try {
      await axios.post(`${API}/api/admin/brands/${brandId}/set-brand-of-week`, {}, { withCredentials: true });
      fetchData();
      alert('Brand of the week updated!');
    } catch (error) {
      console.error('Error setting brand of week:', error);
      alert('Failed to set brand of the week');
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

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      <div className="max-w-7xl mx-auto px-6 md:px-12 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Shield className="w-8 h-8 text-[#39FF14]" />
          <h1 
            className="text-2xl md:text-3xl font-black tracking-tighter uppercase text-white"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="admin-dashboard-title"
          >
            Admin Panel
          </h1>
        </div>

        {/* MVP Seller Cap */}
        {sellerCap && (
          <div
            className={`mb-6 border p-5 flex items-center justify-between gap-4 flex-wrap ${
              sellerCap.cap_reached
                ? 'border-red-500/40 bg-red-500/5'
                : sellerCap.remaining <= 5
                ? 'border-yellow-500/40 bg-yellow-500/5'
                : 'border-[#39FF14]/30 bg-[#39FF14]/5'
            }`}
            data-testid="seller-cap-banner"
          >
            <div className="flex items-center gap-4">
              <div
                className={`text-3xl font-black tabular-nums ${
                  sellerCap.cap_reached
                    ? 'text-red-300'
                    : sellerCap.remaining <= 5
                    ? 'text-yellow-300'
                    : 'text-[#39FF14]'
                }`}
                style={{ fontFamily: 'Clash Display, sans-serif' }}
                data-testid="seller-cap-count"
              >
                {sellerCap.used} / {sellerCap.max}
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-[#C0C0C0] font-bold mb-1">
                  MVP Seller Slots
                </p>
                <p className="text-sm text-[#9CA3AF]">
                  {sellerCap.cap_reached
                    ? `Cap reached. ${sellerCap.waitlisted} application(s) waitlisted. Remove a brand or raise MAX_SELLER_ACCOUNTS to open a slot.`
                    : sellerCap.remaining <= 5
                    ? `Only ${sellerCap.remaining} slot(s) left before applications go to the waitlist.`
                    : `${sellerCap.remaining} slot(s) available before applications go to the waitlist.`}
                </p>
              </div>
            </div>
            {sellerCap.waitlisted > 0 && (
              <span
                className="text-xs uppercase tracking-wider px-3 py-1 bg-yellow-500/10 text-yellow-300 border border-yellow-500/30"
                data-testid="seller-cap-waitlisted"
              >
                {sellerCap.waitlisted} waitlisted
              </span>
            )}
          </div>
        )}

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-12">
            <div className="border border-white/10 p-6 bg-[#0A0A0A]">
              <Users className="w-6 h-6 text-[#9CA3AF] mb-2" />
              <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-1">Buyers</p>
              <p className="text-2xl font-bold text-white" data-testid="stat-buyers">{stats.total_buyers ?? 0}</p>
              <p className="text-[10px] text-[#6B7280] uppercase tracking-wider mt-1" data-testid="stat-users-breakdown">
                {stats.total_users} total acc · {stats.total_brand_owners ?? 0} brand owner{(stats.total_brand_owners ?? 0) === 1 ? '' : 's'}
              </p>
            </div>
            <div className="border border-white/10 p-6 bg-[#0A0A0A]">
              <Package className="w-6 h-6 text-[#9CA3AF] mb-2" />
              <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-1">Total Brands</p>
              <p className="text-2xl font-bold text-white" data-testid="stat-brands">{stats.total_brands}</p>
            </div>
            <div className="border border-white/10 p-6 bg-[#0A0A0A]">
              <ShoppingBag className="w-6 h-6 text-[#9CA3AF] mb-2" />
              <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-1">Products</p>
              <p className="text-2xl font-bold text-white" data-testid="stat-products">{stats.total_products}</p>
            </div>
            <div className="border border-[#39FF14]/30 p-6 bg-[#39FF14]/5">
              <Clock className="w-6 h-6 text-[#39FF14] mb-2" />
              <p className="text-xs text-[#39FF14] uppercase tracking-wider mb-1">Pending</p>
              <p className="text-2xl font-bold text-[#39FF14]" data-testid="stat-pending">{stats.pending_applications}</p>
            </div>
            <div className="border border-white/10 p-6 bg-[#0A0A0A]">
              <Zap className="w-6 h-6 text-[#9CA3AF] mb-2" />
              <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-1">Boosted</p>
              <p className="text-2xl font-bold text-white" data-testid="stat-boosted">{stats.boosted_brands}</p>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-8">
          <AdminApplicationsPanel
            applications={applications}
            statusFilter={statusFilter}
            setStatusFilter={setStatusFilter}
            processing={processing}
            onApprove={handleApprove}
            onReject={handleReject}
          />

          <AdminDisputesPanel
            disputes={disputes}
            disputeProcessing={disputeProcessing}
            onRefund={handleRefundDispute}
            onClose={handleCloseDispute}
          />

          <AdminModerationPanel />

          <AdminBotwImageQueue />

          <AdminBotwRotationPanel />

          {/* Brands Management */}
          <div>
            <h2 
              className="text-xl font-bold uppercase text-white mb-6"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
            >
              Set Brand of the Week
            </h2>

            <div className="space-y-3" data-testid="brands-list">
              {brands.map((brand) => (
                <div key={brand.id} className="border border-white/10 bg-[#0A0A0A] p-4 flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full overflow-hidden bg-[#0F0F0F] flex-shrink-0">
                    {brand.logo_url ? (
                      <img src={brand.logo_url} alt={brand.brand_name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#39FF14] font-bold">
                        {brand.brand_name.charAt(0)}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-white font-medium truncate">{brand.brand_name}</h3>
                      {brand.is_brand_of_week && (
                        <Crown className="w-4 h-4 text-[#39FF14]" />
                      )}
                      {brand.is_boosted && (
                        <Zap className="w-4 h-4 text-[#39FF14]" />
                      )}
                      {brand.is_founding && (
                        <span className="text-[9px] uppercase tracking-[0.15em] px-2 py-0.5 bg-white/5 border border-[#39FF14]/30 text-[#39FF14]" data-testid={`founding-flag-${brand.id}`}>
                          Founding
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#9CA3AF]">{brand.location}</p>
                  </div>
                  <div className="flex gap-2 flex-wrap justify-end">
                    <Link to={`/brands/${brand.id}`}>
                      <Button variant="ghost" size="sm" className="text-[#9CA3AF] hover:text-white p-2">
                        <ExternalLink className="w-4 h-4" />
                      </Button>
                    </Link>
                    <Button
                      variant="ghost"
                      size="sm"
                      className={`text-xs py-1 px-3 border rounded-none ${
                        brand.is_founding
                          ? 'border-yellow-500/40 text-yellow-300 hover:bg-yellow-500/10'
                          : 'border-[#39FF14]/40 text-[#39FF14] hover:bg-[#39FF14]/10'
                      }`}
                      onClick={() => handleToggleFounding(brand)}
                      disabled={deletingId === `founding-${brand.id}`}
                      data-testid={`toggle-founding-${brand.id}`}
                      title={brand.is_founding ? 'Remove Founding Brand badge' : 'Mark as Founding Brand'}
                    >
                      {deletingId === `founding-${brand.id}`
                        ? <Loader2 className="w-3 h-3 animate-spin" />
                        : brand.is_founding ? 'Un-Founding' : 'Make Founding'}
                    </Button>
                    {!brand.is_brand_of_week && (
                      <Button 
                        className="btn-boost text-xs py-1 px-3"
                        onClick={() => handleSetBrandOfWeek(brand.id)}
                        data-testid={`set-bow-${brand.id}`}
                      >
                        <Crown className="w-3 h-3 mr-1" />
                        Set BOW
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-400 hover:text-red-300 hover:bg-red-500/10 p-2"
                      onClick={() => handleDeleteBrand(brand)}
                      disabled={deletingId === `brand-${brand.id}`}
                      data-testid={`delete-brand-${brand.id}`}
                      title="Delete brand and all its products"
                    >
                      {deletingId === `brand-${brand.id}`
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Trash2 className="w-4 h-4" />}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* All Products — admin can delete any listing */}
        <div className="mt-12 border border-white/10 bg-[#0A0A0A] p-6">
          <h2
            className="text-xl font-bold text-white uppercase mb-4 flex items-center gap-2"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="admin-products-heading"
          >
            <Package className="w-5 h-5 text-[#39FF14]" />
            All Products ({products.length})
          </h2>
          {products.length === 0 ? (
            <p className="text-sm text-[#9CA3AF]">No products listed.</p>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto" data-testid="admin-products-list">
              {products.map((p) => (
                <div key={p.id} className="border border-white/5 bg-[#0F0F0F] p-3 flex items-center gap-3">
                  <div className="w-12 h-12 overflow-hidden bg-[#050505] flex-shrink-0">
                    {p.images?.[0] ? (
                      <img
                        src={p.images[0].startsWith('/api/') ? `${API}${p.images[0]}` : p.images[0]}
                        alt={p.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#39FF14]">
                        <Package className="w-4 h-4" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-sm font-medium truncate">{p.name}</p>
                    <p className="text-xs text-[#9CA3AF]">
                      {p.brand_name} · £{p.price?.toFixed?.(2) ?? p.price} · stock {p.stock ?? 0}
                    </p>
                  </div>
                  <Link to={`/products/${p.id}`}>
                    <Button variant="ghost" size="sm" className="text-[#9CA3AF] hover:text-white p-2">
                      <ExternalLink className="w-4 h-4" />
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-400 hover:text-red-300 hover:bg-red-500/10 p-2"
                    onClick={() => handleDeleteProduct(p)}
                    disabled={deletingId === `product-${p.id}`}
                    data-testid={`delete-product-${p.id}`}
                  >
                    {deletingId === `product-${p.id}`
                      ? <Loader2 className="w-4 h-4 animate-spin" />
                      : <Trash2 className="w-4 h-4" />}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
