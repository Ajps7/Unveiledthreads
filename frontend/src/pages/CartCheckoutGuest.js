import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Loader2, ArrowLeft, Lock, Shield, LogIn } from 'lucide-react';
import { toast } from 'sonner';
import Header from '../components/Header';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Guest multi-item cart checkout. Mirrors the single-item GuestCheckout
 * page but reads the basket from CartContext (localStorage) and posts
 * to /api/orders/checkout/cart/guest.
 */
export default function CartCheckoutGuest() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { cart, isEmpty } = useCart();
  const [preview, setPreview] = useState(null);
  const [previewError, setPreviewError] = useState('');
  const [previewLoading, setPreviewLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    buyer_email: '',
    name: '',
    line1: '',
    line2: '',
    city: '',
    postcode: '',
    country: 'GB',
    marketing_opt_in: false,
  });

  useEffect(() => {
    // Signed-in users shouldn't be here — bounce them to authed /cart.
    if (user) {
      navigate('/cart');
      return;
    }
    if (isEmpty) {
      navigate('/cart');
      return;
    }
    (async () => {
      try {
        const items = cart.items.map(({ product_id, size, top_size, bottom_size, quantity }) => ({
          product_id, size, top_size, bottom_size, quantity,
        }));
        const res = await axios.post(
          `${API}/api/orders/cart/preview`,
          { items, origin_url: window.location.origin },
        );
        setPreview(res.data);
      } catch (err) {
        setPreviewError(err.response?.data?.detail || 'Could not price your cart.');
      } finally {
        setPreviewLoading(false);
      }
    })();
  }, [user, isEmpty, cart, navigate]);

  const setField = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!preview) {
      toast.error('Please wait for the summary to load.');
      return;
    }
    setSubmitting(true);
    try {
      const items = cart.items.map(({ product_id, size, top_size, bottom_size, quantity }) => ({
        product_id, size, top_size, bottom_size, quantity,
      }));
      const { data } = await axios.post(`${API}/api/orders/checkout/cart/guest`, {
        items,
        origin_url: window.location.origin,
        buyer_email: form.buyer_email.trim(),
        shipping_address: {
          name: form.name.trim(),
          line1: form.line1.trim(),
          line2: form.line2.trim() || null,
          city: form.city.trim(),
          postcode: form.postcode.trim(),
          country: form.country.trim().toUpperCase(),
        },
        marketing_opt_in: form.marketing_opt_in,
      });
      try { sessionStorage.setItem('guest_lookup_token', data.lookup_token); } catch { /* ignore */ }
      window.location.href = data.url;
    } catch (err) {
      const d = err.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'Could not create checkout');
    } finally {
      setSubmitting(false);
    }
  };

  if (previewLoading) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="w-6 h-6 text-[#39FF14] animate-spin" />
        </div>
      </div>
    );
  }

  if (previewError) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="max-w-xl mx-auto px-6 py-16 text-center">
          <p className="text-red-400 mb-4" data-testid="cart-guest-preview-error">{previewError}</p>
          <Link to="/cart"><Button className="btn-secondary">Back to cart</Button></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-3xl mx-auto px-6 md:px-12 py-10" data-testid="cart-guest-page">
        <Link to="/cart" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-6 transition-colors text-sm" data-testid="back-to-cart">
          <ArrowLeft className="w-4 h-4" /> Back to cart
        </Link>

        <div className="mb-8">
          <h1 className="text-2xl md:text-3xl font-black tracking-tighter uppercase text-white mb-2" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="guest-checkout-title">
            Check out as a guest
          </h1>
          <p className="text-sm text-[#9CA3AF]">
            No account needed — we'll email you the tracking link.{' '}
            <Link to="/login?next=/cart" className="text-[#39FF14] hover:underline inline-flex items-center gap-1">
              <LogIn className="w-3 h-3" /> Or sign in
            </Link>
          </p>
        </div>

        {preview && (
          <div className="border border-white/10 bg-[#0A0A0A] mb-8" data-testid="cart-guest-summary">
            <div className="p-4 border-b border-white/10">
              <p className="text-xs uppercase tracking-wider text-[#C0C0C0]">Brand</p>
              <p className="text-white font-bold">{preview.brand_name}</p>
            </div>
            <ul className="divide-y divide-white/5">
              {preview.lines.map((ln, i) => (
                <li key={i} className="p-4 flex items-center justify-between gap-4" data-testid={`guest-cart-line-${i}`}>
                  <div className="min-w-0">
                    <p className="text-white text-sm font-medium truncate">{ln.product_name}</p>
                    <p className="text-xs text-[#9CA3AF]">
                      {ln.size && <>Size {ln.size}</>}
                      {' · '}Qty {ln.quantity}
                      {ln.is_preorder && <span className="ml-2 text-[#39FF14]">Pre-order</span>}
                    </p>
                  </div>
                  <p className="text-white text-sm">£{(ln.unit_price * ln.quantity).toFixed(2)}</p>
                </li>
              ))}
            </ul>
            <div className="border-t border-white/10 px-4 py-4 text-sm space-y-2">
              <div className="flex justify-between text-[#9CA3AF]"><span>Subtotal</span><span className="text-white">£{preview.merch_subtotal.toFixed(2)}</span></div>
              <div className="flex justify-between text-[#9CA3AF]"><span>Buyer Protection</span><span className="text-white">£{preview.platform_fee.toFixed(2)}</span></div>
              <div className="flex justify-between text-[#9CA3AF]"><span>Shipping</span><span className="text-white">{preview.shipping_cost > 0 ? `£${preview.shipping_cost.toFixed(2)}` : 'Free'}</span></div>
              <div className="flex justify-between pt-2 border-t border-white/10 font-bold"><span className="text-white">Total</span><span className="text-[#39FF14]" data-testid="guest-cart-total">£{preview.total_charged.toFixed(2)}</span></div>
              {preview.mixed_fulfilment && (
                <p className="text-[11px] text-[#39FF14]">Items ship separately — in-stock first, pre-order on its dispatch date.</p>
              )}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6" data-testid="guest-cart-form">
          <div>
            <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-2">Email *</label>
            <Input type="email" required value={form.buyer_email} onChange={setField('buyer_email')} placeholder="you@example.com" className="input-brutalist" data-testid="guest-email" />
            <p className="text-[10px] text-[#6B7280] mt-1">We'll send your tracking link here.</p>
          </div>
          <div className="border-t border-white/10 pt-6">
            <p className="text-xs uppercase tracking-wider text-[#C0C0C0] mb-3">Ship to</p>
            <div className="space-y-3">
              <Input required value={form.name} onChange={setField('name')} placeholder="Full name" className="input-brutalist" data-testid="ship-name" />
              <Input required value={form.line1} onChange={setField('line1')} placeholder="Address line 1" className="input-brutalist" data-testid="ship-line1" />
              <Input value={form.line2} onChange={setField('line2')} placeholder="Address line 2 (optional)" className="input-brutalist" data-testid="ship-line2" />
              <div className="grid grid-cols-2 gap-3">
                <Input required value={form.city} onChange={setField('city')} placeholder="City" className="input-brutalist" data-testid="ship-city" />
                <Input required value={form.postcode} onChange={setField('postcode')} placeholder="Postcode" className="input-brutalist" data-testid="ship-postcode" />
              </div>
              <Input value={form.country} onChange={setField('country')} placeholder="Country (ISO code, e.g. GB)" maxLength={2} className="input-brutalist uppercase" data-testid="ship-country" />
            </div>
          </div>
          <label className="flex items-start gap-3 cursor-pointer select-none" data-testid="marketing-opt-in-label">
            <input type="checkbox" checked={form.marketing_opt_in} onChange={(e) => setForm((f) => ({ ...f, marketing_opt_in: e.target.checked }))} className="mt-1 w-4 h-4 accent-[#39FF14]" data-testid="marketing-opt-in" />
            <span className="text-xs text-[#9CA3AF] leading-relaxed">Keep me posted on new drops and brands. Unsubscribe any time. We store your email only after you confirm here.</span>
          </label>
          <Button type="submit" disabled={submitting} className="btn-primary w-full" data-testid="guest-cart-continue-to-payment">
            {submitting ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Creating checkout…</> : <><Lock className="w-4 h-4 mr-2" /> Continue to secure payment</>}
          </Button>
          <p className="text-[10px] text-[#6B7280] flex items-center justify-center gap-1.5">
            <Shield className="w-3 h-3" /> Card payment handled by Stripe. Buyer Protection included.
          </p>
        </form>
      </div>
    </div>
  );
}
