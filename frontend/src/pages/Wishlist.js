import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import ProductCard from '../components/ProductCard';
import { Heart, ArrowLeft } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function Wishlist() {
  const { user, loading: authLoading } = useAuth();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchWishlist();
  }, [user, authLoading]);

  const fetchWishlist = async () => {
    try {
      const response = await axios.get(`${API}/api/wishlist`, { withCredentials: true });
      setProducts(response.data);
    } catch (error) {
      console.error('Error fetching wishlist:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleWishlistToggle = (productId, nowWishlisted) => {
    if (!nowWishlisted) {
      setProducts(products.filter(p => p.id !== productId));
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex items-center justify-center h-[60vh]">
          <div className="animate-spin w-8 h-8 border-2 border-[#39FF14] border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="text-center py-24">
          <Heart className="w-12 h-12 text-[#9CA3AF] mx-auto mb-4" />
          <p className="text-[#9CA3AF] mb-4">Please login to view your wishlist</p>
          <Link to="/login"><Button className="btn-primary">Login</Button></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      <div className="max-w-7xl mx-auto px-6 md:px-12 py-8">
        <Link to="/products" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to products
        </Link>

        <div className="flex items-center gap-3 mb-8">
          <Heart className="w-6 h-6 text-[#39FF14]" />
          <h1
            className="text-2xl md:text-3xl font-black tracking-tighter uppercase text-white"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="wishlist-title"
          >
            My Wishlist
          </h1>
          <span className="text-sm text-[#9CA3AF]">({products.length} items)</span>
        </div>

        {products.length === 0 ? (
          <div className="border border-white/10 bg-[#0A0A0A] p-16 text-center">
            <Heart className="w-16 h-16 text-[#9CA3AF] mx-auto mb-4" />
            <p className="text-[#9CA3AF] mb-6">Your wishlist is empty</p>
            <Link to="/products">
              <Button className="btn-primary">Explore Products</Button>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6" data-testid="wishlist-grid">
            {products.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                isWishlisted={true}
                onWishlistToggle={handleWishlistToggle}
                showWishlist={true}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
