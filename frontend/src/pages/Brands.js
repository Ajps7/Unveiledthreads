import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Search, MapPin, Zap } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import BrandCard from '../components/BrandCard';

const API = process.env.REACT_APP_BACKEND_URL;

export default function Brands() {
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchBrands();
  }, []);

  const fetchBrands = async () => {
    try {
      const response = await axios.get(`${API}/api/brands`);
      setBrands(response.data);
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
          <p className="text-[#9CA3AF] mb-6">
            Apply to become a seller and launch your brand to a new audience
          </p>
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
