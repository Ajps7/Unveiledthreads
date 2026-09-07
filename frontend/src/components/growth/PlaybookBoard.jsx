import { useState } from 'react';
import { ChevronDown, Clock, PoundSterling, Ban, User } from 'lucide-react';
import { EmptyNote, Panel, fmtNum } from './shared';

function PlayCard({ play, rank, testId }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-white/10 bg-white/[0.02]" data-testid={testId}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-white/5"
        aria-expanded={open}
      >
        {rank !== undefined && (
          <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center border border-[#39FF14]/40 text-xs font-bold text-[#39FF14]">
            {rank}
          </span>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-white">{play.name}</p>
          <p className="mt-1 text-xs leading-relaxed text-[#9CA3AF]">{play.hypothesis}</p>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-[10px] uppercase tracking-wider text-[#6B7280]">
            <span className="text-[#39FF14]/80">Priority {fmtNum(play.priority, 0)}</span>
            <span>ICE {fmtNum(play.ice, 0)}</span>
            <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{play.time_to_signal_days}d to signal</span>
            <span className="flex items-center gap-1"><User className="h-3 w-3" />{play.owner}</span>
          </div>
        </div>
        <ChevronDown className={`mt-1 h-4 w-4 shrink-0 text-[#6B7280] transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="border-t border-white/10 px-4 py-4">
          <p className="text-xs leading-relaxed text-[#D1D5DB]">
            <span className="text-[#6B7280]">Why it works: </span>{play.mechanism}
          </p>

          <h4 className="mt-4 text-[10px] font-bold uppercase tracking-wider text-[#9CA3AF]">How to run it</h4>
          <ol className="mt-2 space-y-1.5">
            {play.steps.map((step, i) => (
              <li key={i} className="flex gap-2 text-xs leading-relaxed text-[#D1D5DB]">
                <span className="shrink-0 text-[#39FF14]">{i + 1}.</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="border border-white/10 p-3">
              <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">Expected</p>
              <p className="mt-1 text-xs text-[#39FF14]">
                {play.expected.metric.replace(/_/g, ' ')} {play.expected.direction} {play.expected.magnitude}
              </p>
            </div>
            <div className="border border-white/10 p-3">
              <p className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#6B7280]">
                <PoundSterling className="h-3 w-3" /> Cost
              </p>
              <p className="mt-1 text-xs text-[#D1D5DB]">{play.cost}</p>
            </div>
          </div>

          <div className="mt-3 border-l-2 border-red-400/40 pl-3">
            <p className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#6B7280]">
              <Ban className="h-3 w-3" /> Kill criteria
            </p>
            <p className="mt-1 text-xs leading-relaxed text-[#D1D5DB]">{play.kill_criteria}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// Plays are ranked by ICE and then gated by stage. The "not yet" column is
// the part that makes this advice rather than a list of good ideas.
export function PlaybookBoard({ playbook }) {
  if (!playbook) return null;
  const { now = [], next = [], not_yet: notYet = [], counts } = playbook;

  return (
    <Panel
      title="Playbook"
      subtitle={`${counts?.triggered ?? 0} plays triggered by your current numbers, ranked by impact x confidence x ease, then gated by stage.`}
      testId="growth-playbook"
    >
      <div className="grid gap-6 lg:grid-cols-3">
        <div>
          <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-[#39FF14]">Do now</h3>
          <div className="space-y-2">
            {now.length === 0 && <EmptyNote>Nothing is triggered — which usually means there is not enough data yet.</EmptyNote>}
            {now.map((play, i) => (
              <PlayCard key={play.key} play={play} rank={i + 1} testId={`play-now-${play.key}`} />
            ))}
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-[#9CA3AF]">Queue behind it</h3>
          <div className="space-y-2">
            {next.length === 0 && <EmptyNote>Nothing queued.</EmptyNote>}
            {next.map((play) => (
              <PlayCard key={play.key} play={play} testId={`play-next-${play.key}`} />
            ))}
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-red-400">Not yet</h3>
          <div className="space-y-2">
            {notYet.length === 0 && <EmptyNote>No plays are being held back.</EmptyNote>}
            {notYet.map((entry) => (
              <div key={entry.key} className="border border-white/10 bg-white/[0.02] px-4 py-3" data-testid={`play-notyet-${entry.key}`}>
                <p className="text-sm font-bold text-[#9CA3AF]">{entry.name}</p>
                <p className="mt-1 text-xs leading-relaxed text-[#6B7280]">{entry.reason}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}
