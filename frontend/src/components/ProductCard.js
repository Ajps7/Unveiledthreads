import { Link } from 'react-router-dom';
import { Heart } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ProductCard({ product, isWishlisted = false, onWishlistToggle, showWishlist = false }) {

  const handleWishlistClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!onWishlistToggle) return;
    try {
      if (isWishlisted) {
        await axios.delete(`${API}/api/wishlist/${product.id}`, { withCredentials: true });
      } else {
        await axios.post(`${API}/api/wishlist/${product.id}`, {}, { withCredentials: true });
      }
      onWishlistToggle(product.id, !isWishlisted);
    } catch (err) {
      // If 401 (not logged in), ignore silently
      if (err.response?.status !== 401) console.error(err);
    }
  };

  const imgSrc = product.images && product.images.length > 0
    ? (product.images[0].startsWith('/api/') ? `${API}${product.images[0]}` : product.images[0])
    : null;

  return (
    <Link
      to={`/products/${product.id}`}
      className="card-product group relative"
      data-testid={`product-card-${product.id}`}
    >
      <div className="aspect-[3/4] overflow-hidden bg-[#0F0F0F] relative">
        {imgSrc ? (
          <img
            src={imgSrc}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[#9CA3AF]">
            No Image
          </div>
        )}

        {product.is_preorder && (
          <span
            className="absolute top-3 left-3 z-10 bg-[#39FF14] text-black text-[10px] font-bold px-2 py-1 uppercase tracking-wider"
            data-testid={`preorder-badge-${product.id}`}
          >
            Pre-order
          </span>
        )}

        {/* Wishlist heart */}
        {showWishlist && (
          <button
            onClick={handleWishlistClick}
            className="absolute top-3 right-3 z-10 p-2 bg-black/50 backdrop-blur-sm border border-white/10 hover:border-[#39FF14]/50 transition-all"
            data-testid={`wishlist-toggle-${product.id}`}
          >
            <Heart
              className={`w-4 h-4 transition-colors ${isWishlisted ? 'fill-[#39FF14] text-[#39FF14]' : 'text-white/70 hover:text-white'}`}
            />
          </button>
        )}
      </div>

      <div className="p-4 border-t border-white/10">
        <p className="text-xs text-[#39FF14] uppercase tracking-wider mb-1">
          {product.brand_name}
        </p>
        <h3 className="text-white font-medium mb-2 line-clamp-1 group-hover:text-[#39FF14] transition-colors">
          {product.name}
        </h3>
        {product.is_preorder && product.preorder_ship_date && (
          <p className="text-[10px] text-[#39FF14] mb-1" data-testid={`preorder-ship-by-${product.id}`}>
            Ships by {product.preorder_ship_date}
          </p>
        )}
        <div className="flex items-center justify-between">
          <span className="text-[#C0C0C0] font-bold">
            £{product.price.toFixed(2)}
          </span>
          <span className="badge-category text-[10px]">
            {product.category}
          </span>
        </div>
      </div>
    </Link>
  );
}

export function ProductCardSkeleton() {
  return (
    <div className="card-product">
      <div className="aspect-[3/4] bg-[#0F0F0F] animate-pulse" />
      <div className="p-4 border-t border-white/10 space-y-2">
        <div className="h-3 w-16 bg-[#0F0F0F] animate-pulse" />
        <div className="h-4 w-3/4 bg-[#0F0F0F] animate-pulse" />
        <div className="h-4 w-1/3 bg-[#0F0F0F] animate-pulse" />
      </div>
    </div>
  );
}
