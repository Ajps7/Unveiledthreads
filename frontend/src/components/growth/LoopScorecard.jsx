import { useState } from 'react';
import { ChevronDown, Info } from 'lucide-react';
import { Panel, Pill, ScoreBar, STATUS_STYLES, fmtByUnit, fmtNum } from './shared';

// Six loops, each scored against published bands. Expanding a loop shows the
// mechanism it depends on and every metric with the band it is judged by —
// a score with no visible threshold is just a number with an opinion.
export function LoopScorecard({ loops, overallScore, grade, weakest }) {
  const [open, setOpen] = useState(weakest || null);
  if (!loops?.length) return null;

  return (
    <Panel
      title="Loop scorecard"
      subtitle="A marketplace is a set of loops, not a funnel. Each is scored 0-100 against its band: 40 is the weak threshold, 80 is healthy."
      testId="growth-loops"
      right={
        <div className="text-right">
          <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">Overall</p>
          <p className="text-2xl font-black text-white" data-testid="overall-score">
            {overallScore === null || overallScore === undefined ? '—' : fmtNum(overallScore, 0)}
            <span className="ml-2 text-sm text-[#39FF14]">{grade}</span>
          </p>
        </div>
      }
    >
      <div className="space-y-2">
        {loops.map((loop) => {
          const status = STATUS_STYLES[loop.status] || STATUS_STYLES.unknown;
          const isOpen = open === loop.key;
          const isWeakest = loop.key === weakest;
          return (
            <div
              key={loop.key}
              className={`border ${isWeakest ? 'border-[#39FF14]/40' : 'border-white/10'} bg-white/[0.02]`}
              data-testid={`loop-${loop.key}`}
            >
              <button
                type="button"
                onClick={() => setOpen(isOpen ? null : loop.key)}
                className="flex w-full items-center gap-4 px-4 py-3 text-left transition-colors hover:bg-white/5"
                aria-expanded={isOpen}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-bold uppercase tracking-wide text-white">{loop.name}</span>
                    <span className={`text-[10px] uppercase tracking-wider ${status.text}`}>{status.label}</span>
                    {isWeakest && (
                      <span className="border border-[#39FF14]/40 px-1.5 text-[10px] uppercase tracking-wider text-[#39FF14]">
                        Constraint
                      </span>
                    )}
                  </div>
                  <p className="mt-1 truncate text-xs text-[#9CA3AF]">{loop.question}</p>
                </div>
                <div className="w-32 shrink-0">
                  <ScoreBar score={loop.score} testId={`loop-${loop.key}-bar`} />
                </div>
                <span className="w-10 shrink-0 text-right text-sm font-bold text-white">
                  {loop.score === null || loop.score === undefined ? '—' : fmtNum(loop.score, 0)}
                </span>
                <ChevronDown className={`h-4 w-4 shrink-0 text-[#6B7280] transition-transform ${isOpen ? 'rotate-180' : ''}`} />
              </button>

              {isOpen && (
                <div className="border-t border-white/10 px-4 py-4">
                  <p className="mb-4 flex gap-2 text-xs leading-relaxed text-[#9CA3AF]">
                    <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#39FF14]" />
                    <span>{loop.mechanism}</span>
                  </p>
                  {loop.measured_weight < 1 && (
                    <p className="mb-3 text-[11px] uppercase tracking-wider text-amber-400/80">
                      Only {Math.round(loop.measured_weight * 100)}% of this loop is measurable right now
                    </p>
                  )}
                  <div className="space-y-3">
                    {loop.metrics.map((m) => (
                      <div key={m.key} data-testid={`metric-${m.key}`}>
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <span className="text-xs text-[#D1D5DB]">{m.label}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-white">{fmtByUnit(m.value, m.unit)}</span>
                            <Pill tone={m.rating}>{(m.rating || 'unknown').replace('_', ' ')}</Pill>
                          </div>
                        </div>
                        <p className="mt-1 text-[10px] uppercase tracking-wider text-[#4B5563]">
                          {m.higher_is_better ? 'weak below' : 'weak above'} {fmtByUnit(m.weak, m.unit)}
                          {' · '}
                          {m.higher_is_better ? 'healthy at' : 'healthy at or below'} {fmtByUnit(m.healthy, m.unit)}
                        </p>
                        {m.why && <p className="mt-1 text-[11px] leading-relaxed text-[#6B7280]">{m.why}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
