import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Cookie, X } from 'lucide-react';

const STORAGE_KEY = 'ut_cookie_ack_v1';

export default function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY)) {
        // Small delay so it doesn't pop in before the page paints
        const t = setTimeout(() => setVisible(true), 800);
        return () => clearTimeout(t);
      }
    } catch (e) {
      // localStorage can throw in Safari private mode / when blocked.
      // Don't fail loud — log for debugging and skip the banner this session.
      console.warn('CookieBanner: localStorage unavailable', e);
    }
  }, []);

  const acknowledge = () => {
    try {
      localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    } catch (e) {
      // Storage may be blocked — banner will re-appear next visit, which is acceptable
      console.warn('CookieBanner: could not persist acknowledgement', e);
    }
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      className="fixed bottom-4 left-4 right-4 md:left-6 md:right-auto md:max-w-md z-[100]"
      data-testid="cookie-banner"
      role="region"
      aria-label="Cookie notice"
    >
      <div className="bg-[#0F0F0F] border border-[#39FF14]/40 shadow-2xl shadow-[#39FF14]/10 p-5 backdrop-blur-xl">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-8 h-8 border border-[#39FF14]/40 flex items-center justify-center">
            <Cookie className="w-4 h-4 text-[#39FF14]" />
          </div>
          <div className="flex-1">
            <p className="text-xs uppercase tracking-[0.2em] text-[#39FF14] font-bold mb-1">
              Cookies
            </p>
            <p className="text-sm text-[#C0C0C0] leading-relaxed mb-3">
              We only use <span className="text-white font-semibold">strictly necessary cookies</span> to keep you
              signed in and protect your account. No advertising trackers, no analytics tags.
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={acknowledge}
                className="px-4 py-1.5 bg-[#39FF14] text-black hover:bg-[#39FF14]/90 text-xs font-bold uppercase tracking-wider transition-colors"
                data-testid="cookie-accept-button"
              >
                Got it
              </button>
              <Link
                to="/privacy"
                className="text-xs text-[#9CA3AF] hover:text-[#39FF14] underline transition-colors"
                data-testid="cookie-privacy-link"
              >
                Read the policy
              </Link>
            </div>
          </div>
          <button
            onClick={acknowledge}
            className="text-[#9CA3AF] hover:text-white transition-colors"
            aria-label="Dismiss cookie notice"
            data-testid="cookie-dismiss-button"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
