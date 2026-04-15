import { Link } from 'react-router-dom';
import { Zap } from 'lucide-react';

export default function ProductCard({ product }) {
  return (
    <Link 
      to={`/products/${product.id}`}
      className="card-product group"
      data-testid={`product-card-${product.id}`}
    >
      <div className="aspect-[3/4] overflow-hidden bg-[#0F0F0F] relative">
        {product.images && product.images.length > 0 ? (
          <img
            src={product.images[0]}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[#9CA3AF]">
            No Image
          </div>
        )}
      </div>
      
      <div className="p-4 border-t border-white/10">
        <p className="text-xs text-[#39FF14] uppercase tracking-wider mb-1">
          {product.brand_name}
        </p>
        <h3 className="text-white font-medium mb-2 line-clamp-1 group-hover:text-[#39FF14] transition-colors">
          {product.name}
        </h3>
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
