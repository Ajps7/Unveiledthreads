import { Link } from 'react-router-dom';
import { Zap, MapPin } from 'lucide-react';

export default function BrandCard({ brand, isBoosted = false }) {
  return (
    <Link 
      to={`/brands/${brand.id}`}
      className="card-brand group"
      data-testid={`brand-card-${brand.id}`}
    >
      {isBoosted && (
        <div className="absolute top-4 right-4">
          <span className="badge-boost flex items-center gap-1">
            <Zap className="w-3 h-3" />
            Boosted
          </span>
        </div>
      )}
      
      <div className="w-20 h-20 rounded-full overflow-hidden bg-[#1A1A1A] mb-4 border border-white/10 group-hover:border-[#39FF14]/50 transition-colors">
        {brand.logo_url ? (
          <img
            src={brand.logo_url}
            alt={brand.brand_name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-2xl font-bold text-[#39FF14]" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            {brand.brand_name.charAt(0)}
          </div>
        )}
      </div>
      
      <h3 
        className="text-lg font-bold text-white uppercase tracking-tight mb-2 group-hover:text-[#39FF14] transition-colors"
        style={{ fontFamily: 'Clash Display, sans-serif' }}
      >
        {brand.brand_name}
      </h3>
      
      <p className="text-sm text-[#9CA3AF] line-clamp-2 mb-4">
        {brand.description}
      </p>
      
      <div className="flex items-center gap-4 text-xs text-[#C0C0C0]">
        <span className="flex items-center gap-1">
          <MapPin className="w-3 h-3" />
          {brand.location}
        </span>
      </div>
    </Link>
  );
}
