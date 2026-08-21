import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Button } from '../ui/button';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { toast } from 'sonner';
import { Crown, Clock, Loader2, RefreshCw, Rocket, TrendingUp, Users } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Admin control panel for the weekly BotW auto-rotation.
 * Shows: current BotW · queued next pick · countdown to rotation · veto UI.
 * All writes go through /api/admin/botw/* endpoints — this component owns
 * no rotation logic itself.
 */
export function AdminBotwRotationPanel() {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [vetoBrandId, setVetoBrandId] = useState('');

  const fetchState = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/admin/botw/queue`, { withCredentials: true });
      setState(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchState(); }, [fetchState]);

  const handleVeto = async () => {
    if (!vetoBrandId) return;
    setSaving(true);
    try {
      const res = await axios.post(
        `${API}/api/admin/botw/veto`,
        { brand_id: vetoBrandId },
        { withCredentials: true },
      );
      toast.success(`Queued ${res.data.brand_name} as next BotW`);
      setVetoBrandId('');
      fetchState();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Veto failed');
    } finally {
      setSaving(false);
    }
  };

  const handleSkip = async () => {
    setSaving(true);
    try {
      const res = await axios.post(`${API}/api/admin/botw/skip`, {}, { withCredentials: true });
      toast.success(res.data.brand_name ? `Recomputed: ${res.data.brand_name}` : 'No eligible brands');
      fetchState();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Skip failed');
    } finally {
      setSaving(false);
    }
  };

  const handleRotateNow = async () => {
    if (!window.confirm('Force an immediate rotation now? This shifts the schedule to +7 days from now.')) return;
    setRotating(true);
    try {
      await axios.post(`${API}/api/admin/botw/rotate-now`, {}, { withCredentials: true });
      toast.success('Rotated');
      fetchState();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Rotate failed');
    } finally {
      setRotating(false);
    }
  };

  if (loading) {
    return (
      <div>
        <h2 className="text-xl font-bold uppercase text-white mb-6" style={{ fontFamily: 'Clash Display, sans-serif' }}>
          BotW Rotation
        </h2>
        <div className="flex items-center justify-center h-24">
          <Loader2 className="w-5 h-5 animate-spin text-[#39FF14]" />
        </div>
      </div>
    );
  }

  const nextScheduled = state?.next_scheduled_at ? new Date(state.next_scheduled_at) : null;
  const now = new Date();
  const msLeft = nextScheduled ? nextScheduled.getTime() - now.getTime() : 0;
  const daysLeft = Math.floor(msLeft / (1000 * 60 * 60 * 24));
  const hoursLeft = Math.floor((msLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const inVetoWindow = msLeft > 0 && msLeft <= 24 * 60 * 60 * 1000;

  return (
    <div data-testid="botw-rotation-panel">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-2">
        <h2 className="text-xl font-bold uppercase text-white" style={{ fontFamily: 'Clash Display, sans-serif' }}>
          BotW Rotation
        </h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={fetchState}
          className="text-[#9CA3AF] hover:text-white text-xs uppercase tracking-wider"
          data-testid="botw-refresh"
        >
          <RefreshCw className="w-3 h-3 mr-1" /> Refresh
        </Button>
      </div>

      {/* Current BotW */}
      <div className="border border-[#39FF14]/30 bg-[#39FF14]/5 p-4 mb-4">
        <div className="flex items-center gap-2 mb-2">
          <Crown className="w-4 h-4 text-[#39FF14]" />
          <p className="text-xs uppercase tracking-wider text-[#C0C0C0] font-bold">Currently featured</p>
        </div>
        {state?.current_brand ? (
          <>
            <p className="text-white font-bold" data-testid="botw-current-name">{state.current_brand.brand_name}</p>
            <p className="text-xs text-[#9CA3AF] mt-1">
              Featured since {state.current_started_at ? new Date(state.current_started_at).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '—'}
            </p>
          </>
        ) : (
          <p className="text-xs text-[#9CA3AF]">No brand is currently featured. The next rotation will fill this slot automatically.</p>
        )}
      </div>

      {/* Next-in-queue */}
      <div className="border border-white/10 bg-[#0A0A0A] p-4 mb-4">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#39FF14]" />
            <p className="text-xs uppercase tracking-wider text-[#C0C0C0] font-bold">Next rotation</p>
          </div>
          {state?.will_be_performance_pick ? (
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 bg-[#39FF14]/20 text-[#39FF14] border border-[#39FF14]/30 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> Performance week
            </span>
          ) : (
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 bg-white/5 text-[#9CA3AF] border border-white/10 flex items-center gap-1">
              <Users className="w-3 h-3" /> Fair rotation
            </span>
          )}
        </div>

        {nextScheduled && (
          <p className="text-xs text-[#9CA3AF] mb-3">
            Runs on <span className="text-white">{nextScheduled.toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
            {' · '}
            {msLeft > 0 ? (
              <span className={inVetoWindow ? 'text-yellow-300' : ''}>
                in {daysLeft > 0 ? `${daysLeft}d ` : ''}{hoursLeft}h
                {inVetoWindow && ' (inside veto window)'}
              </span>
            ) : (
              <span className="text-yellow-300">overdue — will rotate on the next tick</span>
            )}
          </p>
        )}

        {state?.next_brand ? (
          <div className="border border-[#39FF14]/40 p-3 bg-[#050505]">
            <p className="text-[10px] uppercase tracking-wider text-[#39FF14] font-bold mb-1">Queued</p>
            <p className="text-white font-bold" data-testid="botw-next-name">{state.next_brand.brand_name}</p>
            <p className="text-[10px] text-[#9CA3AF] mt-1">
              Picked {state.next_queued_at ? new Date(state.next_queued_at).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : ''}
            </p>
          </div>
        ) : (
          <p className="text-xs text-[#9CA3AF]">
            No candidate queued yet. A pick will be auto-selected 24h before the rotation, or you can force one now with <span className="text-white">Recompute</span>.
          </p>
        )}
      </div>

      {/* Admin controls: veto swap, recompute, force rotate */}
      <div className="border border-white/10 bg-[#0A0A0A] p-4 space-y-3">
        <p className="text-xs uppercase tracking-wider text-[#C0C0C0] font-bold mb-2">Admin actions</p>

        <div className="flex flex-col sm:flex-row gap-2">
          <Select value={vetoBrandId} onValueChange={setVetoBrandId}>
            <SelectTrigger className="input-brutalist flex-1" data-testid="botw-veto-select">
              <SelectValue placeholder="Swap next pick to…" />
            </SelectTrigger>
            <SelectContent className="bg-[#0F0F0F] border-white/10 max-h-72">
              {(state?.eligible_brands || []).map((b) => (
                <SelectItem key={b.id} value={b.id} className="text-white">
                  {b.brand_name}
                  {b.botw_last_featured_at && (
                    <span className="text-[10px] text-[#9CA3AF] ml-2">
                      · last {new Date(b.botw_last_featured_at).toLocaleDateString('en-GB')}
                    </span>
                  )}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={handleVeto}
            disabled={!vetoBrandId || saving}
            className="btn-primary"
            data-testid="botw-veto-button"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Swap next'}
          </Button>
        </div>

        <div className="flex flex-col sm:flex-row gap-2">
          <Button
            onClick={handleSkip}
            disabled={saving}
            variant="ghost"
            className="flex-1 text-[#9CA3AF] hover:text-white border border-white/10 rounded-none text-xs uppercase tracking-wider"
            data-testid="botw-skip-button"
          >
            <RefreshCw className="w-3 h-3 mr-2" /> Recompute pick
          </Button>
          <Button
            onClick={handleRotateNow}
            disabled={rotating}
            variant="ghost"
            className="flex-1 text-yellow-300 hover:bg-yellow-500/10 border border-yellow-500/30 rounded-none text-xs uppercase tracking-wider"
            data-testid="botw-rotate-now-button"
          >
            {rotating ? (
              <><Loader2 className="w-3 h-3 mr-2 animate-spin" /> Rotating…</>
            ) : (
              <><Rocket className="w-3 h-3 mr-2" /> Rotate now</>
            )}
          </Button>
        </div>

        <p className="text-[10px] text-[#6B7280]">
          Cycle {state?.cycle_index ?? 0} · Fair rotation for 3 weeks, performance-weighted pick every 4th week. Cooldown 8 weeks between features.
        </p>
      </div>

      {/* Recent history */}
      {state?.history?.length > 0 && (
        <details className="mt-4">
          <summary className="text-xs text-[#9CA3AF] cursor-pointer hover:text-white uppercase tracking-wider">
            Rotation history ({state.history.length})
          </summary>
          <div className="mt-2 border border-white/10 bg-[#050505] text-xs">
            {[...state.history].reverse().map((h, i) => (
              <div key={i} className="px-3 py-2 border-t border-white/5 first:border-t-0">
                <p className="text-white font-mono text-[10px] break-all">{h.brand_id}</p>
                <p className="text-[10px] text-[#9CA3AF] mt-0.5">
                  {h.started_at ? new Date(h.started_at).toLocaleDateString('en-GB') : '—'}
                  {' → '}
                  {h.ended_at ? new Date(h.ended_at).toLocaleDateString('en-GB') : '—'}
                </p>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
