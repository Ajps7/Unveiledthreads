// Shared presentation helpers for the Network Effects Command Center.
//
// Formatting rule that runs through the whole tool: `null` means "we could
// not measure this" and renders as an em dash, never as 0. A dashboard that
// reports a confident 0% for a week with no traffic is worse than one that
// admits it does not know.

export const ACCENT = '#39FF14';

export const RATING_STYLES = {
  healthy: { text: 'text-[#39FF14]', border: 'border-[#39FF14]/40', bg: 'bg-[#39FF14]/10', label: 'Healthy' },
  developing: { text: 'text-amber-400', border: 'border-amber-400/40', bg: 'bg-amber-400/10', label: 'Developing' },
  weak: { text: 'text-red-400', border: 'border-red-400/40', bg: 'bg-red-400/10', label: 'Weak' },
  unknown: { text: 'text-[#6B7280]', border: 'border-white/10', bg: 'bg-white/5', label: 'No data' },
};

export const STATUS_STYLES = {
  compounding: { text: 'text-[#39FF14]', label: 'Compounding' },
  working: { text: 'text-[#39FF14]/70', label: 'Working' },
  leaking: { text: 'text-amber-400', label: 'Leaking' },
  broken: { text: 'text-red-400', label: 'Broken' },
  unknown: { text: 'text-[#6B7280]', label: 'Not measurable' },
};

export const SEVERITY_STYLES = {
  critical: { text: 'text-red-400', border: 'border-red-400/50', label: 'Critical' },
  high: { text: 'text-orange-400', border: 'border-orange-400/50', label: 'High' },
  medium: { text: 'text-amber-400', border: 'border-amber-400/40', label: 'Medium' },
  low: { text: 'text-[#9CA3AF]', border: 'border-white/10', label: 'Low' },
};

export const DASH = '—';

export function fmtPct(value, places = 1) {
  if (value === null || value === undefined) return DASH;
  return `${(value * 100).toFixed(places)}%`;
}

export function fmtNum(value, places = 1) {
  if (value === null || value === undefined) return DASH;
  return Number(value).toLocaleString('en-GB', {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  });
}

export function fmtMoney(value, places = 0) {
  if (value === null || value === undefined) return DASH;
  return `£${Number(value).toLocaleString('en-GB', {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  })}`;
}

// Render a metric using the unit its band declares, so percentages, ratios,
// indices and day counts never get formatted as each other.
export function fmtByUnit(value, unit) {
  if (value === null || value === undefined) return DASH;
  switch (unit) {
    case 'pct': return fmtPct(value);
    case 'days': return `${fmtNum(value, 0)}d`;
    case 'index': return fmtNum(value, 2);
    default: return fmtNum(value, 2);
  }
}

export function Panel({ title, subtitle, icon: Icon, right, children, testId }) {
  return (
    <section className="border border-white/10 bg-[#0A0A0A]" data-testid={testId}>
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-white/10 px-5 py-4">
        <div className="flex items-start gap-3">
          {Icon && <Icon className="mt-0.5 h-5 w-5 shrink-0 text-[#39FF14]" />}
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-white">{title}</h2>
            {subtitle && <p className="mt-1 max-w-2xl text-xs leading-relaxed text-[#9CA3AF]">{subtitle}</p>}
          </div>
        </div>
        {right}
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
}

// A score bar with the weak and healthy thresholds marked on it, so a number
// is always shown against the bar it is being judged by.
export function ScoreBar({ score, testId }) {
  const pct = score === null || score === undefined ? 0 : Math.max(0, Math.min(100, score));
  const colour = score === null || score === undefined ? '#374151'
    : score < 30 ? '#f87171'
      : score < 55 ? '#fbbf24'
        : score < 80 ? '#a3e635' : ACCENT;
  return (
    <div className="relative h-2 w-full bg-white/10" data-testid={testId}>
      <div className="h-full transition-all" style={{ width: `${pct}%`, backgroundColor: colour }} />
      {/* 40 = the weak threshold, 80 = healthy */}
      <span className="absolute top-0 h-full w-px bg-white/30" style={{ left: '40%' }} />
      <span className="absolute top-0 h-full w-px bg-white/30" style={{ left: '80%' }} />
    </div>
  );
}

export function Pill({ tone = 'unknown', children, testId }) {
  const style = RATING_STYLES[tone] || RATING_STYLES.unknown;
  return (
    <span
      className={`inline-flex items-center border px-2 py-0.5 text-[10px] uppercase tracking-wider ${style.border} ${style.bg} ${style.text}`}
      data-testid={testId}
    >
      {children}
    </span>
  );
}

export function EmptyNote({ children }) {
  return <p className="text-sm text-[#6B7280]">{children}</p>;
}
