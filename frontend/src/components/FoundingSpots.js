import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Gem } from 'lucide-react';
import { FoundingBadge } from './FoundingBadge';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Live source of truth for the founding-cohort counter. The backend
 * `/api/brands/founding-spots` endpoint returns the real number of
 * founding brands onboarded OR the admin override, so this hook never
 * displays a fake / hardcoded value.
 */
const useFoundingSpots = () => {
  const [spots, setSpots] = useState(null);
  useEffect(() => {
    axios.get(`${API}/api/brands/founding-spots`)
      .then((r) => setSpots(r.data))
      .catch(() => setSpots(null));
  }, []);
  return spots;
};

/**
 * Banner shown on the brand application page. When the cohort is full
 * we swap to a "waitlist" framing and the CTA points at /apply which
 * already handles waitlist-mode submissions.
 */
export const FoundingSpotsBanner = () => {
  const spots = useFoundingSpots();
  if (!spots) return null;
  const full = spots.remaining <= 0;
  return (
    <div className="relative border border-white/10 bg-[#0A0A0A] p-6 mb-8 overflow-hidden" data-testid="founding-spots-banner">
      <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-[#C0C0C0] via-[#39FF14] to-[#C0C0C0]" />
      <div className="flex items-start gap-4 pl-2">
        <Gem className="w-7 h-7 text-[#39FF14] flex-shrink-0 mt-1" />
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap mb-2">
            <h3 className="text-white font-bold uppercase tracking-tight" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              {full ? 'Founding cohort full' : 'The Founding 20'}
            </h3>
            {!full && <FoundingBadge size="sm" />}
          </div>
          {full ? (
            <>
              <p className="text-[#9CA3AF] text-sm leading-relaxed">
                All {spots.limit} founding spots are claimed. We&apos;re running a waitlist for
                exceptional independent labels &mdash; if we see a fit we&apos;ll reach out the moment
                a spot opens.
              </p>
              <p className="text-[#39FF14] font-bold text-sm mt-3" data-testid="founding-cohort-full">
                Join the waitlist &rarr;
              </p>
            </>
          ) : (
            <>
              <p className="text-[#9CA3AF] text-sm leading-relaxed">
                We&apos;re curating the first {spots.limit} independent labels on Unveiled Threads.
                Selective by design, this is the founding cohort, and spots are limited.
              </p>
              <p className="text-[#39FF14] font-bold text-sm mt-2" data-testid="founding-spots-remaining">
                Only {spots.remaining} of {spots.limit} founding spots left
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * Compact counter used above the brand grid on /brands.
 * When the cohort is full we swap in a waitlist CTA so visitors
 * don't think the programme is still open.
 */
export const FoundingSpotsCounter = () => {
  const spots = useFoundingSpots();
  if (!spots) return null;
  const full = spots.remaining <= 0;
  if (full) {
    return (
      <p className="text-sm text-[#9CA3AF] mb-6 flex items-center justify-center gap-2" data-testid="founding-spots-counter-full">
        <Gem className="w-3.5 h-3.5 text-[#39FF14]" />
        All {spots.limit} founding spots are taken &mdash;{' '}
        <Link to="/apply" className="text-[#39FF14] hover:underline font-bold">
          join the waitlist
        </Link>
      </p>
    );
  }
  return (
    <p className="text-sm text-[#9CA3AF] mb-6 flex items-center justify-center gap-2" data-testid="founding-spots-counter">
      <Gem className="w-3.5 h-3.5 text-[#39FF14]" />
      <span className="text-[#39FF14] font-bold">{spots.taken}/{spots.limit}</span>
      founding spots taken &mdash; hand-picked, selective by design
    </p>
  );
};
