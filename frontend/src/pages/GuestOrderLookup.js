import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import axios from 'axios';
import Header from '../components/Header';
import { Loader2, Package, Truck, CheckCircle2, Clock, AlertTriangle, ArrowLeft } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_META = {
  paid: { label: 'Paid — awaiting dispatch', Icon: Clock, color: 'text-yellow-300' },
  preorder_paid: { label: 'Pre-order confirmed', Icon: Clock, color: 'text-yellow-300' },
  shipped: { label: 'Shipped', Icon: Truck, color: 'text-[#39FF14]' },
  delivered: { label: 'Delivered', Icon: CheckCircle2, color: 'text-[#39FF14]' },
  initiated: { label: 'Payment pending', Icon: Clock, color: 'text-[#9CA3AF]' },
  refunded: { label: 'Refunded', Icon: AlertTriangle, color: 'text-red-400' },
};

/**
 * Public order tracking page for guest buyers. Reads `order_id` + `token`
 * from the URL (both come from the confirmation-email link) and calls
 * the public lookup endpoint. No auth, never exposes other buyers' data.
 */
export default function GuestOrderLookup() {
  const [sp] = useSearchParams();
  const orderId = sp.get('order_id');
  const token = sp.get('token');

  const [order, setOrder] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!orderId || !token) {
      setError('This tracking link is missing information. Please use the link in your confirmation email.');
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const r = await axios.get(`${API}/api/orders/lookup`, { params: { order_id: orderId, token } });
        setOrder(r.data);
      } catch (e) {
        const detail = e.response?.data?.detail;
        setError(typeof detail === 'string' ? detail : 'Order not found');
      } finally {
        setLoading(false);
      }
    })();
  }, [orderId, token]);

  const meta = order ? (STATUS_META[order.shipping_status] || STATUS_META[order.status] || { label: order.status, Icon: Package, color: 'text-white' }) : null;

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-2xl mx-auto px-6 md:px-12 py-10">
        <Link to="/" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-6 text-sm">
          <ArrowLeft className="w-4 h-4" /> Back to Unveiled Threads
        </Link>

        <h1
          className="text-2xl md:text-3xl font-black tracking-tighter uppercase text-white mb-6"
          style={{ fontFamily: 'Clash Display, sans-serif' }}
          data-testid="track-title"
        >
          Track your order
        </h1>

        {loading && (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 text-[#39FF14] animate-spin" />
          </div>
        )}

        {!loading && error && (
          <div className="border border-red-500/40 bg-red-500/5 p-6" data-testid="track-error">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-white font-medium mb-1">We couldn't find that order</p>
                <p className="text-xs text-[#9CA3AF]">{error}</p>
              </div>
            </div>
          </div>
        )}

        {!loading && order && (
          <div className="space-y-6" data-testid="track-order-card">
            {/* Status pill */}
            <div className="border border-white/10 bg-[#0A0A0A] p-6">
              <div className="flex items-center gap-3 mb-4">
                {meta && <meta.Icon className={`w-6 h-6 ${meta.color}`} />}
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF]">Status</p>
                  <p className={`text-lg font-bold ${meta?.color || 'text-white'}`} data-testid="track-status">
                    {meta?.label || order.status}
                  </p>
                </div>
              </div>
              {order.tracking_number && (
                <div className="border-t border-white/10 pt-3 mt-3">
                  <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF]">Courier &amp; tracking</p>
                  <p className="text-white text-sm font-mono mt-1" data-testid="track-courier-number">
                    {order.courier || 'Courier'} — {order.tracking_number}
                  </p>
                </div>
              )}
              {order.is_preorder && order.preorder_ship_date && (
                <div className="border-t border-white/10 pt-3 mt-3">
                  <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF]">Ships by</p>
                  <p className="text-white text-sm mt-1">{order.preorder_ship_date}</p>
                </div>
              )}
            </div>

            {/* Order summary */}
            <div className="border border-white/10 bg-[#0A0A0A] p-6">
              <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF] mb-3">Order</p>
              <p className="text-white font-bold">{order.product_name}</p>
              <p className="text-xs text-[#9CA3AF] mb-4">{order.brand_name} · Size {order.size}</p>
              <div className="border-t border-white/10 pt-3 flex justify-between text-sm">
                <span className="text-[#9CA3AF]">Total charged</span>
                <span className="text-white font-bold">£{Number(order.total_charged || 0).toFixed(2)}</span>
              </div>
            </div>

            {order.is_guest && (
              <div className="border border-[#39FF14]/30 bg-[#39FF14]/5 p-5">
                <p className="text-sm text-white font-medium mb-1">Want faster tracking next time?</p>
                <p className="text-xs text-[#9CA3AF] mb-3">
                  Create an account with the email you used at checkout and this order will appear automatically in your Orders page.
                </p>
                <Link to="/register" className="text-xs text-[#39FF14] hover:underline font-bold">
                  Set a password →
                </Link>
              </div>
            )}

            {/* Shipping updates feed */}
            {order.shipping_updates?.length > 0 && (
              <div className="border border-white/10 bg-[#0A0A0A] p-6">
                <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF] mb-3">Updates</p>
                <ul className="space-y-2">
                  {order.shipping_updates.map((u, i) => (
                    <li key={i} className="text-xs text-[#9CA3AF] border-l-2 border-[#39FF14]/40 pl-3">
                      <span className="text-white">{u.status || u.message}</span>
                      {u.at && <span className="block text-[10px] text-[#6B7280]">{new Date(u.at).toLocaleString('en-GB')}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
