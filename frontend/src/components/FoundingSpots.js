import { useState, useEffect } from 'react';
import axios from 'axios';
import { Gem } from 'lucide-react';
import { FoundingBadge } from './FoundingBadge';

const API = process.env.REACT_APP_BACKEND_URL;

const useFoundingSpots = () => {
  const [spots, setSpots] = useState(null);
  useEffect(() => {
    axios.get(`${API}/api/brands/founding-spots`)
      .then((r) => setSpots(r.data))
      .catch(() => setSpots(null));
  }, []);
  return spots;
};

export const FoundingSpotsBanner = () => {
  const spots = useFoundingSpots();
  if (!spots || spots.remaining <= 0) return null;
  return (
    <div className="relative border border-white/10 bg-[#0A0A0A] p-6 mb-8 overflow-hidden" data-testid="founding-spots-banner">
      <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-[#C0C0C0] via-[#39FF14] to-[#C0C0C0]" />
      <div className="flex items-start gap-4 pl-2">
        <Gem className="w-7 h-7 text-[#39FF14] flex-shrink-0 mt-1" />
        <div>
          <div className="flex items-center gap-3 flex-wrap mb-2">
            <h3 className="text-white font-bold uppercase tracking-tight" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Become a Founding Brand
            </h3>
            <FoundingBadge size="sm" />
          </div>
          <p className="text-[#9CA3AF] text-sm leading-relaxed">
            The first {spots.limit} brands to join carry the Founding Brand badge permanently — on your
            profile, every product and the brands page. Once the spots are gone, they're gone.
          </p>
          <p className="text-[#39FF14] font-bold text-sm mt-2" data-testid="founding-spots-remaining">
            Only {spots.remaining} of {spots.limit} founding spots left
          </p>
        </div>
      </div>
    </div>
  );
};

export const FoundingSpotsCounter = () => {
  const spots = useFoundingSpots();
  if (!spots) return null;
  return (
    <p className="text-sm text-[#9CA3AF] mb-6 flex items-center justify-center gap-2" data-testid="founding-spots-counter">
      <Gem className="w-3.5 h-3.5 text-[#39FF14]" />
      {spots.remaining > 0 ? (
        <>
          <span className="text-[#39FF14] font-bold">{spots.taken}/{spots.limit}</span>
          founding spots taken — apply while the badge lasts
        </>
      ) : (
        <>All {spots.limit} founding spots are taken</>
      )}
    </p>
  );
};
