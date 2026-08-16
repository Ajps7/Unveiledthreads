import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Crown, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Admin queue for Brand-of-the-Week homepage image submissions.
 * Approve → image goes live on the front page immediately.
 * Reject  → submission is cleared; brand can pick a different image.
 */
export function AdminBotwImageQueue() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(null);

  const fetchQueue = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/api/admin/botw-image/queue`, { withCredentials: true });
      setItems(Array.isArray(r.data) ? r.data : []);
    } catch (e) {
      toast.error('Could not load Brand-of-the-Week image queue');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchQueue(); }, [fetchQueue]);

  const decide = async (id, approve) => {
    setProcessing(id);
    try {
      await axios.post(`${API}/api/admin/botw-image/${id}`, { approve }, { withCredentials: true });
      toast.success(approve ? 'Approved — live on the homepage now.' : 'Rejected — brand can pick another image.');
      setItems((prev) => prev.filter((b) => b.id !== id));
    } catch (e) {
      const detail = e.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Could not update decision');
    } finally {
      setProcessing(null);
    }
  };

  return (
    <div className="mb-12" data-testid="admin-botw-image-section">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold uppercase text-white flex items-center gap-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
          <Crown className="w-5 h-5 text-[#39FF14]" />
          Brand-of-the-Week homepage image
        </h2>
        <span className="text-xs uppercase tracking-wider px-3 py-1 bg-[#39FF14]/10 text-[#39FF14] border border-[#39FF14]/30"
              data-testid="botw-queue-count">
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
          <Crown className="w-8 h-8 text-[#39FF14]/30 mx-auto mb-3" />
          <p className="text-[#9CA3AF] text-sm">No pending Brand-of-the-Week homepage images.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((b) => (
            <div key={b.id} className="border border-yellow-500/30 bg-yellow-500/5 p-5" data-testid={`botw-item-${b.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex-1">
                  <p className="text-xs uppercase tracking-wider text-yellow-300 font-bold mb-1">Pending homepage image</p>
                  <p className="text-white font-bold">{b.brand_name}</p>
                  <p className="text-xs text-[#9CA3AF]">Submitted {b.botw_image_submitted_at ? new Date(b.botw_image_submitted_at).toLocaleString() : '—'}</p>
                </div>
                <div className="w-40 aspect-square overflow-hidden border border-white/10 bg-[#0F0F0F]">
                  {b.botw_featured_image_pending ? (
                    <img
                      src={b.botw_featured_image_pending.startsWith('/api/')
                        ? `${API}${b.botw_featured_image_pending}`
                        : b.botw_featured_image_pending}
                      alt={`${b.brand_name} homepage image`}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[#9CA3AF] text-xs">No image</div>
                  )}
                </div>
              </div>

              <div className="flex gap-2 mt-4">
                <Button className="btn-primary text-sm py-2" onClick={() => decide(b.id, true)}
                        disabled={processing === b.id}
                        data-testid={`botw-approve-${b.id}`}>
                  {processing === b.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-1" />}
                  Approve — go live
                </Button>
                <Button className="btn-secondary text-sm py-2 text-red-400 hover:text-red-300"
                        onClick={() => decide(b.id, false)}
                        disabled={processing === b.id}
                        data-testid={`botw-reject-${b.id}`}>
                  <XCircle className="w-4 h-4 mr-1" />
                  Reject
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
