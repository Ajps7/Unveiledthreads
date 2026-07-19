import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Search, X, SlidersHorizontal, ChevronDown, ChevronUp, Truck } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import Header from '../components/Header';
import ProductCard, { ProductCardSkeleton } from '../components/ProductCard';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

function FilterSection({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-white/5 py-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full text-left"
      >
        <span className="text-xs font-bold text-[#C0C0C0] uppercase tracking-wider">{title}</span>
        {open ? <ChevronUp className="w-4 h-4 text-[#9CA3AF]" /> : <ChevronDown className="w-4 h-4 text-[#9CA3AF]" />}
      </button>
      {open && <div className="mt-3">{children}</div>}
    </div>
  );
}

function ChipSelect({ options, value, onChange, multi = false }) {
  const handleClick = (val) => {
    if (multi) {
      onChange(value.includes(val) ? value.filter(v => v !== val) : [...value, val]);
    } else {
      onChange(value === val ? '' : val);
    }
  };

  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => {
        const optVal = typeof opt === 'string' ? opt : opt.id;
        const optLabel = typeof opt === 'string' ? opt : opt.name;
        const isActive = multi ? value.includes(optVal) : value === optVal;
        return (
          <button
            key={optVal}
            onClick={() => handleClick(optVal)}
            className={`px-3 py-1.5 text-xs border transition-all ${
              isActive
                ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                : 'border-white/10 text-[#9CA3AF] hover:border-white/30 hover:text-white'
            }`}
          >
            {optLabel}
          </button>
        );
      })}
    </div>
  );
}

export default function Products() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filterOptions, setFilterOptions] = useState(null);
  const [wishlistIds, setWishlistIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [activeFilterCount, setActiveFilterCount] = useState(0);

  // Filter state
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [filters, setFilters] = useState({
    category: searchParams.get('category') || 'all',
    size: searchParams.get('size') || '',
    colour: searchParams.get('colour') || '',
    material: searchParams.get('material') || '',
    gender: searchParams.get('gender') || 'all',
    condition: searchParams.get('condition') || 'all',
    fit: searchParams.get('fit') || '',
    min_price: searchParams.get('min_price') || '',
    max_price: searchParams.get('max_price') || '',
    sort: searchParams.get('sort') || 'latest',
    in_stock: searchParams.get('in_stock') === 'true',
    free_shipping: searchParams.get('free_shipping') === 'true',
    is_dead_stock: searchParams.get('is_dead_stock') === 'true',
  });

  const searchQueryRef = useRef(searchQuery);
  useEffect(() => { searchQueryRef.current = searchQuery; }, [searchQuery]);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/categories`);
      setCategories(res.data);
    } catch (e) { console.error(e); }
  }, []);

  const fetchFilterOptions = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/products/filter-options`);
      setFilterOptions(res.data);
    } catch (e) { console.error(e); }
  }, []);

  const fetchWishlistIds = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/wishlist/ids`, { withCredentials: true });
      setWishlistIds(res.data);
    } catch (e) { /* not logged in — wishlist unavailable */ }
  }, []);

  const handleWishlistToggle = (productId, nowWishlisted) => {
    setWishlistIds(prev => nowWishlisted ? [...prev, productId] : prev.filter(id => id !== productId));
  };

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      const search = searchParams.get('search');
      if (search) params.append('search', search);

      for (const [key, val] of searchParams.entries()) {
        if (key !== 'search' && val && val !== 'all' && val !== '') {
          params.append(key, val);
        }
      }

      // Default: exclude dead stock from the main shop. Buyers can opt in
      // via the "Dead Stock only" filter, which flips this to true.
      if (!params.has('is_dead_stock')) {
        params.append('is_dead_stock', 'false');
      }

      const res = await axios.get(`${API}/api/products?${params.toString()}`);
      setProducts(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [searchParams]);

  const countActiveFilters = useCallback(() => {
    let count = 0;
    for (const [key, val] of searchParams.entries()) {
      if (key === 'search' || key === 'sort') continue;
      if (val && val !== 'all' && val !== '' && val !== 'false') count++;
    }
    setActiveFilterCount(count);
  }, [searchParams]);

  const applyFilters = useCallback(() => {
    const params = new URLSearchParams();
    if (searchQueryRef.current) params.set('search', searchQueryRef.current);
    for (const [key, val] of Object.entries(filters)) {
      if (val && val !== 'all' && val !== '' && val !== false) {
        params.set(key, val.toString());
      }
    }
    setSearchParams(params);
  }, [filters, setSearchParams]);

  useEffect(() => {
    fetchCategories();
    fetchFilterOptions();
  }, [fetchCategories, fetchFilterOptions]);

  useEffect(() => {
    fetchProducts();
    countActiveFilters();
  }, [fetchProducts, countActiveFilters]);

  useEffect(() => {
    if (user) fetchWishlistIds();
  }, [user, fetchWishlistIds]);

  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setSearchQuery('');
    setFilters({
      category: 'all', size: '', colour: '', material: '', gender: 'all',
      condition: 'all', fit: '', min_price: '', max_price: '', sort: 'latest',
      in_stock: false, free_shipping: false, is_dead_stock: false,
    });
    setSearchParams({});
  };

  const handleSearch = (e) => {
    e.preventDefault();
    applyFilters();
  };

  // Auto-apply when filters change (applyFilters identity tracks `filters`)
  useEffect(() => {
    const timeout = setTimeout(() => applyFilters(), 300);
    return () => clearTimeout(timeout);
  }, [applyFilters]);

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      {/* Hero */}
      <section className="py-12 px-6 md:px-12 border-b border-white/10 bg-[#0A0A0A]">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-black tracking-tighter uppercase mb-3 text-white" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="products-page-title">
            SHOP ALL
          </h1>
          <p className="text-[#9CA3AF]">Discover exclusive streetwear from emerging independent UK brands</p>
        </div>
      </section>

      {/* Search + Filter Toggle */}
      <section className="py-4 px-6 md:px-12 border-b border-white/10 sticky top-16 z-40 bg-[#050505]/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row gap-3 items-start md:items-center justify-between">
          <form onSubmit={handleSearch} className="flex gap-2 w-full md:w-auto">
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search products, brands..."
              className="input-brutalist w-full md:w-80"
              data-testid="products-search-input"
            />
            <Button type="submit" className="btn-secondary px-4" data-testid="products-search-button">
              <Search className="w-5 h-5" />
            </Button>
          </form>

          <div className="flex items-center gap-3">
            {/* Sort */}
            <Select value={filters.sort} onValueChange={(v) => updateFilter('sort', v)}>
              <SelectTrigger className="w-[170px] bg-transparent border-white/20 rounded-none text-white text-sm" data-testid="sort-select">
                <SelectValue placeholder="Sort" />
              </SelectTrigger>
              <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                <SelectItem value="latest" className="text-white hover:bg-white/10 rounded-none">Latest</SelectItem>
                <SelectItem value="price_low" className="text-white hover:bg-white/10 rounded-none">Price: Low to High</SelectItem>
                <SelectItem value="price_high" className="text-white hover:bg-white/10 rounded-none">Price: High to Low</SelectItem>
                <SelectItem value="popular" className="text-white hover:bg-white/10 rounded-none">Popular</SelectItem>
              </SelectContent>
            </Select>

            {/* Filter toggle */}
            <Button
              className={`btn-secondary text-sm ${showFilters ? 'border-[#39FF14] text-[#39FF14]' : ''}`}
              onClick={() => setShowFilters(!showFilters)}
              data-testid="toggle-filters"
            >
              <SlidersHorizontal className="w-4 h-4 mr-2" />
              Filters
              {activeFilterCount > 0 && (
                <span className="ml-1.5 w-5 h-5 bg-[#39FF14] text-black text-[10px] font-bold rounded-full flex items-center justify-center">
                  {activeFilterCount}
                </span>
              )}
            </Button>

            {activeFilterCount > 0 && (
              <Button variant="ghost" onClick={clearFilters} className="text-[#9CA3AF] hover:text-white text-sm" data-testid="clear-filters-button">
                <X className="w-4 h-4 mr-1" /> Clear all
              </Button>
            )}
          </div>
        </div>
      </section>

      <div className="max-w-7xl mx-auto px-6 md:px-12 py-8">
        <div className="flex gap-8">
          {/* Filter Sidebar */}
          {showFilters && filterOptions && (
            <aside className="w-64 flex-shrink-0 hidden md:block" data-testid="filter-sidebar">
              <div className="sticky top-36 border border-white/10 bg-[#0A0A0A] p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-white uppercase">Filters</h3>
                  {activeFilterCount > 0 && (
                    <button onClick={clearFilters} className="text-xs text-[#39FF14] hover:underline">Clear all</button>
                  )}
                </div>

                {/* Category */}
                <FilterSection title="Category" defaultOpen>
                  <Select value={filters.category} onValueChange={(v) => updateFilter('category', v)}>
                    <SelectTrigger className="w-full bg-transparent border-white/20 rounded-none text-white text-xs">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                      <SelectItem value="all" className="text-white hover:bg-white/10 rounded-none">All Categories</SelectItem>
                      {categories.map((c) => (
                        <SelectItem key={c.id} value={c.id} className="text-white hover:bg-white/10 rounded-none">{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FilterSection>

                {/* Size */}
                <FilterSection title="Size" defaultOpen>
                  <ChipSelect
                    options={filterOptions.sizes}
                    value={filters.size}
                    onChange={(v) => updateFilter('size', v)}
                  />
                </FilterSection>

                {/* Colour */}
                <FilterSection title="Colour">
                  <ChipSelect
                    options={filterOptions.colours}
                    value={filters.colour}
                    onChange={(v) => updateFilter('colour', v)}
                  />
                </FilterSection>

                {/* Material */}
                <FilterSection title="Material">
                  <ChipSelect
                    options={filterOptions.materials}
                    value={filters.material}
                    onChange={(v) => updateFilter('material', v)}
                  />
                </FilterSection>

                {/* Fit */}
                <FilterSection title="Fit">
                  <ChipSelect
                    options={filterOptions.fits}
                    value={filters.fit}
                    onChange={(v) => updateFilter('fit', v)}
                  />
                </FilterSection>

                {/* Gender */}
                <FilterSection title="Gender">
                  <ChipSelect
                    options={filterOptions.genders}
                    value={filters.gender}
                    onChange={(v) => updateFilter('gender', v)}
                  />
                </FilterSection>

                {/* Condition */}
                <FilterSection title="Condition">
                  <ChipSelect
                    options={filterOptions.conditions}
                    value={filters.condition}
                    onChange={(v) => updateFilter('condition', v)}
                  />
                </FilterSection>

                {/* Price Range */}
                <FilterSection title="Price (£)">
                  <div className="flex gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={filters.min_price}
                      onChange={(e) => updateFilter('min_price', e.target.value)}
                      className="input-brutalist text-xs"
                      data-testid="min-price-input"
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={filters.max_price}
                      onChange={(e) => updateFilter('max_price', e.target.value)}
                      className="input-brutalist text-xs"
                      data-testid="max-price-input"
                    />
                  </div>
                </FilterSection>

                {/* Quick filters */}
                <FilterSection title="Quick Filters">
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.in_stock}
                        onChange={(e) => updateFilter('in_stock', e.target.checked)}
                        className="accent-[#39FF14]"
                        data-testid="in-stock-checkbox"
                      />
                      <span className="text-xs text-[#C0C0C0]">In Stock Only</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.free_shipping}
                        onChange={(e) => updateFilter('free_shipping', e.target.checked)}
                        className="accent-[#39FF14]"
                        data-testid="free-shipping-checkbox"
                      />
                      <span className="text-xs text-[#C0C0C0] flex items-center gap-1"><Truck className="w-3 h-3" /> Free Shipping</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.is_dead_stock}
                        onChange={(e) => updateFilter('is_dead_stock', e.target.checked)}
                        className="accent-[#39FF14]"
                        data-testid="dead-stock-checkbox"
                      />
                      <span className="text-xs text-[#39FF14] font-bold">Dead Stock Only</span>
                    </label>
                  </div>
                </FilterSection>
              </div>
            </aside>
          )}

          {/* Mobile filters */}
          {showFilters && filterOptions && (
            <div className="md:hidden fixed inset-0 z-50 bg-black/90 overflow-y-auto pt-20 px-6 pb-6" data-testid="mobile-filters">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white uppercase">Filters</h3>
                <Button variant="ghost" onClick={() => setShowFilters(false)} className="text-white"><X className="w-5 h-5" /></Button>
              </div>
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-[#C0C0C0] uppercase mb-2">Size</p>
                  <ChipSelect options={filterOptions.sizes} value={filters.size} onChange={(v) => updateFilter('size', v)} />
                </div>
                <div>
                  <p className="text-xs text-[#C0C0C0] uppercase mb-2">Colour</p>
                  <ChipSelect options={filterOptions.colours} value={filters.colour} onChange={(v) => updateFilter('colour', v)} />
                </div>
                <div>
                  <p className="text-xs text-[#C0C0C0] uppercase mb-2">Material</p>
                  <ChipSelect options={filterOptions.materials} value={filters.material} onChange={(v) => updateFilter('material', v)} />
                </div>
                <div>
                  <p className="text-xs text-[#C0C0C0] uppercase mb-2">Gender</p>
                  <ChipSelect options={filterOptions.genders} value={filters.gender} onChange={(v) => updateFilter('gender', v)} />
                </div>
                <Button className="btn-primary w-full mt-4" onClick={() => setShowFilters(false)}>Apply Filters</Button>
              </div>
            </div>
          )}

          {/* Products */}
          <div className="flex-1">
            <div className="mb-6 flex items-center justify-between">
              <p className="text-sm text-[#9CA3AF]">
                {loading ? 'Loading...' : `${products.length} product${products.length !== 1 ? 's' : ''} found`}
              </p>

              {/* Active filter chips */}
              {activeFilterCount > 0 && (
                <div className="flex flex-wrap gap-2">
                  {filters.size && (
                    <span className="badge-boost text-[10px] flex items-center gap-1">
                      Size: {filters.size} <button onClick={() => updateFilter('size', '')}><X className="w-3 h-3" /></button>
                    </span>
                  )}
                  {filters.colour && (
                    <span className="badge-boost text-[10px] flex items-center gap-1">
                      {filters.colour} <button onClick={() => updateFilter('colour', '')}><X className="w-3 h-3" /></button>
                    </span>
                  )}
                  {filters.material && (
                    <span className="badge-boost text-[10px] flex items-center gap-1">
                      {filters.material} <button onClick={() => updateFilter('material', '')}><X className="w-3 h-3" /></button>
                    </span>
                  )}
                </div>
              )}
            </div>

            {loading ? (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-6" data-testid="products-loading">
                {[...Array(6)].map((_, i) => <ProductCardSkeleton key={i} />)}
              </div>
            ) : products.length > 0 ? (
              <div className={`grid gap-6 ${showFilters ? 'grid-cols-2 md:grid-cols-3' : 'grid-cols-2 md:grid-cols-3 lg:grid-cols-4'}`} data-testid="products-grid">
                {products.map((product) => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    showWishlist={!!user}
                    isWishlisted={wishlistIds.includes(product.id)}
                    onWishlistToggle={handleWishlistToggle}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-20 border border-white/10 bg-[#0A0A0A]" data-testid="no-products">
                <p className="text-[#9CA3AF] mb-4">No products match your filters</p>
                <Button onClick={clearFilters} className="btn-secondary">Clear Filters</Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
