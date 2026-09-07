import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import { Button } from '../components/ui/button';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  ArrowLeft, Loader2, Network, RefreshCw, TriangleAlert,
} from 'lucide-react';
import { MemoPanel } from '../components/growth/MemoPanel';
import { StageTrack } from '../components/growth/StageTrack';
import { LoopScorecard } from '../components/growth/LoopScorecard';
import { PlaybookBoard } from '../components/growth/PlaybookBoard';
import { NetworkPanel } from '../components/growth/NetworkPanel';
import { CohortMatrix } from '../components/growth/CohortMatrix';
import { FlywheelSimulator } from '../components/growth/FlywheelSimulator';
import { fmtMoney, fmtNum, fmtPct } from '../components/growth/shared';

const API = process.env.REACT_APP_BACKEND_URL;

const HEADLINE_METRICS = [
  { key: 'gmv', label: 'GMV', format: (v) => fmtMoney(v) },
  { key: 'orders', label: 'Orders', format: (v) => fmtNum(v, 0) },
  { key: 'active_buyers', label: 'Active buyers', format: (v) => fmtNum(v, 0) },
  { key: 'selling_brands', label: 'Brands selling', format: (v) => fmtNum(v, 0) },
  { key: 'sell_through_rate', label: 'Sell-through', format: (v) => fmtPct(v) },
  { key: 'multi_brand_buyer_rate', label: 'Multi-brand buyers', format: (v) => fmtPct(v) },
];

// Data-coverage warnings sit above the numbers, not in a footnote. A gap in
// what can be measured changes how much weight the rest of the page can bear.
function CoverageBanner({ coverage }) {
  const gaps = (coverage?.gaps || []).filter((g) => g.severity === 'high');
  if (gaps.length === 0) return null;
  return (
    <div className="mb-6 border border-amber-400/40 bg-amber-400/5 p-4" data-testid="coverage-banner">
      <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-400">
        <TriangleAlert className="h-4 w-4" /> What this tool cannot see
      </p>
      <ul className="mt-2 space-y-2">
        {gaps.map((gap) => (
          <li key={gap.key} className="text-xs leading-relaxed text-[#D1D5DB]">
            <span className="text-white">{gap.what}</span> {gap.consequence}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function GrowthCommandCenter() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [brief, setBrief] = useState(null);
  const [days, setDays] = useState('90');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const fetchBrief = useCallback(async (windowDays, refresh = false) => {
    if (refresh) setRefreshing(true);
    setError(null);
    try {
      const res = await axios.get(
        `${API}/api/growth/brief?days=${windowDays}${refresh ? '&refresh=true' : ''}`,
        { withCredentials: true },
      );
      setBrief(res.data);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Could not load the growth brief.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { navigate('/login'); return; }
    if (user.role !== 'admin') { navigate('/'); return; }
    document.title = 'Growth · Unveiled Threads';
    fetchBrief(days);
  }, [user, authLoading, navigate, days, fetchBrief]);

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex h-[60vh] items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-[#39FF14]" />
        </div>
      </div>
    );
  }

  const metrics = brief?.metrics || {};
  const diagnosis = brief?.diagnosis || {};

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      <div className="mx-auto max-w-7xl px-6 py-8 md:px-12">
        <Link to="/admin" className="mb-8 inline-flex items-center gap-2 text-[#9CA3AF] transition-colors hover:text-white">
          <ArrowLeft className="h-4 w-4" /> Back to admin
        </Link>

        <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div className="flex items-start gap-3">
            <Network className="mt-1 h-7 w-7 shrink-0 text-[#39FF14]" />
            <div>
              <h1
                className="text-2xl font-black uppercase tracking-tighter text-white md:text-3xl"
                style={{ fontFamily: 'Clash Display, sans-serif' }}
                data-testid="growth-title"
              >
                Network Effects Command Center
              </h1>
              <p className="mt-1 max-w-2xl text-xs leading-relaxed text-[#9CA3AF]">
                Marketplace growth diagnosis: which loop is broken, what to do about it, what to stop,
                and what the flywheel does if you pull each lever.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Select value={days} onValueChange={setDays}>
              <SelectTrigger className="w-[150px] rounded-none border-white/20 bg-transparent text-white" data-testid="growth-window-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="rounded-none border-white/10 bg-[#0F0F0F]">
                {[['30', 'Last 30 days'], ['90', 'Last 90 days'], ['180', 'Last 6 months'], ['365', 'Last 12 months']].map(([v, l]) => (
                  <SelectItem key={v} value={v} className="rounded-none text-white hover:bg-white/10">{l}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              type="button"
              onClick={() => fetchBrief(days, true)}
              disabled={refreshing}
              className="h-10 rounded-none border border-white/20 bg-transparent px-3 text-white hover:bg-white/10"
              data-testid="growth-refresh"
              aria-label="Recalculate from live data"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {error && (
          <div className="mb-6 border border-red-400/40 bg-red-400/10 p-4 text-sm text-red-400" data-testid="growth-error">
            {error}
          </div>
        )}

        {brief && (
          <>
            <CoverageBanner coverage={brief.coverage} />

            <div className="mb-8 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
              {HEADLINE_METRICS.map((m) => (
                <div key={m.key} className="border border-white/10 bg-[#0A0A0A] p-4" data-testid={`headline-${m.key}`}>
                  <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF]">{m.label}</p>
                  <p className="mt-2 text-xl font-bold text-white">{m.format(metrics[m.key])}</p>
                </div>
              ))}
            </div>

            <Tabs defaultValue="diagnosis" className="w-full">
              <TabsList className="mb-6 h-auto w-full flex-wrap justify-start gap-1 rounded-none border border-white/10 bg-[#0A0A0A] p-1">
                {[
                  ['diagnosis', 'Diagnosis'],
                  ['playbook', 'Playbook'],
                  ['network', 'Network'],
                  ['retention', 'Retention'],
                  ['simulator', 'Simulator'],
                ].map(([value, label]) => (
                  <TabsTrigger
                    key={value}
                    value={value}
                    className="rounded-none px-4 py-2 text-xs uppercase tracking-wider text-[#9CA3AF] data-[state=active]:bg-[#39FF14] data-[state=active]:text-black"
                    data-testid={`growth-tab-${value}`}
                  >
                    {label}
                  </TabsTrigger>
                ))}
              </TabsList>

              <TabsContent value="diagnosis" className="mt-0 space-y-6">
                <MemoPanel memo={brief.memo} confidence={diagnosis.confidence} />
                <StageTrack stage={diagnosis.stage} />
                <LoopScorecard
                  loops={diagnosis.loops}
                  overallScore={diagnosis.overall_score}
                  grade={diagnosis.grade}
                  weakest={diagnosis.weakest_loop}
                />
              </TabsContent>

              <TabsContent value="playbook" className="mt-0">
                <PlaybookBoard playbook={brief.playbook} />
              </TabsContent>

              <TabsContent value="network" className="mt-0">
                <NetworkPanel detail={brief.detail} metrics={metrics} />
              </TabsContent>

              <TabsContent value="retention" className="mt-0">
                <CohortMatrix cohorts={brief.detail?.cohorts} repeatRate={metrics.repeat_buyer_rate} />
              </TabsContent>

              <TabsContent value="simulator" className="mt-0">
                <FlywheelSimulator defaults={brief.simulator_defaults} windowDays={Number(days)} />
              </TabsContent>
            </Tabs>

            <p className="mt-8 text-[10px] text-[#4B5563]">
              Snapshot generated {brief.generated_at}. Benchmarks are heuristics calibrated for a curated
              marketplace of independent brands — argue with them, they are all in{' '}
              <code className="text-[#6B7280]">backend/growth/benchmarks.py</code>.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
