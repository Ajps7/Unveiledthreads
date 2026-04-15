import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, MapPin, Globe, Instagram, Zap, Crown } from 'lucide-react';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import ProductCard from '../components/ProductCard';

const API = process.env.REACT_APP_BACKEND_URL;

export default function BrandProfile() {
  const { id } = useParams();
  const [brand, setBrand] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBrand();
  }, [id]);

  const fetchBrand = async () => {
    try {
      const response = await axios.get(`${API}/api/brands/${id}`);
      setBrand(response.data);
    } catch (error) {
      console.error('Error fetching brand:', error);
    } finally {
      setLoading(false);
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

  if (!brand) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex flex-col items-center justify-center h-[60vh]">
          <p className="text-[#9CA3AF] mb-4">Brand not found</p>
          <Link to="/brands">
            <Button className="btn-secondary">Back to Brands</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      {/* Banner */}
      <div className="relative h-64 md:h-80 overflow-hidden">
        {brand.banner_url ? (
          <img
            src={brand.banner_url}
            alt={brand.brand_name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-r from-[#0A0A0A] to-[#1A1A1A]" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-[#050505] to-transparent" />
      </div>

      {/* Brand Info */}
      <div className="max-w-7xl mx-auto px-6 md:px-12 -mt-24 relative z-10">
        <Link to="/brands" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to brands
        </Link>

        <div className="flex flex-col md:flex-row gap-8 items-start">
          {/* Logo */}
          <div className="w-32 h-32 rounded-full overflow-hidden bg-[#0F0F0F] border-4 border-[#050505] flex-shrink-0">
            {brand.logo_url ? (
              <img src={brand.logo_url} alt={brand.brand_name} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-4xl font-bold text-[#39FF14]" style={{ fontFamily: 'Clash Display, sans-serif' }}>
                {brand.brand_name.charAt(0)}
              </div>
            )}
          </div>

          {/* Info */}
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <h1 
                className="text-3xl md:text-4xl font-black tracking-tighter uppercase text-white"
                style={{ fontFamily: 'Clash Display, sans-serif' }}
                data-testid="brand-name"
              >
                {brand.brand_name}
              </h1>
              {brand.is_brand_of_week && (
                <span className="badge-boost flex items-center gap-1">
                  <Crown className="w-3 h-3" />
                  Brand of the Week
                </span>
              )}
              {brand.is_boosted && (
                <span className="badge-boost flex items-center gap-1">
                  <Zap className="w-3 h-3" />
                  Boosted
                </span>
              )}
            </div>

            <p className="text-[#9CA3AF] mb-6 max-w-2xl" data-testid="brand-description">
              {brand.description}
            </p>

            <div className="flex flex-wrap items-center gap-6 text-sm text-[#C0C0C0]">
              <span className="flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                {brand.location}
              </span>
              {brand.instagram_handle && (
                <a 
                  href={`https://instagram.com/${brand.instagram_handle.replace('@', '')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 hover:text-[#39FF14] transition-colors"
                >
                  <Instagram className="w-4 h-4" />
                  {brand.instagram_handle}
                </a>
              )}
              {brand.website && (
                <a 
                  href={brand.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 hover:text-[#39FF14] transition-colors"
                >
                  <Globe className="w-4 h-4" />
                  Website
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Products */}
      <section className="py-16 px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <h2 
              className="text-xl md:text-2xl font-bold uppercase tracking-tight text-white"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
            >
              Products
            </h2>
            <span className="text-sm text-[#9CA3AF]">
              {brand.products ? brand.products.length : 0} items
            </span>
          </div>

          {brand.products && brand.products.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6" data-testid="brand-products">
              {brand.products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          ) : (
            <div className="text-center py-16 border border-white/10">
              <p className="text-[#9CA3AF]">No products yet</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
