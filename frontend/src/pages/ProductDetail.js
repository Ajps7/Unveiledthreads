import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { ArrowLeft, MapPin, Globe, Instagram, ShoppingBag, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import Header from '../components/Header';

const API = process.env.REACT_APP_BACKEND_URL;
const PLATFORM_FEE_PERCENT = 10;

export default function ProductDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [product, setProduct] = useState(null);
  const [selectedSize, setSelectedSize] = useState('');
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);

  useEffect(() => {
    fetchProduct();
  }, [id]);

  const fetchProduct = async () => {
    try {
      const response = await axios.get(`${API}/api/products/${id}`);
      setProduct(response.data);
      if (response.data.sizes && response.data.sizes.length > 0) {
        setSelectedSize(response.data.sizes[0]);
      }
    } catch (error) {
      console.error('Error fetching product:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async () => {
    if (!user) {
      window.location.href = '/login';
      return;
    }
    if (!selectedSize) return;

    setPurchasing(true);
    try {
      const response = await axios.post(
        `${API}/api/orders/checkout`,
        {
          product_id: id,
          size: selectedSize,
          origin_url: window.location.origin
        },
        { withCredentials: true }
      );
      window.location.href = response.data.url;
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to create checkout';
      alert(msg);
    } finally {
      setPurchasing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex items-center justify-center h-[60vh]">
          <div className="animate-spin w-8 h-8 border-2 border-[#39FF14] border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex flex-col items-center justify-center h-[60vh]">
          <p className="text-[#9CA3AF] mb-4">Product not found</p>
          <Link to="/products">
            <Button className="btn-secondary">Back to Products</Button>
          </Link>
        </div>
      </div>
    );
  }

  const platformFee = (product.price * PLATFORM_FEE_PERCENT / 100);
  const totalPrice = product.price + platformFee;

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      <div className="max-w-7xl mx-auto px-6 md:px-12 py-8">
        <Link to="/products" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to products
        </Link>

        <div className="grid lg:grid-cols-2 gap-12">
          {/* Images */}
          <div className="space-y-4">
            <div className="aspect-[3/4] overflow-hidden border border-white/10 bg-[#0F0F0F]">
              {product.images && product.images.length > 0 ? (
                <img
                  src={product.images[0].startsWith('/api/') ? `${API}${product.images[0]}` : product.images[0]}
                  alt={product.name}
                  className="w-full h-full object-cover"
                  data-testid="product-main-image"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-[#9CA3AF]">
                  No Image
                </div>
              )}
            </div>
            {product.images && product.images.length > 1 && (
              <div className="grid grid-cols-4 gap-2">
                {product.images.slice(1).map((img, i) => (
                  <div key={i} className="aspect-square overflow-hidden border border-white/10 bg-[#0F0F0F]">
                    <img src={img.startsWith('/api/') ? `${API}${img}` : img} alt={`${product.name} ${i + 2}`} className="w-full h-full object-cover" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Product Info */}
          <div>
            {product.brand && (
              <Link
                to={`/brands/${product.brand.id}`}
                className="inline-flex items-center gap-2 text-[#39FF14] text-sm uppercase tracking-wider hover:underline mb-4"
                data-testid="product-brand-link"
              >
                {product.brand.brand_name}
              </Link>
            )}

            <h1
              className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-4 text-white"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
              data-testid="product-name"
            >
              {product.name}
            </h1>

            <p className="text-3xl font-bold text-[#C0C0C0] mb-2" data-testid="product-price">
              £{product.price.toFixed(2)}
            </p>
            <p className="text-xs text-[#9CA3AF] mb-6">
              + £{platformFee.toFixed(2)} platform fee (total: £{totalPrice.toFixed(2)})
            </p>

            <p className="text-[#9CA3AF] mb-8 leading-relaxed" data-testid="product-description">
              {product.description}
            </p>

            {/* Size Selection */}
            {product.sizes && product.sizes.length > 0 && (
              <div className="mb-8">
                <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-3">
                  Size
                </label>
                <div className="flex flex-wrap gap-2">
                  {product.sizes.map((size) => (
                    <button
                      key={size}
                      onClick={() => setSelectedSize(size)}
                      className={`px-4 py-2 border transition-all ${
                        selectedSize === size
                          ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                          : 'border-white/20 text-white hover:border-white/40'
                      }`}
                      data-testid={`size-${size}`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Stock */}
            <p className="text-sm text-[#9CA3AF] mb-6">
              {product.stock > 0 ? (
                <span className="text-[#39FF14]">{product.stock} in stock</span>
              ) : (
                <span className="text-red-400">Out of stock</span>
              )}
            </p>

            {/* Buy Button */}
            <div className="flex gap-4 mb-8">
              <Button
                className="btn-primary flex-1"
                disabled={product.stock === 0 || !selectedSize || purchasing}
                onClick={handlePurchase}
                data-testid="buy-now-button"
              >
                {purchasing ? (
                  <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Processing...</>
                ) : (
                  <><ShoppingBag className="w-5 h-5 mr-2" /> BUY NOW — £{totalPrice.toFixed(2)}</>
                )}
              </Button>
            </div>

            <p className="text-xs text-[#9CA3AF] mb-8">
              A {PLATFORM_FEE_PERCENT}% platform fee supports Unveiled Threads and helps independent brands grow.
            </p>

            {/* Brand Info Card */}
            {product.brand && (
              <div className="border border-white/10 p-6 bg-[#0A0A0A]">
                <h3 className="text-sm uppercase tracking-wider text-[#C0C0C0] mb-4">About the Brand</h3>
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-full overflow-hidden bg-[#1A1A1A] border border-white/10 flex-shrink-0">
                    {product.brand.logo_url ? (
                      <img src={product.brand.logo_url.startsWith('/api/') ? `${API}${product.brand.logo_url}` : product.brand.logo_url} alt={product.brand.brand_name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#39FF14] font-bold">
                        {product.brand.brand_name.charAt(0)}
                      </div>
                    )}
                  </div>
                  <div>
                    <h4 className="text-white font-bold mb-1">{product.brand.brand_name}</h4>
                    <p className="text-[#9CA3AF] text-sm line-clamp-2">{product.brand.description}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-[#C0C0C0]">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {product.brand.location}
                      </span>
                      {product.brand.instagram_handle && (
                        <span className="flex items-center gap-1">
                          <Instagram className="w-3 h-3" />
                          {product.brand.instagram_handle}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <Link to={`/brands/${product.brand.id}`}>
                  <Button className="btn-secondary w-full mt-4" data-testid="view-brand-button">
                    View Brand
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
