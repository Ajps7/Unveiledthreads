import { ClipboardList, OctagonX, Target, HelpCircle, AlertTriangle } from 'lucide-react';
import { Panel, SEVERITY_STYLES } from './shared';

// The Monday memo. Deliberately the first thing on the page: the numbers
// below it exist to support this, not the other way round.
export function MemoPanel({ memo, confidence }) {
  if (!memo) return null;

  return (
    <Panel
      title="The memo"
      subtitle="What a growth lead would tell you if they had read every number below."
      icon={ClipboardList}
      testId="growth-memo"
    >
      <p
        className="border-l-2 border-[#39FF14] pl-4 text-lg font-medium leading-relaxed text-white"
        data-testid="memo-headline"
      >
        {memo.headline}
      </p>

      <div className="mt-6 space-y-2">
        {memo.where_we_are?.map((line, i) => (
          <p key={i} className="text-sm leading-relaxed text-[#D1D5DB]">{line}</p>
        ))}
      </div>

      {memo.whats_happening?.length > 0 && (
        <div className="mt-8">
          <h3 className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#9CA3AF]">
            <AlertTriangle className="h-4 w-4" /> What is actually happening
          </h3>
          <div className="space-y-3">
            {memo.whats_happening.map((item) => {
              const sev = SEVERITY_STYLES[item.severity] || SEVERITY_STYLES.low;
              return (
                <div key={item.title} className={`border-l-2 ${sev.border} bg-white/[0.02] px-4 py-3`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`text-sm font-bold uppercase tracking-wide ${sev.text}`}>{item.title}</span>
                    <span className="text-[10px] uppercase tracking-wider text-[#6B7280]">{sev.label}</span>
                  </div>
                  <p className="mt-1 text-sm text-[#D1D5DB]">{item.detail}</p>
                  <p className="mt-2 text-xs leading-relaxed text-[#9CA3AF]">{item.why}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#39FF14]">
            <Target className="h-4 w-4" /> Next 30 days
          </h3>
          <ol className="space-y-3">
            {memo.next_30_days?.map((item, i) => (
              <li key={item.name} className="border border-white/10 p-3" data-testid={`memo-next-${i}`}>
                <p className="text-sm font-bold text-white">{i + 1}. {item.name}</p>
                <p className="mt-1 text-xs text-[#9CA3AF]">{item.why}</p>
                {item.first_step && (
                  <p className="mt-2 text-xs text-[#D1D5DB]">
                    <span className="text-[#6B7280]">Start with: </span>{item.first_step}
                  </p>
                )}
                <p className="mt-2 text-[11px] uppercase tracking-wider text-[#39FF14]/80">{item.expect}</p>
                <p className="mt-1 text-[10px] uppercase tracking-wider text-[#6B7280]">Owner · {item.owner}</p>
              </li>
            ))}
          </ol>
        </div>

        <div>
          <h3 className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-red-400">
            <OctagonX className="h-4 w-4" /> Stop doing
          </h3>
          <ul className="space-y-2">
            {memo.stop_doing?.map((line, i) => (
              <li key={i} className="border-l-2 border-red-400/40 pl-3 text-sm leading-relaxed text-[#D1D5DB]">
                {line}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-8 border-t border-white/10 pt-5">
        <h3 className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#9CA3AF]">
          <HelpCircle className="h-4 w-4" /> What would change my mind
        </h3>
        {confidence?.level && (
          <p className="mb-2 text-[11px] uppercase tracking-wider text-[#6B7280]" data-testid="memo-confidence">
            Confidence · {String(confidence.level).replace('_', ' ')} ·{' '}
            {confidence.orders_in_window} orders, {confidence.views_in_window} views in window
          </p>
        )}
        <ul className="space-y-2">
          {memo.what_would_change_my_mind?.map((line, i) => (
            <li key={i} className="text-xs leading-relaxed text-[#9CA3AF]">{line}</li>
          ))}
        </ul>
      </div>
    </Panel>
  );
}
