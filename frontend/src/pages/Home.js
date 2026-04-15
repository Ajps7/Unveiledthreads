import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import Marquee from 'react-fast-marquee';
import { Search, ArrowRight, Zap, Crown, TrendingUp, ShoppingBag } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import Header from '../components/Header';
import ProductCard from '../components/ProductCard';
import BrandCard from '../components/BrandCard';

const API = process.env.REACT_APP_BACKEND_URL;

const TRENDING_BRANDS = ['INDEPENDENT', 'UK MADE', 'SMALL BATCH', 'UNDERGROUND', 'HANDCRAFTED', 'LIMITED DROPS', 'ETHICALLY SOURCED'];

export default function Home() {
  const [brandOfWeek, setBrandOfWeek] = useState(null);
  const [boostedBrands, setBoostedBrands] = useState([]);
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [bowRes, boostedRes, catRes, prodRes] = await Promise.all([
        axios.get(`${API}/api/brands/brand-of-week`),
        axios.get(`${API}/api/brands/boosted`),
        axios.get(`${API}/api/categories`),
        axios.get(`${API}/api/products?limit=8`)
      ]);
      setBrandOfWeek(bowRes.data);
      setBoostedBrands(boostedRes.data);
      setCategories(catRes.data);
      setProducts(prodRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      window.location.href = `/products?search=${encodeURIComponent(searchQuery)}`;
    }
  };

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      {/* Hero Section */}
      <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0">
          <img
            src="https://images.pexels.com/photos/5319298/pexels-photo-5319298.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
            alt="Streetwear"
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-black/60" />
        </div>

        <div className="relative z-10 text-center px-6 max-w-5xl mx-auto">
          <p className="text-xs uppercase tracking-[0.3em] text-[#39FF14] mb-6 animate-fade-in-up">
            UK'S MARKETPLACE FOR INDEPENDENT STREETWEAR
          </p>
          <h1 
            className="text-5xl md:text-7xl lg:text-8xl font-black tracking-tighter uppercase mb-6 text-white text-shadow animate-fade-in-up animate-delay-100"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
          >
            UNVEILED<br />THREADS
          </h1>
          <p className="text-lg md:text-xl text-[#C0C0C0] mb-10 max-w-2xl mx-auto animate-fade-in-up animate-delay-200">
            A platform built for new and emerging UK streetwear brands. Get seen. Get worn. Get growing.
          </p>

          {/* Search Bar */}
          <form onSubmit={handleSearch} className="flex max-w-xl mx-auto mb-8 animate-fade-in-up animate-delay-300">
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search brands, products..."
              className="input-brutalist flex-1 border-r-0"
              data-testid="hero-search-input"
            />
            <Button type="submit" className="btn-primary px-8" data-testid="hero-search-button">
              <Search className="w-5 h-5" />
            </Button>
          </form>

          <div className="flex flex-wrap justify-center gap-4 animate-fade-in-up animate-delay-400">
            <Link to="/products">
              <Button className="btn-primary" data-testid="shop-now-button">
                SHOP NOW <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
            <Link to="/apply">
              <Button className="btn-secondary" data-testid="sell-your-brand-button">
                SELL YOUR BRAND
              </Button>
            </Link>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <div className="w-6 h-10 border-2 border-white/30 rounded-full flex justify-center pt-2">
            <div className="w-1.5 h-3 bg-[#39FF14] rounded-full" />
          </div>
        </div>
      </section>

      {/* Marquee */}
      <div className="bg-[#39FF14] py-3 overflow-hidden">
        <Marquee speed={50} gradient={false}>
          {[...TRENDING_BRANDS, ...TRENDING_BRANDS].map((brand, i) => (
            <span key={i} className="text-black font-bold uppercase tracking-wider mx-8 text-sm" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              {brand} •
            </span>
          ))}
        </Marquee>
      </div>

      {/* Brand of the Week */}
      {brandOfWeek && (
        <section className="py-24 px-6 md:px-12 border-b border-white/10">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-center gap-3 mb-8">
              <Crown className="w-6 h-6 text-[#39FF14]" />
              <span className="text-xs uppercase tracking-[0.2em] text-[#39FF14]">Brand of the Week</span>
            </div>

            <div className="grid lg:grid-cols-2 gap-12 items-center">
              <div>
                <h2 
                  className="text-4xl md:text-6xl font-black tracking-tighter uppercase mb-6 text-white"
                  style={{ fontFamily: 'Clash Display, sans-serif' }}
                  data-testid="brand-of-week-name"
                >
                  {brandOfWeek.brand_name}
                </h2>
                <p className="text-[#9CA3AF] text-lg mb-6 leading-relaxed">
                  {brandOfWeek.description}
                </p>
                <div className="flex flex-wrap gap-4 mb-8">
                  <span className="badge-boost">{brandOfWeek.location}</span>
                  <span className="badge-category">{brandOfWeek.category}</span>
                  {brandOfWeek.instagram_handle && (
                    <span className="badge-category">{brandOfWeek.instagram_handle}</span>
                  )}
                </div>
                <Link to={`/brands/${brandOfWeek.id}`}>
                  <Button className="btn-primary" data-testid="view-brand-of-week-button">
                    VIEW COLLECTION <ArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </Link>
              </div>

              <div className="relative">
                <div className="aspect-[4/5] overflow-hidden border border-white/10">
                  <img
                    src={brandOfWeek.banner_url || "https://images.unsplash.com/photo-1615545362149-85299994b09b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwzfHxzdHJlZXR3ZWFyJTIwZmFzaGlvbiUyMG1vZGVsfGVufDB8fHx8MTc3NjExNDAyNnww&ixlib=rb-4.1.0&q=85"}
                    alt={brandOfWeek.brand_name}
                    className="w-full h-full object-cover hover:scale-105 transition-transform duration-500"
                  />
                </div>
                <div className="absolute -bottom-4 -right-4 bg-[#39FF14] text-black font-bold uppercase tracking-wide px-6 py-3 text-sm">
                  Featured
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Boosted Brands */}
      {boostedBrands.length > 0 && (
        <section className="py-24 px-6 md:px-12 border-b border-white/10 bg-[#0A0A0A]">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-center justify-between mb-12">
              <div className="flex items-center gap-3">
                <Zap className="w-6 h-6 text-[#39FF14]" />
                <h2 
                  className="text-2xl md:text-3xl font-bold tracking-tight uppercase text-white"
                  style={{ fontFamily: 'Clash Display, sans-serif' }}
                >
                  Boosted Brands
                </h2>
              </div>
              <Link to="/brands" className="text-[#39FF14] text-sm uppercase tracking-wider hover:underline" data-testid="view-all-brands-link">
                View All →
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" data-testid="boosted-brands-grid">
              {boostedBrands.slice(0, 4).map((brand) => (
                <BrandCard key={brand.id} brand={brand} isBoosted />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Categories */}
      <section className="py-24 px-6 md:px-12 border-b border-white/10">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-12">
            <TrendingUp className="w-6 h-6 text-[#C0C0C0]" />
            <h2 
              className="text-2xl md:text-3xl font-bold tracking-tight uppercase text-white"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
            >
              Shop by Category
            </h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 border border-white/10" data-testid="categories-grid">
            {categories.map((category) => (
              <Link
                key={category.id}
                to={`/products?category=${category.id}`}
                className="group p-8 border border-white/10 hover:bg-white/5 transition-colors text-center"
                data-testid={`category-${category.id}`}
              >
                <ShoppingBag className="w-8 h-8 mx-auto mb-4 text-[#9CA3AF] group-hover:text-[#39FF14] transition-colors" />
                <h3 className="text-white font-bold uppercase tracking-wider text-sm group-hover:text-[#39FF14] transition-colors">
                  {category.name}
                </h3>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Latest Products */}
      <section className="py-24 px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-12">
            <h2 
              className="text-2xl md:text-3xl font-bold tracking-tight uppercase text-white"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
            >
              Latest Drops
            </h2>
            <Link to="/products" className="text-[#39FF14] text-sm uppercase tracking-wider hover:underline" data-testid="view-all-products-link">
              View All →
            </Link>
          </div>

          {loading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="aspect-[3/4] bg-[#0F0F0F] animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6" data-testid="products-grid">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6 md:px-12 bg-[#0F0F0F] border-t border-white/10">
        <div className="max-w-4xl mx-auto text-center">
          <h2 
            className="text-3xl md:text-5xl font-black tracking-tighter uppercase mb-6 text-white"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
          >
            STARTING A STREETWEAR BRAND?
          </h2>
          <p className="text-[#9CA3AF] text-lg mb-10 max-w-2xl mx-auto">
            Unveiled Threads is the launchpad for new UK streetwear brands. 
            We give independent creators the visibility they deserve — no gatekeeping, just pure talent.
          </p>
          <Link to="/apply">
            <Button className="btn-boost text-lg px-10 py-4" data-testid="cta-apply-button">
              APPLY NOW
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 md:px-12 border-t border-white/10">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            <div>
              <h3 className="text-xl font-bold text-white mb-4" style={{ fontFamily: 'Clash Display, sans-serif' }}>
                UNVEILED THREADS
              </h3>
              <p className="text-[#9CA3AF] text-sm">
                The launchpad for independent UK streetwear brands. Discover, shop, and support emerging creators.
              </p>
            </div>
            <div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-[#C0C0C0] mb-4">Shop</h4>
              <ul className="space-y-2 text-sm text-[#9CA3AF]">
                <li><Link to="/products" className="hover:text-white transition-colors">All Products</Link></li>
                <li><Link to="/brands" className="hover:text-white transition-colors">Brands</Link></li>
                <li><Link to="/products?category=hoodies" className="hover:text-white transition-colors">Hoodies</Link></li>
                <li><Link to="/products?category=t-shirts" className="hover:text-white transition-colors">T-Shirts</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-[#C0C0C0] mb-4">Brands</h4>
              <ul className="space-y-2 text-sm text-[#9CA3AF]">
                <li><Link to="/apply" className="hover:text-white transition-colors">Sell on Unveiled Threads</Link></li>
                <li><Link to="/brand/dashboard" className="hover:text-white transition-colors">Brand Dashboard</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-[#C0C0C0] mb-4">Support</h4>
              <ul className="space-y-2 text-sm text-[#9CA3AF]">
                <li><Link to="/login" className="hover:text-white transition-colors">Login</Link></li>
                <li><Link to="/register" className="hover:text-white transition-colors">Register</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-white/10 pt-8 text-center text-sm text-[#9CA3AF]">
            <p>© 2024 Unveiled Threads. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
