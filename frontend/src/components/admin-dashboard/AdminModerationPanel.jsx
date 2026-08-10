import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { ShieldCheck, CheckCircle, XCircle, Loader2, ExternalLink } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Admin queue for products whose images landed in `needs_review`.
 *
 * Backend contract:
 *   GET  /api/admin/moderation/products             → list flagged/unverified
 *   POST /api/admin/moderation/products/{id}        → {approve: bool}
 * `approve: true`  → moderation_status='passed' (visible)
 * `approve: false` → moderation_status='flagged' (hidden from public list)
 */
export function AdminModerationPanel() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(null);

  const fetchQueue = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/api/admin/moderation/products`, { withCredentials: true });
      setItems(Array.isArray(r.data) ? r.data : []);
    } catch (e) {
      toast.error('Could not load moderation queue');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchQueue(); }, [fetchQueue]);

  const decide = async (id, approve) => {
    setProcessing(id);
    try {
      await axios.post(
        `${API}/api/admin/moderation/products/${id}`,
        { approve },
        { withCredentials: true }
      );
      toast.success(approve ? 'Approved — product is live.' : 'Taken down — hidden from the public list.');
      // Drop the item locally instead of a full refetch (snappier).
      setItems((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      const detail = e.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Could not update moderation status');
    } finally {
      setProcessing(null);
    }
  };

  return (
    <div className="mb-12" data-testid="admin-moderation-section">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold uppercase text-white flex items-center gap-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
          <ShieldCheck className="w-5 h-5 text-[#39FF14]" />
          Image moderation
        </h2>
        <span
          className="text-xs uppercase tracking-wider px-3 py-1 bg-[#39FF14]/10 text-[#39FF14] border border-[#39FF14]/30"
          data-testid="moderation-queue-count"
        >
          {items.length} to review
        </span>
      </div>

      {loading ? (
        <div className="border border-white/10 bg-[#0A0A0A] p-8 text-center text-[#9CA3AF]">
          <Loader2 className="w-5 h-5 animate-spin inline mr-2 text-[#39FF14]" />
          Loading queue…
        </div>
      ) : items.length === 0 ? (
        <div className="border border-white/10 bg-[#0A0A0A] p-8 text-center">
          <ShieldCheck className="w-8 h-8 text-[#39FF14]/30 mx-auto mb-3" />
          <p className="text-[#9CA3AF] text-sm">Nothing waiting. Every listing has passed automated checks.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((p) => {
            const mod = Array.isArray(p.images_moderation) ? p.images_moderation : [];
            const flaggedIdx = mod.map((m, i) => m.status !== 'passed' ? i : -1).filter((i) => i >= 0);
            return (
              <div key={p.id} className="border border-yellow-500/30 bg-yellow-500/5 p-5" data-testid={`moderation-item-${p.id}`}>
                <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                  <div>
                    <p className="text-xs uppercase tracking-wider text-yellow-300 font-bold mb-1">
                      Needs review · £{Number(p.price || 0).toFixed(2)}
                    </p>
                    <p className="text-white font-bold">{p.name}</p>
                    <p className="text-xs text-[#9CA3AF]">
                      {p.brand_name || 'Unknown brand'} · {p.category}
                    </p>
                  </div>
                  <a
                    href={`/products/${p.id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs uppercase tracking-wider text-[#39FF14] hover:text-white transition-colors flex items-center gap-1"
                    data-testid={`moderation-open-product-${p.id}`}
                  >
                    Open listing <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                {/* Image thumbnails with a per-image status badge */}
                <div className="grid grid-cols-4 sm:grid-cols-6 gap-2 mb-3">
                  {(p.images || []).map((url, i) => {
                    const entry = mod.find((m) => m.index === i) || {};
                    const status = entry.status || 'unknown';
                    return (
                      <div key={`${p.id}-${i}`} className="relative aspect-square overflow-hidden border border-white/10 bg-[#0F0F0F]">
                        <img
                          src={url.startsWith('/api/') ? `${API}${url}` : url}
                          alt={`Image ${i + 1}`}
                          className="w-full h-full object-cover"
                        />
                        <span
                          className={`absolute bottom-1 left-1 text-[9px] uppercase tracking-wider px-1.5 py-0.5 ${
                            status === 'passed' ? 'bg-[#39FF14] text-black' :
                            status === 'flagged' ? 'bg-red-500 text-white' :
                            'bg-yellow-500 text-black'
                          }`}
                        >
                          {status}
                        </span>
                      </div>
                    );
                  })}
                </div>

                <p className="text-xs text-[#9CA3AF] mb-3">
                  {flaggedIdx.length > 0
                    ? `Non-passed image position${flaggedIdx.length > 1 ? 's' : ''}: ${flaggedIdx.map((i) => i + 1).join(', ')}`
                    : 'No image flagged — sitting in queue because no provider verdict is stored.'}
                </p>

                <div className="flex gap-2 flex-wrap">
                  <Button
                    className="btn-primary text-sm py-2"
                    onClick={() => decide(p.id, true)}
                    disabled={processing === p.id}
                    data-testid={`moderation-approve-${p.id}`}
                  >
                    {processing === p.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-1" />}
                    Approve
                  </Button>
                  <Button
                    className="btn-secondary text-sm py-2 text-red-400 hover:text-red-300"
                    onClick={() => decide(p.id, false)}
                    disabled={processing === p.id}
                    data-testid={`moderation-takedown-${p.id}`}
                  >
                    <XCircle className="w-4 h-4 mr-1" />
                    Take down
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
