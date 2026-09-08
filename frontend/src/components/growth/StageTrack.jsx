import { Check, Circle, Lock } from 'lucide-react';
import { Panel, fmtNum } from './shared';

// The sequencing model, rendered as a track. Its job is to make it obvious
// which stage you are on and to give explicit permission to ignore the ones
// above it — that permission is most of the value.
export function StageTrack({ stage }) {
  if (!stage) return null;
  const currentIndex = stage.stages.findIndex((s) => s.key === stage.current);

  return (
    <Panel
      title="Where you are"
      subtitle="Stages clear in order. Work on the first one that has not cleared, and ignore everything above it — most marketplace growth failure is a late-stage tactic applied to an early-stage problem."
      testId="growth-stage-track"
    >
      <div className="grid gap-3 md:grid-cols-5">
        {stage.stages.map((s, i) => {
          const isCurrent = s.key === stage.current;
          const isDone = s.passed && i < currentIndex;
          const isLocked = i > currentIndex;
          const Icon = isDone ? Check : isLocked ? Lock : Circle;
          return (
            <div
              key={s.key}
              className={`border p-3 ${isCurrent ? 'border-[#39FF14] bg-[#39FF14]/5' : 'border-white/10 bg-white/[0.02]'}`}
              data-testid={`stage-${s.key}`}
            >
              <div className="flex items-center gap-2">
                <Icon className={`h-3.5 w-3.5 ${isDone ? 'text-[#39FF14]' : isCurrent ? 'text-[#39FF14]' : 'text-[#4B5563]'}`} />
                <span className={`text-xs font-bold uppercase tracking-wider ${isCurrent ? 'text-white' : isDone ? 'text-[#39FF14]' : 'text-[#6B7280]'}`}>
                  {s.name}
                </span>
              </div>
              <div className="mt-2 space-y-1">
                {s.checks.map((c) => (
                  <div key={c.metric} className="flex items-baseline justify-between gap-2 text-[11px]">
                    <span className="text-[#9CA3AF]">{c.label}</span>
                    <span className={c.passed ? 'text-[#39FF14]' : 'text-red-400'}>
                      {c.value === null || c.value === undefined ? 'no data' : fmtNum(c.value, 2)}
                      <span className="text-[#4B5563]">
                        {' '}/ {c.higher_is_better ? '≥' : '≤'} {fmtNum(c.threshold, 2)}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="border-l-2 border-[#39FF14] pl-4">
          <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">Focus now</p>
          <p className="mt-1 text-sm leading-relaxed text-white" data-testid="stage-focus">{stage.focus}</p>
        </div>
        <div className="border-l-2 border-red-400/50 pl-4">
          <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">Stop</p>
          <p className="mt-1 text-sm leading-relaxed text-[#D1D5DB]" data-testid="stage-stop">{stage.stop}</p>
        </div>
      </div>
    </Panel>
  );
}
