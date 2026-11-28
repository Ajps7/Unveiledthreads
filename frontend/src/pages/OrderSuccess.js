import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import { CheckCircle, Loader2, XCircle, Package } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function OrderSuccess() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [status, setStatus] = useState('checking');
  const [order, setOrder] = useState(null);

  const isGuest = searchParams.get('guest') === '1';
  const guestToken = searchParams.get('token') || '';

  const pollPaymentStatus = useCallback(async (sessionId, attemptNum = 0) => {
    if (attemptNum >= 5) {
      setStatus('timeout');
      return;
    }

    try {
      // Guest flow tacks on `?token=<lookup_token>` for authorisation —
      // the backend accepts either a session cookie or a matching token.
      const url = isGuest && guestToken
        ? `${API}/api/orders/status/${sessionId}?token=${encodeURIComponent(guestToken)}`
        : `${API}/api/orders/status/${sessionId}`;
      const response = await axios.get(url, { withCredentials: !isGuest });

      if (response.data.payment_status === 'paid') {
        if (response.data.order) setOrder(response.data.order);
        setStatus('success');
        return;
      } else if (response.data.status === 'expired') {
        setStatus('expired');
        return;
      }

      setTimeout(() => pollPaymentStatus(sessionId, attemptNum + 1), 2000);
    } catch (error) {
      console.error('Error checking payment status:', error);
      setStatus('error');
    }
  }, [isGuest, guestToken]);

  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    if (!sessionId) {
      setStatus('error');
      return;
    }
    pollPaymentStatus(sessionId);
  }, [searchParams, pollPaymentStatus]);

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      <div className="max-w-2xl mx-auto px-6 py-24 text-center">
        {status === 'checking' && (
          <>
            <Loader2 className="w-16 h-16 text-[#39FF14] animate-spin mx-auto mb-6" />
            <h1 className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-4 text-white" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              PROCESSING ORDER
            </h1>
            <p className="text-[#9CA3AF]">Confirming your payment...</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="w-16 h-16 text-[#39FF14] mx-auto mb-6" />
            <h1 className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-4 text-white" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="order-success-title">
              ORDER CONFIRMED!
            </h1>
            <p className="text-[#9CA3AF] mb-8">
              Thank you for supporting an independent UK brand! The brand will be notified of your order.
            </p>
            {order && (
              <div className="max-w-sm mx-auto mb-8 border border-white/10 bg-[#0A0A0A] p-5 text-left text-sm" data-testid="order-receipt">
                <p className="text-xs uppercase tracking-wider text-[#9CA3AF] mb-3">Receipt</p>
                <p className="text-white font-bold mb-1">{order.product_name}</p>
                <p className="text-xs text-[#9CA3AF] mb-4">{order.brand_name} · Size {order.size}</p>
                <div className="space-y-1.5 text-[#9CA3AF]">
                  <div className="flex justify-between"><span>Item</span><span className="text-white">£{(order.price ?? 0).toFixed(2)}</span></div>
                  {order.discount_code && order.discount_amount > 0 && (
                    <div className="flex justify-between" data-testid="receipt-discount">
                      <span className="text-[#39FF14]">{order.discount_percent}% off {order.brand_name} <span className="text-[10px] text-[#9CA3AF]">(code {order.discount_code})</span></span>
                      <span className="text-[#39FF14]">-£{order.discount_amount.toFixed(2)}</span>
                    </div>
                  )}
                  <div className="flex justify-between"><span>Buyer Protection</span><span className="text-white" data-testid="receipt-buyer-protection">£{(order.platform_fee ?? 0).toFixed(2)}</span></div>
                  {order.credit_applied > 0 && (
                    <div className="flex justify-between"><span>Referral credit</span><span className="text-[#39FF14]">-£{order.credit_applied.toFixed(2)}</span></div>
                  )}
                  <div className="flex justify-between"><span>Shipping</span><span className="text-white">{order.shipping_cost > 0 ? `£${order.shipping_cost.toFixed(2)}` : 'Free'}</span></div>
                  <div className="flex justify-between border-t border-white/10 pt-2 mt-2 font-bold text-white"><span>Total</span><span data-testid="receipt-total">£{(order.total_charged ?? 0).toFixed(2)}</span></div>
                </div>
              </div>
            )}
            <div className="flex gap-4 justify-center flex-wrap">
              {isGuest && guestToken && order ? (
                <Link to={`/track?order_id=${order.id || ''}&token=${encodeURIComponent(guestToken)}`}>
                  <Button className="btn-primary" data-testid="guest-track-order-button">
                    <Package className="w-4 h-4 mr-2" /> Track your order
                  </Button>
                </Link>
              ) : (
                <>
                  <Link to="/products">
                    <Button className="btn-primary" data-testid="continue-shopping-button">
                      <Package className="w-4 h-4 mr-2" />
                      Continue Shopping
                    </Button>
                  </Link>
                  <Link to="/orders">
                    <Button className="btn-secondary" data-testid="view-orders-button">
                      My Orders
                    </Button>
                  </Link>
                </>
              )}
            </div>

            {/* Guest-only: optional account upgrade. Skippable — we don't
                require it, and the order is already saved + emailed. */}
            {isGuest && !user && (
              <div className="max-w-sm mx-auto mt-10 border border-[#39FF14]/30 bg-[#39FF14]/5 p-5 text-left" data-testid="guest-upgrade-card">
                <p className="text-sm text-white font-medium mb-1">Save tracking for next time?</p>
                <p className="text-xs text-[#9CA3AF] mb-3">
                  Set a password to see all your orders on one page. Totally optional — your order's already saved and we've emailed you the tracking link.
                </p>
                <div className="flex gap-2">
                  <Link to="/register" className="flex-1">
                    <Button className="btn-primary w-full text-xs" data-testid="guest-create-account-button">
                      Create account
                    </Button>
                  </Link>
                  <Link to="/products" className="flex-1">
                    <Button className="btn-secondary w-full text-xs" data-testid="guest-skip-account-button">
                      Skip
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </>
        )}

        {status === 'expired' && (
          <>
            <XCircle className="w-16 h-16 text-red-400 mx-auto mb-6" />
            <h1 className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-4 text-white" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              SESSION EXPIRED
            </h1>
            <p className="text-[#9CA3AF] mb-8">Your payment session expired. Please try again.</p>
            <Button className="btn-primary" onClick={() => navigate('/products')}>Back to Products</Button>
          </>
        )}

        {(status === 'timeout' || status === 'error') && (
          <>
            <Loader2 className="w-16 h-16 text-yellow-400 mx-auto mb-6" />
            <h1 className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-4 text-white" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              {status === 'timeout' ? 'STILL PROCESSING' : 'SOMETHING WENT WRONG'}
            </h1>
            <p className="text-[#9CA3AF] mb-8">
              {status === 'timeout'
                ? 'Payment is still being processed. Check your orders page in a few minutes.'
                : 'There was an error. Please check your orders or contact support.'}
            </p>
            <Button className="btn-primary" onClick={() => navigate('/products')}>Back to Products</Button>
          </>
        )}
      </div>
    </div>
  );
}
