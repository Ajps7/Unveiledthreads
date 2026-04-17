import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Search, X } from 'lucide-react';
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

export default function Products() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [wishlistIds, setWishlistIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [selectedCategory, setSelectedCategory] = useState(searchParams.get('category') || 'all');

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [searchParams]);

  useEffect(() => {
    if (user) fetchWishlistIds();
  }, [user]);

  const fetchWishlistIds = async () => {
    try {
      const res = await axios.get(`${API}/api/wishlist/ids`, { withCredentials: true });
      setWishlistIds(res.data);
    } catch (e) { /* ignore */ }
  };

  const handleWishlistToggle = (productId, nowWishlisted) => {
    setWishlistIds(prev => nowWishlisted ? [...prev, productId] : prev.filter(id => id !== productId));
  };

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/api/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      const search = searchParams.get('search');
      const category = searchParams.get('category');
      
      if (search) params.append('search', search);
      if (category && category !== 'all') params.append('category', category);
      
      const response = await axios.get(`${API}/api/products?${params.toString()}`);
      setProducts(response.data);
    } catch (error) {
      console.error('Error fetching products:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    const params = new URLSearchParams(searchParams);
    if (searchQuery) {
      params.set('search', searchQuery);
    } else {
      params.delete('search');
    }
    setSearchParams(params);
  };

  const handleCategoryChange = (value) => {
    setSelectedCategory(value);
    const params = new URLSearchParams(searchParams);
    if (value && value !== 'all') {
      params.set('category', value);
    } else {
      params.delete('category');
    }
    setSearchParams(params);
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedCategory('all');
    setSearchParams({});
  };

  const hasFilters = searchParams.get('search') || searchParams.get('category');

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      {/* Hero Banner */}
      <section className="py-16 px-6 md:px-12 border-b border-white/10 bg-[#0A0A0A]">
        <div className="max-w-7xl mx-auto">
          <h1 
            className="text-4xl md:text-5xl font-black tracking-tighter uppercase mb-4 text-white"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="products-page-title"
          >
            SHOP ALL
          </h1>
          <p className="text-[#9CA3AF] max-w-2xl">
            Discover exclusive streetwear from emerging independent UK brands
          </p>
        </div>
      </section>

      {/* Filters */}
      <section className="py-6 px-6 md:px-12 border-b border-white/10 sticky top-16 z-40 bg-[#050505]/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
            {/* Search */}
            <form onSubmit={handleSearch} className="flex gap-2 w-full md:w-auto">
              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search products..."
                className="input-brutalist w-full md:w-80"
                data-testid="products-search-input"
              />
              <Button type="submit" className="btn-secondary px-4" data-testid="products-search-button">
                <Search className="w-5 h-5" />
              </Button>
            </form>

            {/* Category Filter */}
            <div className="flex items-center gap-4">
              <Select value={selectedCategory} onValueChange={handleCategoryChange}>
                <SelectTrigger className="w-[180px] bg-transparent border-white/20 rounded-none text-white" data-testid="category-select">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                  <SelectItem value="all" className="text-white hover:bg-white/10 rounded-none">All Categories</SelectItem>
                  {categories.map((cat) => (
                    <SelectItem key={cat.id} value={cat.id} className="text-white hover:bg-white/10 rounded-none">
                      {cat.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {hasFilters && (
                <Button 
                  variant="ghost" 
                  onClick={clearFilters}
                  className="text-[#9CA3AF] hover:text-white hover:bg-white/10 rounded-none"
                  data-testid="clear-filters-button"
                >
                  <X className="w-4 h-4 mr-2" />
                  Clear
                </Button>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Products Grid */}
      <section className="py-12 px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          {/* Results count */}
          <div className="mb-8">
            <p className="text-sm text-[#9CA3AF]">
              {loading ? 'Loading...' : `${products.length} products found`}
            </p>
          </div>

          {loading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6" data-testid="products-loading">
              {[...Array(8)].map((_, i) => (
                <ProductCardSkeleton key={i} />
              ))}
            </div>
          ) : products.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6" data-testid="products-grid">
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
            <div className="text-center py-20" data-testid="no-products">
              <p className="text-[#9CA3AF] mb-4">No products found</p>
              <Button onClick={clearFilters} className="btn-secondary">
                Clear Filters
              </Button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
