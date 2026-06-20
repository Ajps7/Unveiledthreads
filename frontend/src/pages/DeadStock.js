import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import Header from '../components/Header';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Loader2, Tag, ArrowLeft, Truck } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function DeadStock() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState('latest');
  const [minDiscount, setMinDiscount] = useState('all');

  useEffect(() => {
    fetchProducts();
  }, [sort, minDiscount]);

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ sort });
      if (minDiscount !== 'all') params.set('min_discount', minDiscount);
      const res = await axios.get(`${API}/api/dead-stock?${params.toString()}`);
      setProducts(res.data);
    } catch (e) {
      console.error('Failed to load dead stock:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505]" data-testid="dead-stock-page">
      <Header />

      {/* Hero */}
      <section className="border-b border-white/10 bg-gradient-to-b from-[#39FF14]/5 to-transparent">
        <div className="max-w-7xl mx-auto px-6 md:px-12 py-16">
          <Link to="/products" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-6 transition-colors text-sm">
            <ArrowLeft className="w-4 h-4" /> All products
          </Link>
          <div className="flex items-center gap-3 mb-3">
            <Tag className="w-5 h-5 text-[#39FF14]" />
            <p className="text-xs uppercase tracking-[0.3em] text-[#39FF14] font-bold">Archive Sale</p>
          </div>
          <h1
            className="text-4xl md:text-6xl font-black tracking-tighter uppercase text-white mb-3"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="dead-stock-title"
          >
            DEAD STOCK
          </h1>
          <p className="text-[#9CA3AF] max-w-2xl text-base">
            Past-collection pieces straight from the brands. Limited stock, sharper prices —
            once it&apos;s gone, it&apos;s gone.
          </p>
        </div>
      </section>

      <div className="max-w-7xl mx-auto px-6 md:px-12 py-12">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-8 pb-6 border-b border-white/5">
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#9CA3AF] uppercase tracking-wider">Sort</span>
            <Select value={sort} onValueChange={setSort}>
              <SelectTrigger className="w-[180px] bg-transparent border-white/20 rounded-none text-white" data-testid="dead-stock-sort">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                <SelectItem value="latest" className="text-white hover:bg-white/10 rounded-none">Just dropped</SelectItem>
                <SelectItem value="biggest_discount" className="text-white hover:bg-white/10 rounded-none">Biggest discount</SelectItem>
                <SelectItem value="price_low" className="text-white hover:bg-white/10 rounded-none">Price low → high</SelectItem>
                <SelectItem value="price_high" className="text-white hover:bg-white/10 rounded-none">Price high → low</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#9CA3AF] uppercase tracking-wider">Min discount</span>
            <Select value={minDiscount} onValueChange={setMinDiscount}>
              <SelectTrigger className="w-[140px] bg-transparent border-white/20 rounded-none text-white" data-testid="dead-stock-min-discount">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                <SelectItem value="all" className="text-white hover:bg-white/10 rounded-none">Any</SelectItem>
                <SelectItem value="15" className="text-white hover:bg-white/10 rounded-none">15%+</SelectItem>
                <SelectItem value="30" className="text-white hover:bg-white/10 rounded-none">30%+</SelectItem>
                <SelectItem value="50" className="text-white hover:bg-white/10 rounded-none">50%+</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="text-xs text-[#9CA3AF] ml-auto" data-testid="dead-stock-count">
            {products.length} {products.length === 1 ? 'item' : 'items'}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="w-8 h-8 text-[#39FF14] animate-spin" />
          </div>
        ) : products.length === 0 ? (
          <div className="text-center py-24 border border-white/10 bg-[#0A0A0A]">
            <Tag className="w-12 h-12 text-[#39FF14]/40 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-white mb-2">Nothing in the archive yet</h3>
            <p className="text-[#9CA3AF] text-sm max-w-md mx-auto">
              When brands move pieces into Dead Stock, they&apos;ll show up here. Check back soon.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" data-testid="dead-stock-grid">
            {products.map((p) => {
              const imgSrc = p.images?.[0]
                ? (p.images[0].startsWith('/api/') ? `${API}${p.images[0]}` : p.images[0])
                : null;
              const discount = p.discount_percent || 0;
              return (
                <Link
                  key={p.id}
                  to={`/products/${p.id}`}
                  className="group border border-white/10 bg-[#0A0A0A] hover:border-[#39FF14]/40 transition-colors block"
                  data-testid={`dead-stock-item-${p.id}`}
                >
                  <div className="aspect-[4/5] overflow-hidden bg-[#0F0F0F] relative">
                    {imgSrc ? (
                      <img src={imgSrc} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#9CA3AF] text-xs">No image</div>
                    )}
                    {discount > 0 && (
                      <span
                        className="absolute top-2 left-2 text-[10px] uppercase tracking-wider px-2 py-1 bg-[#39FF14] text-black font-bold"
                        data-testid={`discount-badge-${p.id}`}
                      >
                        -{discount}%
                      </span>
                    )}
                    <span className="absolute top-2 right-2 text-[9px] uppercase tracking-wider px-2 py-1 bg-black/80 text-[#39FF14] border border-[#39FF14]/30 font-bold">
                      Dead Stock
                    </span>
                  </div>
                  <div className="p-3">
                    <p className="text-[10px] uppercase tracking-wider text-[#39FF14] mb-1 truncate">
                      {p.brand_name}
                    </p>
                    <h3 className="text-sm text-white font-medium mb-2 line-clamp-1">{p.name}</h3>
                    <div className="flex items-baseline gap-2 flex-wrap">
                      <span className="text-[#39FF14] font-bold text-base">£{Number(p.price).toFixed(2)}</span>
                      {p.original_price && p.original_price > p.price && (
                        <span className="text-xs text-[#6B7280] line-through" data-testid={`original-price-${p.id}`}>
                          £{Number(p.original_price).toFixed(2)}
                        </span>
                      )}
                    </div>
                    {p.shipping_cost === 0 && (
                      <p className="text-[10px] text-[#39FF14] mt-1 flex items-center gap-1">
                        <Truck className="w-2.5 h-2.5" /> Free shipping
                      </p>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
