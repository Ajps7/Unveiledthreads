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
import { ArrowLeft, Plus, Loader2 } from 'lucide-react';

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

    if (!form.name.trim()) { setError('Product name is required'); return; }
    if (!form.description.trim()) { setError('Description is required'); return; }
    if (!form.price || parseFloat(form.price) <= 0) { setError('Valid price is required'); return; }
    if (!form.category) { setError('Category is required'); return; }
    if (form.sizes.length === 0) { setError('Select at least one size'); return; }
    if (form.images.length === 0) { setError('Upload at least one photo'); return; }
    if (!form.stock || parseInt(form.stock) < 0) { setError('Stock quantity is required'); return; }

    setSubmitting(true);
    try {
      await axios.post(
        `${API}/api/products`,
        {
          name: form.name.trim(),
          description: form.description.trim(),
          price: parseFloat(form.price),
          shipping_cost: parseFloat(form.shipping_cost) || 0,
          category: form.category,
          sizes: form.sizes,
          images: form.images,
          stock: parseInt(form.stock),
          colour: form.colour || null,
          material: form.material || null,
          gender: form.gender,
          condition: form.condition,
          fit: form.fit || null,
        },
        { withCredentials: true }
      );

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
          <ProductPhotos
            images={form.images}
            onUpload={handleImageUpload}
            onRemove={removeImage}
          />

          <ProductDetailsFields form={form} setForm={setForm} />

          <ProductSizes sizes={form.sizes} onToggle={toggleSize} />

          <ProductPricing form={form} setForm={setForm} />

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
