import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import { ProductPhotos } from '../components/product-form/ProductPhotos';
import { ProductDetailsFields } from '../components/product-form/ProductDetailsFields';
import { ProductSizes } from '../components/product-form/ProductSizes';
import { ProductPricing } from '../components/product-form/ProductPricing';
import { SetBuilder } from '../components/product-form/SetBuilder';
import { ArrowLeft, Plus, Loader2, Shirt, Layers } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AddProduct() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    name: '',
    description: '',
    price: '',
    shipping_cost: '3.99',
    category: '',
    stock: '',
    images: [],
    sizes: [],
    colour: '',
    material: '',
    gender: 'unisex',
    condition: 'new',
    fit: '',
    // Pre-order
    is_preorder: false,
    preorder_ship_date: '',
    preorder_limit: '',
    // ---- Full-set / tracksuit shape (default = single) ----
    listing_type: 'single',
    set_components: [
      { label: 'Top',    role: 'top' },
      { label: 'Bottom', role: 'bottom' },
    ],
    sizing_mode: 'split',       // sensible default for tracksuits
    top_sizes: [],
    bottom_sizes: [],
    sold_separately: false,
    component_prices: [],
    // Structured description (all optional)
    story: '',
    details_raw: '',   // newline-separated bullets in the textarea
    materials: '',
    fit_notes: '',
    care: '',
  });

  useEffect(() => {
    if (authLoading) return;
    if (!user) { navigate('/login'); return; }
    if (user.role !== 'brand' && user.role !== 'admin') { navigate('/apply'); return; }
  }, [user, authLoading, navigate]);

  const toggleSize = (size) => {
    setForm((prev) => ({
      ...prev,
      sizes: prev.sizes.includes(size)
        ? prev.sizes.filter((s) => s !== size)
        : [...prev.sizes, size],
    }));
  };

  const handleImageUpload = (urls) => {
    setForm((prev) => ({ ...prev, images: [...prev.images, ...urls] }));
  };

  const removeImage = (index) => {
    setForm((prev) => ({ ...prev, images: prev.images.filter((_, i) => i !== index) }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const isSet = form.listing_type === 'set';

    if (!form.name.trim()) { setError('Product name is required'); return; }
    if (!form.description.trim()) { setError('Description is required'); return; }
    if (!form.price || parseFloat(form.price) <= 0) { setError('Valid price is required'); return; }
    if (!form.category) { setError('Category is required'); return; }
    if (form.images.length === 0) { setError('Upload at least one photo'); return; }

    // Branch: single vs set validation
    if (!isSet) {
      if (form.sizes.length === 0) { setError('Select at least one size'); return; }
    } else {
      if (!form.set_components || form.set_components.length < 2) {
        setError('A set needs at least 2 components (a Top and a Bottom)'); return;
      }
      if (form.set_components.some((c) => !c.label || !c.label.trim())) {
        setError('Give every piece in the set a label (e.g. "Hoodie", "Trousers")'); return;
      }
      if (form.sizing_mode === 'unified') {
        if (!form.sizes || form.sizes.length === 0) {
          setError('Pick at least one set size'); return;
        }
      } else {
        if (!form.top_sizes || form.top_sizes.length === 0) {
          setError('Pick at least one top size'); return;
        }
        if (!form.bottom_sizes || form.bottom_sizes.length === 0) {
          setError('Pick at least one bottom size'); return;
        }
      }
    }

    // Pre-order allows stock=0 so we only enforce presence, not > 0.
    if (form.stock === '' || parseInt(form.stock) < 0) { setError('Stock quantity is required (0 is allowed for pre-orders)'); return; }
    if (form.is_preorder) {
      if (!form.preorder_ship_date) { setError('Pick an expected ship date for the pre-order'); return; }
      const shipDate = new Date(form.preorder_ship_date);
      if (isNaN(shipDate.getTime()) || shipDate <= new Date()) {
        setError('Pre-order ship date must be in the future'); return;
      }
    }

    setSubmitting(true);
    try {
      // Auto-apply the Tracksuits & Sets category for set listings so they're
      // discoverable on the shop. Brand can still override if they want.
      const category = isSet && form.category === '' ? 'Tracksuits & Sets' : form.category;

      const payload = {
        name: form.name.trim(),
        description: form.description.trim(),
        price: parseFloat(form.price),
        shipping_cost: parseFloat(form.shipping_cost) || 0,
        category,
        images: form.images,
        stock: parseInt(form.stock),
        colour: form.colour || null,
        material: form.material || null,
        gender: form.gender,
        condition: form.condition,
        fit: form.fit || null,
        is_preorder: form.is_preorder,
        preorder_ship_date: form.is_preorder && form.preorder_ship_date ? form.preorder_ship_date : null,
        preorder_limit: form.is_preorder && form.preorder_limit ? parseInt(form.preorder_limit) : null,
        listing_type: form.listing_type,
      };

      if (!isSet) {
        payload.sizes = form.sizes;
      } else {
        payload.set_components = form.set_components.map((c) => ({ label: c.label.trim(), role: c.role }));
        payload.sizing_mode = form.sizing_mode;
        if (form.sizing_mode === 'unified') {
          payload.sizes = form.sizes;
        } else {
          payload.top_sizes = form.top_sizes;
          payload.bottom_sizes = form.bottom_sizes;
          // Backend requires `sizes` to be a list but it can be empty for split sets.
          payload.sizes = [];
        }
        // Component prices — only persisted when sold_separately is ON AND
        // every component has a positive price, so partial data can never
        // mislead the PDP savings badge.
        payload.sold_separately = !!form.sold_separately;
        if (form.sold_separately) {
          const cps = (form.component_prices || []).slice(0, form.set_components.length);
          const complete = cps.length === form.set_components.length
            && cps.every((cp) => cp && typeof cp.price === 'number' && cp.price > 0);
          payload.component_prices = complete
            ? cps.map((cp, i) => ({ label: form.set_components[i].label.trim(), price: cp.price }))
            : null;
        } else {
          payload.component_prices = null;
        }
      }

      await axios.post(`${API}/api/products`, payload, { withCredentials: true });

      navigate('/brand/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create product');
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading) {
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
      <div className="max-w-4xl mx-auto px-6 md:px-12 py-8">
        <Link to="/brand/dashboard" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to dashboard
        </Link>

        <h1
          className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-2 text-white"
          style={{ fontFamily: 'Clash Display, sans-serif' }}
          data-testid="add-product-title"
        >
          LIST A PRODUCT
        </h1>
        <p className="text-[#9CA3AF] mb-10">
          Add clear, well-lit photos and detailed descriptions to attract buyers. Quality listings get more views.
        </p>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 mb-6" data-testid="product-form-error">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Listing type toggle — defaults to Single so nothing changes for existing sellers */}
          <div className="border border-white/10 bg-[#0A0A0A] p-6 mb-6" data-testid="listing-type-section">
            <h2 className="text-lg font-bold text-white uppercase mb-1" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Listing type
            </h2>
            <p className="text-xs text-[#9CA3AF] mb-4">
              Pick &ldquo;Full set&rdquo; for tracksuits, co-ords, or any bundle that sells as one.
            </p>
            <div className="grid grid-cols-2 gap-3" data-testid="listing-type-toggle">
              <button
                type="button"
                onClick={() => setForm((prev) => ({ ...prev, listing_type: 'single' }))}
                className={`px-4 py-4 border text-left transition-all flex items-start gap-3 ${
                  form.listing_type === 'single'
                    ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                    : 'border-white/20 text-[#9CA3AF] hover:border-white/40 hover:text-white'
                }`}
                data-testid="listing-type-single"
              >
                <Shirt className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <span>
                  <span className="block uppercase tracking-wider text-sm font-bold">Single item</span>
                  <span className="block text-[11px] font-normal normal-case mt-1 opacity-80">
                    One garment: hoodie, tee, trousers…
                  </span>
                </span>
              </button>
              <button
                type="button"
                onClick={() => setForm((prev) => ({ ...prev, listing_type: 'set' }))}
                className={`px-4 py-4 border text-left transition-all flex items-start gap-3 ${
                  form.listing_type === 'set'
                    ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                    : 'border-white/20 text-[#9CA3AF] hover:border-white/40 hover:text-white'
                }`}
                data-testid="listing-type-set"
              >
                <Layers className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <span>
                  <span className="block uppercase tracking-wider text-sm font-bold">Full set / Tracksuit</span>
                  <span className="block text-[11px] font-normal normal-case mt-1 opacity-80">
                    Multi-piece bundle with its own sizing
                  </span>
                </span>
              </button>
            </div>
          </div>

          <ProductPhotos
            images={form.images}
            onUpload={handleImageUpload}
            onRemove={removeImage}
          />

          <ProductDetailsFields form={form} setForm={setForm} />

          {form.listing_type === 'set' ? (
            <SetBuilder form={form} setForm={setForm} />
          ) : (
            <ProductSizes sizes={form.sizes} onToggle={toggleSize} />
          )}

          <ProductPricing form={form} setForm={setForm} />

          {/* Listing highlights — optional structured description. */}
          <div className="border border-white/10 bg-[#0A0A0A] p-6 mb-6" data-testid="highlights-section">
            <h2 className="text-lg font-bold text-white uppercase mb-1" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Listing highlights <span className="text-[#9CA3AF] text-xs font-normal normal-case ml-2">(optional — makes your listing look premium)</span>
            </h2>
            <p className="text-xs text-[#9CA3AF] mb-4">
              Skip anything you don&apos;t want to fill in. Empty fields are hidden on your listing.
            </p>
            <div className="grid gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1">Short story <span className="text-[#9CA3AF] normal-case">(max 300 chars)</span></label>
                <textarea maxLength={300} value={form.story} onChange={(e) => setForm({ ...form, story: e.target.value })}
                  placeholder="e.g. Cut & sewn in a small East London studio, our love letter to late-90s British streetwear."
                  className="input-brutalist w-full min-h-[70px] resize-none" data-testid="story-input" />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1">Key details <span className="text-[#9CA3AF] normal-case">(one bullet per line, up to 8)</span></label>
                <textarea value={form.details_raw} onChange={(e) => setForm({ ...form, details_raw: e.target.value })}
                  placeholder="380 gsm heavyweight cotton&#10;Screen-printed with water-based inks&#10;Boxy fit — sits below the belt"
                  className="input-brutalist w-full min-h-[100px] resize-none" data-testid="details-input" />
              </div>
              <div className="grid md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1">Materials</label>
                  <input type="text" maxLength={120} value={form.materials} onChange={(e) => setForm({ ...form, materials: e.target.value })}
                    placeholder="e.g. 100% organic cotton" className="input-brutalist w-full" data-testid="materials-input" />
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1">Fit notes</label>
                  <input type="text" maxLength={200} value={form.fit_notes} onChange={(e) => setForm({ ...form, fit_notes: e.target.value })}
                    placeholder='e.g. Runs true to size; model wears M'
                    className="input-brutalist w-full" data-testid="fit-notes-input" />
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1">Care</label>
                  <input type="text" maxLength={200} value={form.care} onChange={(e) => setForm({ ...form, care: e.target.value })}
                    placeholder="e.g. Machine wash cold, tumble dry low"
                    className="input-brutalist w-full" data-testid="care-input" />
                </div>
              </div>
            </div>
          </div>

          {/* Pre-order controls — MVP pre-order feature */}
          <div className="border border-white/10 bg-[#0A0A0A] p-6 mb-6" data-testid="preorder-section">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_preorder}
                onChange={(e) => setForm({ ...form, is_preorder: e.target.checked })}
                className="w-5 h-5 accent-[#39FF14]"
                data-testid="is-preorder-checkbox"
              />
              <div>
                <h2 className="text-lg font-bold text-white uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
                  Sell as pre-order
                </h2>
                <p className="text-xs text-[#9CA3AF] mt-1">
                  Charge buyers now, ship when your stock lands. You&apos;ll receive payouts on Unveiled Threads&apos; standard 7-day rolling delay for buyer protection.
                </p>
              </div>
            </label>

            {form.is_preorder && (
              <div className="grid md:grid-cols-2 gap-5 mt-5">
                <div>
                  <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
                    Expected ship date *
                  </label>
                  <input
                    type="date"
                    value={form.preorder_ship_date}
                    onChange={(e) => setForm({ ...form, preorder_ship_date: e.target.value })}
                    className="input-brutalist w-full"
                    min={new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 10)}
                    data-testid="preorder-ship-date-input"
                  />
                  <p className="text-xs text-[#9CA3AF] mt-1">
                    Buyers see this in your listing. Ship on time or they can refund.
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
                    Pre-order cap (optional)
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={form.preorder_limit}
                    onChange={(e) => setForm({ ...form, preorder_limit: e.target.value })}
                    className="input-brutalist w-full"
                    placeholder="e.g. 50 — leave blank for uncapped"
                    data-testid="preorder-limit-input"
                  />
                  <p className="text-xs text-[#9CA3AF] mt-1">
                    Cap the total pre-orders you&apos;ll accept for this run.
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-4">
            <Button
              type="submit"
              className="btn-primary flex-1 py-4 text-lg"
              disabled={submitting}
              data-testid="submit-product-button"
            >
              {submitting ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Creating Listing...</>
              ) : (
                <><Plus className="w-5 h-5 mr-2" /> LIST PRODUCT</>
              )}
            </Button>
            <Link to="/brand/dashboard">
              <Button type="button" className="btn-secondary py-4">Cancel</Button>
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
