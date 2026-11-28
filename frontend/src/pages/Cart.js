import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ShoppingBag, Loader2, Trash2, Minus, Plus, Package } from 'lucide-react';
import Header from '../components/Header';
import { Button } from '../components/ui/button';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

export default function Cart() {
  const { cart, isEmpty, removeItem, updateQty, clearCart } = useCart();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [preview, setPreview] = useState(null);
  const [previewError, setPreviewError] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [checkingOut, setCheckingOut] = useState(false);
  const [checkoutError, setCheckoutError] = useState('');
  // Discount code state — applied code lives here AND is sent on every
  // preview call so totals re-price server-authoritatively.
  const [codeInput, setCodeInput] = useState('');
  const [appliedCode, setAppliedCode] = useState('');
  const [codeError, setCodeError] = useState('');
  const [codeLoading, setCodeLoading] = useState(false);

  const fetchPreview = useCallback(async () => {
    if (isEmpty) { setPreview(null); return; }
    setPreviewLoading(true);
    setPreviewError('');
    try {
      const items = cart.items.map(({ product_id, size, top_size, bottom_size, quantity }) => ({
        product_id, size, top_size, bottom_size, quantity,
      }));
      const payload = { items, origin_url: window.location.origin };
      if (appliedCode) payload.code = appliedCode;
      const res = await axios.post(
        `${API}/api/orders/cart/preview`,
        payload,
      );
      setPreview(res.data);
      // The server re-evaluates the code every preview. If it has become
      // invalid (window closed, cap hit, items changed to another brand),
      // the response carries `discount_error` and we clear the applied state.
      if (appliedCode && !res.data.discount && res.data.discount_error) {
        setCodeError(res.data.discount_error);
        setAppliedCode('');
      } else if (res.data.discount) {
        setCodeError('');
      }
    } catch (err) {
      setPreview(null);
      setPreviewError(err.response?.data?.detail || 'Could not price your cart.');
    } finally {
      setPreviewLoading(false);
    }
  }, [cart, isEmpty, appliedCode]);

  useEffect(() => { fetchPreview(); }, [fetchPreview]);

  const handleApplyCode = async () => {
    const code = codeInput.trim().toUpperCase();
    if (!code) return;
    setCodeLoading(true);
    setCodeError('');
    try {
      const items = cart.items.map(({ product_id, size, top_size, bottom_size, quantity }) => ({
        product_id, size, top_size, bottom_size, quantity,
      }));
      const payload = { code, items };
      if (!user && cart.items[0]) {
        // For guests the per-customer limit needs an email, but we don't
        // have one yet on the cart page — the limit is re-checked at
        // guest checkout time against the email they type there.
      }
      const res = await axios.post(
        `${API}/api/discounts/validate`,
        payload,
        user ? { withCredentials: true } : undefined,
      );
      if (res.data.ok) {
        setAppliedCode(res.data.code);
        setCodeError('');
      } else {
        setCodeError(res.data.message || 'This code can\'t be applied.');
      }
    } catch (err) {
      setCodeError(err.response?.data?.detail || 'Could not validate code.');
    } finally {
      setCodeLoading(false);
    }
  };

  const handleRemoveCode = () => {
    setAppliedCode('');
    setCodeInput('');
    setCodeError('');
  };

  const handleCheckout = async () => {
    setCheckoutError('');
    setCheckingOut(true);
    const items = cart.items.map(({ product_id, size, top_size, bottom_size, quantity }) => ({
      product_id, size, top_size, bottom_size, quantity,
    }));
    try {
      if (!user) {
        // Guests go to a dedicated multi-item guest checkout page that
        // reads the cart from CartContext and collects email + shipping.
        // Hand the applied code through sessionStorage so the guest page
        // re-validates it with the typed email for the per-customer cap.
        try { sessionStorage.setItem('ut_cart_code', appliedCode || ''); } catch { /* ignore */ }
        navigate('/checkout/guest/cart');
        return;
      }
      const payload = { items, origin_url: window.location.origin };
      if (appliedCode) payload.code = appliedCode;
      const res = await axios.post(
        `${API}/api/orders/checkout/cart`,
        payload,
        { withCredentials: true }
      );
      window.location.href = res.data.url;
    } catch (err) {
      setCheckoutError(err.response?.data?.detail || 'Could not start checkout.');
    } finally {
      setCheckingOut(false);
    }
  };

  // Map preview lines back to cart items so we can render current/server price
  const previewByProductIdKey = {};
  if (preview?.lines) {
    for (const ln of preview.lines) {
      const key = `${ln.product_id}|${ln.size || ''}|${ln.top_size || ''}|${ln.bottom_size || ''}`;
      previewByProductIdKey[key] = ln;
    }
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-5xl mx-auto px-6 md:px-12 py-10" data-testid="cart-page">
        <h1
          className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-6 text-white"
          style={{ fontFamily: 'Clash Display, sans-serif' }}
        >
          Your Cart
        </h1>

        {isEmpty ? (
          <div className="border border-white/10 bg-[#0A0A0A] p-12 text-center" data-testid="cart-empty-state">
            <ShoppingBag className="w-10 h-10 text-[#39FF14] mx-auto mb-4" />
            <p className="text-white font-bold text-lg mb-2">Your cart is empty.</p>
            <p className="text-[#9CA3AF] text-sm mb-6">Browse independent UK brands and add pieces you love.</p>
            <Link to="/products">
              <Button className="btn-primary" data-testid="cart-browse-button">Browse the shop</Button>
            </Link>
          </div>
        ) : (
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Lines */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <p className="text-sm uppercase tracking-wider text-[#C0C0C0]">
                  Brand: <span className="text-[#39FF14] font-bold">{cart.brand_name}</span>
                </p>
                <button
                  className="text-xs text-[#9CA3AF] hover:text-red-400 transition-colors"
                  onClick={() => { if (window.confirm('Clear your cart?')) clearCart(); }}
                  data-testid="cart-clear-button"
                >
                  Clear cart
                </button>
              </div>

              {cart.items.map((it, idx) => {
                const key = `${it.product_id}|${it.size || ''}|${it.top_size || ''}|${it.bottom_size || ''}`;
                const serverLine = previewByProductIdKey[key];
                const unitPrice = serverLine?.unit_price ?? it.unit_price ?? 0;
                return (
                  <div key={`${key}-${idx}`} className="border border-white/10 bg-[#0A0A0A] p-4 flex gap-4" data-testid={`cart-line-${idx}`}>
                    <Link to={`/products/${it.product_id}`} className="shrink-0">
                      {it.image ? (
                        <img src={it.image.startsWith('/api/') ? `${API}${it.image}` : it.image} alt={it.product_name} className="w-20 h-20 object-cover" />
                      ) : (
                        <div className="w-20 h-20 bg-[#1A1A1A] flex items-center justify-center">
                          <ShoppingBag className="w-6 h-6 text-[#27272A]" />
                        </div>
                      )}
                    </Link>
                    <div className="flex-1 min-w-0">
                      <Link to={`/products/${it.product_id}`} className="block">
                        <p className="text-white font-bold truncate hover:text-[#39FF14] transition-colors" data-testid={`cart-line-name-${idx}`}>{it.product_name}</p>
                      </Link>
                      <p className="text-xs text-[#9CA3AF] mt-0.5">
                        {it.size && <>Size {it.size}</>}
                        {it.top_size && <>Top {it.top_size} / Bottom {it.bottom_size}</>}
                        {it.is_preorder && (
                          <span className="ml-2 inline-block px-1.5 py-0.5 bg-[#39FF14]/10 text-[#39FF14] text-[10px] uppercase tracking-wider border border-[#39FF14]/30">
                            Pre-order{it.preorder_ship_date ? ` · ships by ${it.preorder_ship_date}` : ''}
                          </span>
                        )}
                      </p>
                      <div className="flex items-center justify-between mt-3">
                        <div className="flex items-center border border-white/10">
                          <button
                            className="w-8 h-8 flex items-center justify-center text-[#C0C0C0] hover:text-white hover:bg-white/5 disabled:opacity-30"
                            onClick={() => updateQty(idx, (it.quantity || 1) - 1)}
                            disabled={(it.quantity || 1) <= 1}
                            data-testid={`cart-qty-minus-${idx}`}
                            aria-label="Decrease quantity"
                          >
                            <Minus className="w-3 h-3" />
                          </button>
                          <span className="w-10 text-center text-sm text-white" data-testid={`cart-qty-${idx}`}>{it.quantity || 1}</span>
                          <button
                            className="w-8 h-8 flex items-center justify-center text-[#C0C0C0] hover:text-white hover:bg-white/5 disabled:opacity-30"
                            onClick={() => updateQty(idx, (it.quantity || 1) + 1)}
                            disabled={(it.quantity || 1) >= 10}
                            data-testid={`cart-qty-plus-${idx}`}
                            aria-label="Increase quantity"
                          >
                            <Plus className="w-3 h-3" />
                          </button>
                        </div>
                        <div className="flex items-center gap-4">
                          <p className="text-white font-bold" data-testid={`cart-line-price-${idx}`}>
                            £{(unitPrice * (it.quantity || 1)).toFixed(2)}
                          </p>
                          <button
                            className="text-[#9CA3AF] hover:text-red-400 transition-colors"
                            onClick={() => removeItem(idx)}
                            data-testid={`cart-remove-${idx}`}
                            aria-label="Remove item"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {previewError && (
                <div className="border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300" data-testid="cart-preview-error">
                  {previewError}
                </div>
              )}
            </div>

            {/* Summary */}
            <aside className="lg:col-span-1">
              <div className="border border-white/10 bg-[#0A0A0A] p-6 lg:sticky lg:top-24" data-testid="cart-summary">
                <h2 className="text-sm uppercase tracking-wider text-[#C0C0C0] mb-4">Order summary</h2>
                {previewLoading && !preview ? (
                  <div className="text-center py-6">
                    <Loader2 className="w-5 h-5 animate-spin text-[#39FF14] mx-auto" />
                  </div>
                ) : preview ? (
                  <>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between text-[#9CA3AF]">
                        <span>Subtotal</span>
                        <span className="text-white" data-testid="cart-subtotal">£{preview.merch_subtotal.toFixed(2)}</span>
                      </div>
                      {preview.discount && (
                        <div className="flex justify-between text-[#39FF14]" data-testid="cart-discount-line">
                          <span>
                            {preview.discount.percent_off}% off {preview.discount.brand_name}
                            <span className="block text-[10px] text-[#9CA3AF]">code {preview.discount.code}</span>
                          </span>
                          <span className="font-bold">-£{preview.discount.amount.toFixed(2)}</span>
                        </div>
                      )}
                      <div className="flex justify-between text-[#9CA3AF]">
                        <span>Buyer Protection</span>
                        <span className="text-white" data-testid="cart-fee">£{preview.platform_fee.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between text-[#9CA3AF]">
                        <span>Shipping</span>
                        <span className="text-white" data-testid="cart-shipping">{preview.shipping_cost > 0 ? `£${preview.shipping_cost.toFixed(2)}` : 'Free'}</span>
                      </div>
                      <div className="flex justify-between pt-3 mt-2 border-t border-white/10">
                        <span className="text-white font-bold">Total</span>
                        <span className="text-[#39FF14] font-bold text-lg" data-testid="cart-total">£{preview.total_charged.toFixed(2)}</span>
                      </div>
                    </div>

                    {/* Have a code? — compact input, server-validated, shows
                        applied state with a remove button. No code? Nothing
                        is shown about discounts. */}
                    <div className="mt-4 pt-4 border-t border-white/10" data-testid="cart-code-section">
                      {appliedCode && preview.discount ? (
                        <div className="flex items-center justify-between gap-2 border border-[#39FF14]/40 bg-[#39FF14]/5 px-3 py-2 text-sm">
                          <span className="text-[#39FF14] font-bold" data-testid="cart-code-applied">
                            {appliedCode} applied
                          </span>
                          <button
                            onClick={handleRemoveCode}
                            className="text-xs text-[#9CA3AF] hover:text-red-400 transition-colors"
                            data-testid="cart-code-remove"
                          >
                            Remove
                          </button>
                        </div>
                      ) : (
                        <>
                          <label className="block text-[10px] uppercase tracking-wider text-[#C0C0C0] mb-1.5">Have a code?</label>
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={codeInput}
                              onChange={(e) => setCodeInput(e.target.value.toUpperCase())}
                              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleApplyCode(); } }}
                              placeholder="FLAIRE25"
                              maxLength={32}
                              className="flex-1 bg-transparent border border-white/20 px-3 py-2 text-sm text-white uppercase tracking-wider focus:border-[#39FF14] focus:outline-none"
                              data-testid="cart-code-input"
                            />
                            <button
                              onClick={handleApplyCode}
                              disabled={!codeInput.trim() || codeLoading}
                              className="px-4 py-2 border border-[#39FF14] text-[#39FF14] text-sm uppercase tracking-wider hover:bg-[#39FF14] hover:text-black transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                              data-testid="cart-code-apply"
                            >
                              {codeLoading ? '…' : 'Apply'}
                            </button>
                          </div>
                          {codeError && (
                            <p className="mt-1.5 text-xs text-red-400" data-testid="cart-code-error">{codeError}</p>
                          )}
                        </>
                      )}
                    </div>

                    {preview.mixed_fulfilment && (
                      <div className="mt-4 border border-[#39FF14]/30 bg-[#39FF14]/5 p-3 text-xs text-[#9CA3AF]" data-testid="cart-mixed-fulfilment-notice">
                        <Package className="w-4 h-4 text-[#39FF14] inline mr-1.5" />
                        <strong className="text-white">Items ship separately.</strong> In-stock pieces ship first; pre-order pieces ship on their dispatch date.
                      </div>
                    )}

                    <Button
                      className="btn-primary w-full mt-5 min-h-[48px]"
                      disabled={checkingOut || !!previewError}
                      onClick={handleCheckout}
                      data-testid="cart-checkout-button"
                    >
                      {checkingOut ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Processing...</> : <>Checkout — £{preview.total_charged.toFixed(2)}</>}
                    </Button>
                    {checkoutError && (
                      <p className="mt-3 text-xs text-red-400" data-testid="cart-checkout-error">{checkoutError}</p>
                    )}
                    <p className="mt-3 text-[10px] text-[#6B7280] leading-relaxed">
                      Buyer Protection (5% + £0.49, max £6) once per order — money-back guarantee, easy returns, hand-vetted independent brands.
                    </p>
                  </>
                ) : null}
              </div>
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}
