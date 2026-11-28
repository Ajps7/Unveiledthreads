import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { ArrowLeft, Loader2, Plus, Trash2, Pause, Play, Tag, Shuffle } from 'lucide-react';
import Header from '../components/Header';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';

const API = process.env.REACT_APP_BACKEND_URL;

const statusStyles = {
  live: 'bg-[#39FF14]/15 text-[#39FF14] border-[#39FF14]/40',
  scheduled: 'bg-sky-500/15 text-sky-300 border-sky-500/40',
  paused: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40',
  ended: 'bg-white/5 text-[#9CA3AF] border-white/20',
};

function toLocalInputDate(d) {
  // ISO → value for <input type="datetime-local">, UTC
  if (!d) return '';
  try {
    const dt = new Date(d);
    const pad = (n) => String(n).padStart(2, '0');
    return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
  } catch { return ''; }
}

function fromLocalInputDate(v) {
  if (!v) return null;
  return new Date(v).toISOString();
}

function generateCode(prefix = 'DEAL') {
  const suffix = Math.floor(10 + Math.random() * 90);
  return `${prefix}${suffix}`;
}

export default function BrandPromotions() {
  const [list, setList] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const emptyForm = {
    code: '',
    percent_off: 25,
    threshold_pounds: 100,
    starts_at: toLocalInputDate(new Date()),
    ends_at: toLocalInputDate(new Date(Date.now() + 14 * 24 * 3600 * 1000)),
    usage_limit: '',
    per_customer_limit: 1,
    active: true,
  };
  const [form, setForm] = useState(emptyForm);
  const [codeAvailable, setCodeAvailable] = useState(null);
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/discounts/mine`, { withCredentials: true });
      setList(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not load promotions.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Debounced availability check as the brand types a code
  useEffect(() => {
    const normalised = (form.code || '').trim().toUpperCase();
    if (!normalised || normalised.length < 3) { setCodeAvailable(null); return; }
    const t = setTimeout(async () => {
      try {
        const r = await axios.get(`${API}/api/discounts/code-available?code=${encodeURIComponent(normalised)}`, { withCredentials: true });
        setCodeAvailable(r.data);
      } catch { setCodeAvailable(null); }
    }, 350);
    return () => clearTimeout(t);
  }, [form.code]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        code: form.code.trim().toUpperCase(),
        percent_off: Number(form.percent_off),
        threshold_amount: Math.round(Number(form.threshold_pounds) * 100),
        starts_at: fromLocalInputDate(form.starts_at),
        ends_at: fromLocalInputDate(form.ends_at),
        usage_limit: form.usage_limit ? Number(form.usage_limit) : null,
        per_customer_limit: Number(form.per_customer_limit),
        active: !!form.active,
      };
      await axios.post(`${API}/api/discounts`, payload, { withCredentials: true });
      toast.success(`Code ${payload.code} created.`);
      setForm(emptyForm);
      setShowForm(false);
      refresh();
    } catch (err) {
      const d = err.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'Could not create code.');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (d) => {
    try {
      await axios.put(`${API}/api/discounts/${d.id}`, { active: !d.active }, { withCredentials: true });
      toast.success(d.active ? 'Paused.' : 'Resumed.');
      refresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to update.'); }
  };

  const handleEndNow = async (d) => {
    if (!window.confirm('End this code now? It will stop applying immediately.')) return;
    try {
      await axios.put(`${API}/api/discounts/${d.id}`, { ends_at: new Date().toISOString() }, { withCredentials: true });
      toast.success('Ended.');
      refresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to end.'); }
  };

  const handleDelete = async (d) => {
    if (!window.confirm(`Delete code ${d.code}? It will no longer be usable.`)) return;
    try {
      await axios.delete(`${API}/api/discounts/${d.id}`, { withCredentials: true });
      toast.success('Deleted.');
      refresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to delete.'); }
  };

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-5xl mx-auto px-6 md:px-12 py-10" data-testid="brand-promotions-page">
        <Link to="/brand/dashboard" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-6 transition-colors text-sm">
          <ArrowLeft className="w-4 h-4" /> Back to dashboard
        </Link>

        <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-black tracking-tighter uppercase text-white" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Promotions
            </h1>
            <p className="text-sm text-[#9CA3AF] mt-1">Code-gated "spend X, get Y% off" promos on your own products.</p>
          </div>
          <Button className="btn-primary" onClick={() => setShowForm((v) => !v)} data-testid="new-promotion-button">
            <Plus className="w-4 h-4 mr-2" /> {showForm ? 'Cancel' : 'New promotion'}
          </Button>
        </div>

        {showForm && (
          <form onSubmit={handleCreate} className="border border-white/10 bg-[#0A0A0A] p-6 mb-8 space-y-4" data-testid="promotion-form">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1.5">Code *</label>
                <div className="flex gap-2">
                  <Input
                    required
                    value={form.code}
                    onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '') })}
                    placeholder="FLAIRE25"
                    maxLength={32}
                    className="input-brutalist uppercase"
                    data-testid="promo-code-input"
                  />
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, code: generateCode() })}
                    className="px-3 py-2 border border-white/20 text-[#C0C0C0] hover:text-[#39FF14] hover:border-[#39FF14] transition-colors"
                    aria-label="Generate code"
                    data-testid="promo-generate-code"
                  >
                    <Shuffle className="w-4 h-4" />
                  </button>
                </div>
                {codeAvailable !== null && (
                  <p className={`text-xs mt-1 ${codeAvailable.available ? 'text-[#39FF14]' : 'text-red-400'}`} data-testid="promo-code-availability">
                    {codeAvailable.available ? '✓ Available' : (codeAvailable.reason || 'Already taken.')}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1.5">% off *</label>
                <Input type="number" required min={1} max={90} value={form.percent_off} onChange={(e) => setForm({ ...form, percent_off: e.target.value })} className="input-brutalist" data-testid="promo-percent-input" />
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1.5">Spend threshold (£) *</label>
                <Input type="number" required min={0} step="0.01" value={form.threshold_pounds} onChange={(e) => setForm({ ...form, threshold_pounds: e.target.value })} className="input-brutalist" data-testid="promo-threshold-input" />
                <p className="text-[10px] text-[#6B7280] mt-1">Minimum spend on YOUR products before the code applies.</p>
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1.5">Total usage cap (optional)</label>
                <Input type="number" min={1} value={form.usage_limit} onChange={(e) => setForm({ ...form, usage_limit: e.target.value })} placeholder="Unlimited" className="input-brutalist" data-testid="promo-usage-limit-input" />
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1.5">Start *</label>
                <Input type="datetime-local" required value={form.starts_at} onChange={(e) => setForm({ ...form, starts_at: e.target.value })} className="input-brutalist" data-testid="promo-starts-input" />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1.5">End *</label>
                <Input type="datetime-local" required value={form.ends_at} onChange={(e) => setForm({ ...form, ends_at: e.target.value })} className="input-brutalist" data-testid="promo-ends-input" />
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-1.5">Per-customer limit *</label>
                <Input type="number" required min={1} max={10} value={form.per_customer_limit} onChange={(e) => setForm({ ...form, per_customer_limit: e.target.value })} className="input-brutalist" data-testid="promo-per-customer-input" />
                <p className="text-[10px] text-[#6B7280] mt-1">Keep this at 1 for a public code so one buyer can't redeem it over and over.</p>
              </div>
              <label className="flex items-center gap-3 self-end mb-2">
                <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} className="w-4 h-4 accent-[#39FF14]" data-testid="promo-active-input" />
                <span className="text-sm text-white">Active on save</span>
              </label>
            </div>
            <Button type="submit" className="btn-primary w-full md:w-auto" disabled={saving || (codeAvailable && !codeAvailable.available)} data-testid="promo-save-button">
              {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Saving…</> : 'Save promotion'}
            </Button>
          </form>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 text-[#39FF14] animate-spin" /></div>
        ) : !list || list.length === 0 ? (
          <div className="border border-white/10 bg-[#0A0A0A] p-10 text-center" data-testid="promotions-empty-state">
            <Tag className="w-10 h-10 text-[#39FF14] mx-auto mb-3" />
            <p className="text-white font-bold mb-1">No promotions yet.</p>
            <p className="text-sm text-[#9CA3AF]">Create a code to run a short-term "spend £X, get Y% off" drop.</p>
          </div>
        ) : (
          <div className="space-y-3" data-testid="promotions-list">
            {list.map((d) => (
              <div key={d.id} className="border border-white/10 bg-[#0A0A0A] p-4 flex flex-wrap items-center gap-4" data-testid={`promotion-row-${d.code}`}>
                <div className="flex-1 min-w-[200px]">
                  <div className="flex items-center gap-3 flex-wrap">
                    <p className="text-white font-bold font-mono tracking-wider" data-testid={`promotion-code-${d.code}`}>{d.code}</p>
                    <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 border ${statusStyles[d.status]}`} data-testid={`promotion-status-${d.code}`}>{d.status}</span>
                  </div>
                  <p className="text-xs text-[#9CA3AF] mt-1">
                    {d.percent_off}% off when buyers spend £{d.threshold_pounds.toFixed(2)}+ on your products.
                  </p>
                  <p className="text-[11px] text-[#6B7280] mt-0.5">
                    {new Date(d.starts_at).toLocaleDateString()} → {new Date(d.ends_at).toLocaleDateString()} · Redeemed {d.used_count}{d.usage_limit ? `/${d.usage_limit}` : ' (unlimited)'} · {d.per_customer_limit}/buyer
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => handleToggleActive(d)} className="px-2 py-1 text-xs border border-white/20 text-[#C0C0C0] hover:text-white hover:border-white transition-colors flex items-center gap-1" data-testid={`promotion-toggle-${d.code}`}>
                    {d.active ? <><Pause className="w-3 h-3" /> Pause</> : <><Play className="w-3 h-3" /> Resume</>}
                  </button>
                  {d.status !== 'ended' && (
                    <button onClick={() => handleEndNow(d)} className="px-2 py-1 text-xs border border-yellow-500/40 text-yellow-300 hover:bg-yellow-500/10 transition-colors" data-testid={`promotion-end-${d.code}`}>End now</button>
                  )}
                  <button onClick={() => handleDelete(d)} className="px-2 py-1 text-xs border border-red-500/40 text-red-400 hover:bg-red-500/10 transition-colors flex items-center gap-1" data-testid={`promotion-delete-${d.code}`}>
                    <Trash2 className="w-3 h-3" /> Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
