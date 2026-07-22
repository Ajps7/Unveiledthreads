import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Search, MapPin, Zap, Crown, ArrowRight } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import BrandCard from '../components/BrandCard';
import { FoundingSpotsCounter } from '../components/FoundingSpots';

const API = process.env.REACT_APP_BACKEND_URL;

export default function Brands() {
  const [brands, setBrands] = useState([]);
  const [brandOfWeek, setBrandOfWeek] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [brandsRes, bowRes] = await Promise.all([
        axios.get(`${API}/api/brands`),
        axios.get(`${API}/api/brands/brand-of-week`).catch(() => ({ data: null }))
      ]);
      setBrands(brandsRes.data);
      setBrandOfWeek(bowRes.data);
    } catch (error) {
      console.error('Error fetching brands:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredBrands = brands.filter(brand => 
    brand.brand_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    brand.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    brand.location.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const boostedBrands = filteredBrands.filter(b => b.is_boosted);
  const regularBrands = filteredBrands.filter(b => !b.is_boosted);

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      {/* Hero Banner */}
      <section className="py-16 px-6 md:px-12 border-b border-white/10 bg-[#0A0A0A]">
        <div className="max-w-7xl mx-auto">
          <h1 
            className="text-4xl md:text-5xl font-black tracking-tighter uppercase mb-4 text-white"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="brands-page-title"
          >
            ALL BRANDS
          </h1>
          <p className="text-[#9CA3AF] max-w-2xl mb-8">
            Discover emerging independent UK streetwear brands — all starting small, all making moves
          </p>

          {/* Search */}
          <div className="flex gap-2 max-w-md">
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search brands..."
              className="input-brutalist"
              data-testid="brands-search-input"
            />
            <Button className="btn-secondary px-4">
              <Search className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </section>

      {/* Brand of the Week */}
      {brandOfWeek && (
        <section className="py-16 px-6 md:px-12 border-b border-white/10">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-center gap-3 mb-8">
              <Crown className="w-6 h-6 text-[#39FF14]" />
              <span className="text-xs uppercase tracking-[0.2em] text-[#39FF14]">Brand of the Week</span>
            </div>

            <div className="grid lg:grid-cols-2 gap-12 items-center">
              <div>
                <h2
                  className="text-3xl md:text-5xl font-black tracking-tighter uppercase mb-4 text-white"
                  style={{ fontFamily: 'Clash Display, sans-serif' }}
                  data-testid="brands-bow-name"
                >
                  {brandOfWeek.brand_name}
                </h2>
                <p className="text-[#9CA3AF] text-base mb-6 leading-relaxed">
                  {brandOfWeek.description}
                </p>
                <div className="flex flex-wrap gap-3 mb-6">
                  <span className="badge-boost">{brandOfWeek.location}</span>
                  <span className="badge-category">{brandOfWeek.category}</span>
                </div>
                <Link to={`/brands/${brandOfWeek.id}`}>
                  <Button className="btn-primary" data-testid="brands-bow-button">
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
        <section className="py-12 px-6 md:px-12 border-b border-white/10 bg-[#0A0A0A]">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-center gap-3 mb-8">
              <Zap className="w-5 h-5 text-[#39FF14]" />
              <h2 className="text-xl font-bold uppercase tracking-tight text-white" style={{ fontFamily: 'Clash Display, sans-serif' }}>
                Featured Brands
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" data-testid="boosted-brands">
              {boostedBrands.map((brand) => (
                <BrandCard key={brand.id} brand={brand} isBoosted />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* All Brands */}
      <section className="py-12 px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <h2 className="text-xl font-bold uppercase tracking-tight text-white mb-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              All Brands
            </h2>
            <p className="text-sm text-[#9CA3AF]">
              {loading ? 'Loading...' : `${filteredBrands.length} brands`}
            </p>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="card-brand animate-pulse">
                  <div className="w-20 h-20 rounded-full bg-[#1A1A1A] mb-4" />
                  <div className="h-5 w-24 bg-[#1A1A1A] mb-2" />
                  <div className="h-4 w-full bg-[#1A1A1A]" />
                </div>
              ))}
            </div>
          ) : regularBrands.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" data-testid="all-brands">
              {regularBrands.map((brand) => (
                <BrandCard key={brand.id} brand={brand} />
              ))}
            </div>
          ) : boostedBrands.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-[#9CA3AF]">No brands found</p>
            </div>
          ) : null}
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6 md:px-12 border-t border-white/10 bg-[#0A0A0A]">
        <div className="max-w-2xl mx-auto text-center">
          <h2 
            className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-4 text-white"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
          >
            WANT TO JOIN?
          </h2>
          <p className="text-[#9CA3AF] mb-4">
            Apply to become a seller and launch your brand to a new audience
          </p>
          <FoundingSpotsCounter />
          <Link to="/apply">
            <Button className="btn-boost" data-testid="apply-cta-button">
              APPLY NOW
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
