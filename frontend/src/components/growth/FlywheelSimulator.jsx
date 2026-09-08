import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { Loader2, RotateCcw, Zap } from 'lucide-react';
import { Button } from '../ui/button';
import { Panel, fmtMoney, fmtNum, fmtPct } from './shared';

const API = process.env.REACT_APP_BACKEND_URL;

// Only the levers an operator can actually pull. Each carries the unit and a
// one-line note on what moving it means in the real business, so the model
// stays a thinking tool rather than a black box.
const LEVERS = [
  {
    key: 'buyer_retention', label: 'Monthly buyer retention', min: 0, max: 0.95, step: 0.01,
    format: (v) => fmtPct(v, 0),
    note: 'Share of active buyers who buy again next month. The multiplier on every acquisition pound.',
  },
  {
    key: 'k_factor', label: 'K-factor (referral)', min: 0, max: 1.5, step: 0.05,
    format: (v) => fmtNum(v, 2),
    note: 'New buyers generated per buyer acquired last month. Compounds on the prior month, so it builds slowly then bites.',
  },
  {
    key: 'orders_per_buyer_month', label: 'Orders per buyer / month', min: 0, max: 3, step: 0.05,
    format: (v) => fmtNum(v, 2),
    note: 'Purchase frequency before the catalogue-depth adjustment is applied.',
  },
  {
    key: 'aov', label: 'Average order value', min: 10, max: 300, step: 5,
    format: (v) => fmtMoney(v),
    note: 'Raising this lowers the effective take rate — the Buyer Protection fee is capped at £6.',
  },
  {
    key: 'brand_adds_per_month', label: 'New brands / month', min: 0, max: 40, step: 1,
    format: (v) => fmtNum(v, 0),
    note: 'Before the supply-response adjustment: brands join faster when existing brands visibly earn.',
  },
  {
    key: 'listings_per_brand', label: 'Listings per brand', min: 1, max: 200, step: 1,
    format: (v) => fmtNum(v, 0),
    note: 'Drives catalogue depth, which throttles or unlocks conversion.',
  },
  {
    key: 'baseline_organic_new_buyers', label: 'Organic new buyers / month', min: 0, max: 500, step: 5,
    format: (v) => fmtNum(v, 0),
    note: 'At today\'s catalogue breadth. Scales sub-linearly as the catalogue widens.',
  },
  {
    key: 'monthly_paid_spend', label: 'Monthly paid spend', min: 0, max: 50000, step: 250,
    format: (v) => fmtMoney(v),
    note: 'Buys new buyers at the CAC below. Worth nothing if the funnel does not convert.',
  },
  {
    key: 'cac', label: 'Paid CAC', min: 1, max: 200, step: 1,
    format: (v) => fmtMoney(v),
    note: 'Cost per acquired buyer. Compare against LTV in the summary.',
  },
];

function Slider({ lever, value, onChange }) {
  return (
    <div data-testid={`lever-${lever.key}`}>
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={`lever-${lever.key}`} className="text-xs text-[#D1D5DB]">{lever.label}</label>
        <span className="text-xs font-bold text-[#39FF14]">{lever.format(value)}</span>
      </div>
      <input
        id={`lever-${lever.key}`}
        type="range"
        min={lever.min}
        max={lever.max}
        step={lever.step}
        value={value}
        onChange={(e) => onChange(lever.key, Number(e.target.value))}
        className="mt-2 h-1 w-full cursor-pointer appearance-none bg-white/15 accent-[#39FF14]"
      />
      <p className="mt-1 text-[10px] leading-relaxed text-[#6B7280]">{lever.note}</p>
    </div>
  );
}

function SummaryTile({ label, value, sub, tone = 'text-white' }) {
  return (
    <div className="border border-white/10 p-3">
      <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">{label}</p>
      <p className={`mt-1 text-lg font-bold ${tone}`}>{value}</p>
      {sub && <p className="mt-1 text-[10px] text-[#6B7280]">{sub}</p>}
    </div>
  );
}

export function FlywheelSimulator({ defaults, windowDays }) {
  const [levers, setLevers] = useState(null);
  const [months, setMonths] = useState(12);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Seed the sliders from the measured baseline, so moving one always means
  // "change this from what it actually is" rather than from a made-up number.
  const seeded = useMemo(() => {
    if (!defaults) return null;
    const out = {};
    LEVERS.forEach((l) => { out[l.key] = defaults[l.key] ?? 0; });
    return out;
  }, [defaults]);

  useEffect(() => { if (seeded && !levers) setLevers(seeded); }, [seeded, levers]);

  // Run the baseline projection once, as soon as the sliders have been seeded
  // from real data. `hasRun` is what keeps this to a single call — the effect
  // still declares every dependency it reads.
  const [hasRun, setHasRun] = useState(false);

  const run = useCallback(async (payloadLevers, payloadMonths) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(
        `${API}/api/growth/simulate`,
        { ...payloadLevers, months: payloadMonths, window_days: windowDays, compare_to_baseline: true },
        { withCredentials: true },
      );
      setResult(res.data);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Could not run the simulation.');
    } finally {
      setLoading(false);
    }
  }, [windowDays]);

  useEffect(() => {
    if (levers && !hasRun) {
      setHasRun(true);
      run(levers, months);
    }
  }, [levers, hasRun, months, run]);

  if (!levers) return null;

  const onChange = (key, value) => setLevers((prev) => ({ ...prev, [key]: value }));
  const reset = () => { setLevers(seeded); run(seeded, months); };

  const chartData = (result?.scenario?.series || []).map((row, i) => ({
    month: `M${row.month}`,
    scenario: row.gmv,
    baseline: result?.base?.series?.[i]?.gmv ?? null,
  }));

  const s = result?.scenario?.summary;
  const b = result?.base?.summary;
  const changed = LEVERS.filter((l) => seeded && Math.abs(levers[l.key] - seeded[l.key]) > 1e-9);

  return (
    <Panel
      title="Flywheel simulator"
      subtitle="A model with the loops closed: catalogue depth throttles conversion, poor GMV per brand churns supply, and referrals compound on last month's acquisition. Read the shape, not the decimals."
      icon={Zap}
      testId="growth-simulator"
      right={
        <Button
          type="button"
          onClick={reset}
          className="h-8 rounded-none border border-white/20 bg-transparent px-3 text-xs uppercase tracking-wider text-white hover:bg-white/10"
          data-testid="simulator-reset"
        >
          <RotateCcw className="mr-1 h-3 w-3" /> Reset to actuals
        </Button>
      }
    >
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <div className="space-y-4">
          <div>
            <div className="flex items-baseline justify-between gap-2">
              <label htmlFor="lever-months" className="text-xs text-[#D1D5DB]">Horizon</label>
              <span className="text-xs font-bold text-[#39FF14]">{months} months</span>
            </div>
            <input
              id="lever-months"
              type="range"
              min={3}
              max={36}
              step={1}
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              className="mt-2 h-1 w-full cursor-pointer appearance-none bg-white/15 accent-[#39FF14]"
            />
          </div>

          {LEVERS.map((lever) => (
            <Slider key={lever.key} lever={lever} value={levers[lever.key]} onChange={onChange} />
          ))}

          <Button
            type="button"
            onClick={() => run(levers, months)}
            disabled={loading}
            className="w-full rounded-none bg-[#39FF14] font-bold uppercase tracking-wider text-black hover:bg-[#39FF14]/90"
            data-testid="simulator-run"
          >
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Run projection
          </Button>
          {changed.length > 0 && (
            <p className="text-[10px] leading-relaxed text-[#6B7280]" data-testid="simulator-changed">
              Changed vs actuals: {changed.map((l) => l.label).join(', ')}
            </p>
          )}
        </div>

        <div>
          {error && <p className="mb-4 border border-red-400/40 bg-red-400/10 p-3 text-xs text-red-400">{error}</p>}

          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer>
              <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis dataKey="month" stroke="#6B7280" tick={{ fontSize: 11 }} tickLine={false} />
                <YAxis
                  stroke="#6B7280"
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  tickFormatter={(v) => (v >= 1000 ? `£${Math.round(v / 1000)}k` : `£${v}`)}
                />
                <Tooltip
                  contentStyle={{ background: '#0F0F0F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 0, fontSize: 12 }}
                  formatter={(v) => fmtMoney(v)}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="baseline" name="Do nothing" stroke="#6B7280" strokeWidth={1.5} dot={false} strokeDasharray="4 3" />
                <Line type="monotone" dataKey="scenario" name="Scenario" stroke="#39FF14" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {s && (
            <>
              <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
                <SummaryTile
                  label={`Monthly GMV at M${months}`}
                  value={fmtMoney(s.ending_gmv)}
                  sub={b ? `Do nothing: ${fmtMoney(b.ending_gmv)}` : null}
                />
                <SummaryTile label="Brands" value={fmtNum(s.ending_brands, 0)} sub={b ? `Do nothing: ${fmtNum(b.ending_brands, 0)}` : null} />
                <SummaryTile
                  label="LTV : CAC"
                  value={s.ltv_cac === null ? '—' : `${fmtNum(s.ltv_cac, 2)}x`}
                  sub={s.payback_months === null ? 'No payback at these economics' : `Payback ${fmtNum(s.payback_months, 1)} months`}
                  tone={s.ltv_cac !== null && s.ltv_cac >= 3 ? 'text-[#39FF14]' : 'text-amber-400'}
                />
                <SummaryTile
                  label="Organic share"
                  value={fmtPct(s.organic_share_of_new_buyers, 0)}
                  sub={s.escape_velocity ? 'Escape velocity' : 'Growth still bought'}
                  tone={s.escape_velocity ? 'text-[#39FF14]' : 'text-white'}
                />
              </div>

              <div className="mt-4 border-l-2 border-[#39FF14] pl-4">
                <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">Binding constraint at this setting</p>
                <p className="mt-1 text-sm font-bold uppercase tracking-wide text-white" data-testid="simulator-constraint">
                  {s.binding_constraint}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-[#9CA3AF]">{s.binding_constraint_note}</p>
              </div>

              <p className="mt-4 text-[10px] leading-relaxed text-[#6B7280]">
                Cumulative contribution over {months} months: {fmtMoney(s.cumulative_contribution)} (scenario)
                {b ? ` vs ${fmtMoney(b.cumulative_contribution)} doing nothing` : ''}. Revenue is modelled from the
                live Buyer Protection fee at the chosen AOV, not a flat take rate.
              </p>
            </>
          )}
        </div>
      </div>
    </Panel>
  );
}
