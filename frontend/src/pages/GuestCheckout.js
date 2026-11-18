import { useState, useEffect } from 'react';
import { useParams, useSearchParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import Header from '../components/Header';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import { Loader2, ArrowLeft, Lock, Shield, LogIn } from 'lucide-react';
import { calcBuyerFee, BUYER_PROTECTION_TOOLTIP } from '../lib/fees';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Guest checkout — buy without creating an account. Collects email +
 * shipping, posts to /api/orders/checkout/guest, then hands the buyer
 * off to Stripe Checkout. No password, no auth bounce; the buyer gets
 * their tracking link in the confirmation email.
 */
export default function GuestCheckout() {
  const { productId } = useParams();
  const [sp] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const size = sp.get('size') || '';

  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
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
    // If the buyer's already signed in, short-circuit back to the normal
    // authed checkout on the product page — no reason to make them
    // retype what we already have.
    if (user) {
      navigate(`/products/${productId}`);
      return;
    }
    (async () => {
      try {
        const r = await axios.get(`${API}/api/products/${productId}`);
        setProduct(r.data);
      } catch (e) {
        toast.error('Product not found');
        navigate('/');
      } finally {
        setLoading(false);
      }
    })();
  }, [productId, user, navigate]);

  const setField = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!size) {
      toast.error('No size selected — go back and pick one.');
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await axios.post(`${API}/api/orders/checkout/guest`, {
        product_id: productId,
        size,
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
      // Persist the lookup_token in sessionStorage so OrderSuccess can
      // deep-link into the tracking page without the buyer needing to
      // re-enter anything.
      try { sessionStorage.setItem('guest_lookup_token', data.lookup_token); } catch { /* ignore */ }
      window.location.href = data.url;
    } catch (err) {
      const d = err.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'Could not create checkout');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="w-6 h-6 text-[#39FF14] animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-3xl mx-auto px-6 md:px-12 py-10">
        <Link
          to={`/products/${productId}`}
          className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-6 transition-colors text-sm"
          data-testid="back-to-product"
        >
          <ArrowLeft className="w-4 h-4" /> Back to product
        </Link>

        <div className="mb-8">
          <h1
            className="text-2xl md:text-3xl font-black tracking-tighter uppercase text-white mb-2"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="guest-checkout-title"
          >
            Check out as a guest
          </h1>
          <p className="text-sm text-[#9CA3AF]">
            No account needed — we'll email you the tracking link.{' '}
            <Link to={`/login?next=/products/${productId}`} className="text-[#39FF14] hover:underline inline-flex items-center gap-1">
              <LogIn className="w-3 h-3" /> Or sign in
            </Link>
          </p>
        </div>

        {/* Product summary + full price breakdown — matches what Stripe will show,
            so the buyer isn't surprised by the Buyer Protection line at payment. */}
        <div className="border border-white/10 bg-[#0A0A0A] mb-8" data-testid="guest-checkout-summary">
          <div className="p-4 flex items-center gap-4">
            {product?.images?.[0] && (
              <img
                src={product.images[0].startsWith('/api/') ? `${API}${product.images[0]}` : product.images[0]}
                alt={product.name}
                className="w-20 h-20 object-cover border border-white/10"
              />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium truncate">{product?.name}</p>
              <p className="text-xs text-[#9CA3AF]">{product?.brand_name} · Size {size}</p>
            </div>
          </div>
          {product && (() => {
            const price = Number(product.price || 0);
            const shipping = Number(product.shipping_cost || 0);
            const fee = calcBuyerFee(price);
            const total = Math.round((price + fee + shipping) * 100) / 100;
            return (
              <div className="border-t border-white/10 px-4 py-4 text-sm space-y-2">
                <div className="flex justify-between text-[#9CA3AF]">
                  <span>Item</span>
                  <span className="text-white" data-testid="summary-item-price">£{price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-[#9CA3AF]">
                  <span title={BUYER_PROTECTION_TOOLTIP} className="underline decoration-dotted decoration-[#9CA3AF]/40 underline-offset-2 cursor-help">
                    Buyer Protection
                  </span>
                  <span className="text-white" data-testid="summary-buyer-fee">£{fee.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-[#9CA3AF]">
                  <span>Shipping</span>
                  <span className="text-white" data-testid="summary-shipping">{shipping > 0 ? `£${shipping.toFixed(2)}` : 'Free'}</span>
                </div>
                <div className="flex justify-between pt-2 border-t border-white/10 font-bold">
                  <span className="text-white">Total</span>
                  <span className="text-[#39FF14]" data-testid="summary-total">£{total.toFixed(2)}</span>
                </div>
                <p className="text-[10px] text-[#6B7280] pt-1 leading-relaxed">
                  Buyer Protection (5% + £0.49, max £6) covers your money-back guarantee, easy returns, and hand-vetted independent brands.
                </p>
              </div>
            );
          })()}
        </div>

        <form onSubmit={handleSubmit} className="space-y-6" data-testid="guest-checkout-form">
          <div>
            <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-2">Email *</label>
            <Input
              type="email"
              required
              value={form.buyer_email}
              onChange={setField('buyer_email')}
              placeholder="you@example.com"
              className="input-brutalist"
              data-testid="guest-email"
            />
            <p className="text-[10px] text-[#6B7280] mt-1">
              We'll send your tracking link here. No password. No account yet.
            </p>
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

          {/* GDPR opt-in — unticked by default, with explicit consent copy. */}
          <label className="flex items-start gap-3 cursor-pointer select-none" data-testid="marketing-opt-in-label">
            <input
              type="checkbox"
              checked={form.marketing_opt_in}
              onChange={(e) => setForm((f) => ({ ...f, marketing_opt_in: e.target.checked }))}
              className="mt-1 w-4 h-4 accent-[#39FF14]"
              data-testid="marketing-opt-in"
            />
            <span className="text-xs text-[#9CA3AF] leading-relaxed">
              Keep me posted on new drops and brands. Unsubscribe any time via the link in the footer of our emails. We store your email only after you confirm here — never shared, never sold.
            </span>
          </label>

          <Button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full"
            data-testid="guest-continue-to-payment"
          >
            {submitting ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Creating checkout…</>
            ) : (
              <><Lock className="w-4 h-4 mr-2" /> Continue to secure payment</>
            )}
          </Button>

          <p className="text-[10px] text-[#6B7280] flex items-center justify-center gap-1.5">
            <Shield className="w-3 h-3" /> Card payment handled by Stripe. Buyer Protection included on every order.
          </p>
        </form>
      </div>
    </div>
  );
}
