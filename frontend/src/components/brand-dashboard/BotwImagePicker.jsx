import { useMemo, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Crown, Check, Clock, XCircle } from 'lucide-react';
import ImageUpload from '../ImageUpload';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Brand-of-the-Week homepage image chooser.
 *
 * Only rendered when `brandData.is_brand_of_week` is true. The brand
 * picks one of its own product images to serve as the front-page hero;
 * the selection enters `pending` and only goes live once admin approves.
 *
 * States (from brandData.botw_image_status):
 *   null / undefined → no submission yet
 *   'pending'        → awaiting admin decision, current live image =
 *                      previously-approved (if any) or banner_url fallback
 *   'approved'       → live on the homepage
 *   'rejected'       → admin said no; brand can resubmit
 */
export function BotwImagePicker({ brandData, products, onSubmitted }) {
  const [submitting, setSubmitting] = useState(null);

  const allImages = useMemo(() => {
    const seen = new Set();
    const out = [];
    (products || []).forEach((p) => {
      (p.images || []).forEach((url) => {
        if (!seen.has(url)) {
          seen.add(url);
          out.push({ url, product_name: p.name });
        }
      });
    });
    return out;
  }, [products]);

  if (!brandData?.is_brand_of_week) return null;

  const status = brandData.botw_image_status;
  const pending = brandData.botw_featured_image_pending;
  const approved = brandData.botw_featured_image_approved;

  const submit = async (url) => {
    setSubmitting(url);
    try {
      await axios.post(`${API}/api/brands/me/botw-image`, { image_url: url }, { withCredentials: true });
      toast.success('Sent for admin approval — you\'ll see the change on the homepage once it\'s approved.');
      if (onSubmitted) onSubmitted();
    } catch (e) {
      const detail = e.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Could not submit image');
    } finally {
      setSubmitting(null);
    }
  };

  // Fresh device upload: the URL comes back from /api/upload/image after it
  // clears magic-byte + moderation checks, then we send it through the same
  // botw-image endpoint so admin approval still gates the homepage swap.
  const submitFresh = async (freshUrl) => {
    if (!freshUrl) return;
    setSubmitting('__fresh__');
    try {
      await axios.post(`${API}/api/brands/me/botw-image`, { image_url: freshUrl }, { withCredentials: true });
      toast.success('New photo sent for admin approval — you\'ll see it on the homepage once it\'s approved.');
      if (onSubmitted) onSubmitted();
    } catch (e) {
      const detail = e.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Could not submit image');
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className="mb-12 border border-[#39FF14]/30 bg-[#39FF14]/5 p-6" data-testid="botw-image-picker">
      <div className="flex items-start gap-4">
        <Crown className="w-8 h-8 text-[#39FF14] flex-shrink-0" />
        <div className="flex-1">
          <h3 className="text-xl font-bold text-white mb-1" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            BRAND OF THE WEEK — HOMEPAGE IMAGE
          </h3>
          <p className="text-sm text-[#9CA3AF] mb-4">
            Pick one of your product images to feature on the Unveiled Threads homepage this week.
            An admin will approve it before it goes live to buyers.
          </p>

          {/* Status pill */}
          {status === 'pending' && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-4 border border-yellow-500/40 bg-yellow-500/10 text-yellow-300 text-xs uppercase tracking-wider"
                 data-testid="botw-status-pending">
              <Clock className="w-3 h-3" />
              Awaiting admin approval
            </div>
          )}
          {status === 'approved' && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-4 border border-[#39FF14]/40 bg-[#39FF14]/10 text-[#39FF14] text-xs uppercase tracking-wider"
                 data-testid="botw-status-approved">
              <Check className="w-3 h-3" />
              Live on the homepage
            </div>
          )}
          {status === 'rejected' && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-4 border border-red-500/40 bg-red-500/10 text-red-400 text-xs uppercase tracking-wider"
                 data-testid="botw-status-rejected">
              <XCircle className="w-3 h-3" />
              Not approved — try another image
            </div>
          )}

          {allImages.length === 0 ? (
            <p className="text-sm text-[#9CA3AF]">Upload a product first, or pick a fresh photo from your device below.</p>
          ) : (
            <>
              <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF] mb-2">Reuse one of your product photos</p>
              <div className="grid grid-cols-3 sm:grid-cols-5 md:grid-cols-6 gap-2 mb-6" data-testid="botw-image-grid">
              {allImages.map(({ url, product_name }) => {
                const isPending = url === pending && status === 'pending';
                const isApproved = url === approved && status === 'approved';
                const isChosen = isPending || isApproved;
                return (
                  <button
                    key={url}
                    type="button"
                    onClick={() => submit(url)}
                    disabled={submitting === url || isChosen}
                    aria-label={`Feature image from ${product_name}`}
                    className={`relative aspect-square overflow-hidden bg-[#0F0F0F] transition-all ${
                      isChosen
                        ? 'border-2 border-[#39FF14] ring-1 ring-[#39FF14]/40 cursor-default'
                        : 'border border-white/10 hover:border-[#39FF14]/60'
                    } disabled:opacity-70`}
                    data-testid={`botw-tile-${allImages.indexOf({ url, product_name })}`}
                  >
                    <img
                      src={url.startsWith('/api/') ? `${API}${url}` : url}
                      alt={product_name}
                      className="w-full h-full object-cover"
                    />
                    {isChosen && (
                      <span
                        className={`absolute top-1 left-1 flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 ${
                          isApproved ? 'bg-[#39FF14] text-black' : 'bg-yellow-500 text-black'
                        }`}
                      >
                        {isApproved ? <Check className="w-2.5 h-2.5" /> : <Clock className="w-2.5 h-2.5" />}
                        {isApproved ? 'Live' : 'Pending'}
                      </span>
                    )}
                    {submitting === url && (
                      <span className="absolute inset-0 flex items-center justify-center bg-black/60 text-[#39FF14] text-[10px] uppercase">
                        Sending…
                      </span>
                    )}
                  </button>
                );
              })}
              </div>
            </>
          )}

          {/* Fresh device upload — camera roll / files. Native <input type="file">
              so the browser only surrenders the specific photo the brand picks. */}
          <div className="border-t border-white/10 pt-4 mt-2" data-testid="botw-fresh-upload">
            <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF] mb-2">
              Or upload a fresh hero shot from your device
            </p>
            <ImageUpload
              stageBeforeUpload
              multiple={false}
              label="Choose photo from device"
              onUpload={submitFresh}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
