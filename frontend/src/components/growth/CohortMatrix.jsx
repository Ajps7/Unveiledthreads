import { EmptyNote, Panel, fmtPct } from './shared';

// Retention by acquisition month. Reading down a column answers "is the
// product getting better?"; reading across a row answers "how long do
// buyers last?".
function cellStyle(rate) {
  if (rate === null || rate === undefined) return { backgroundColor: 'transparent' };
  // Opacity carries the value; a single accent hue keeps it readable in the
  // dark theme without inventing a second colour scale.
  const alpha = Math.min(0.85, 0.08 + rate * 1.6);
  return { backgroundColor: `rgba(57, 255, 20, ${alpha})` };
}

export function CohortMatrix({ cohorts, repeatRate }) {
  const rows = cohorts?.rows || [];
  const offsets = cohorts?.months || [];

  return (
    <Panel
      title="Buyer cohorts"
      subtitle="Each row is the month a buyer first purchased; each column is the share of that cohort who bought again N months later. Month 0 is 100% by definition and is omitted."
      testId="growth-cohorts"
      right={
        <div className="text-right">
          <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">Repeat rate (window)</p>
          <p className="text-xl font-black text-white">{fmtPct(repeatRate)}</p>
        </div>
      }
    >
      {rows.length === 0 ? (
        <EmptyNote>No completed orders yet, so there are no cohorts to follow.</EmptyNote>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] border-collapse text-xs">
            <thead>
              <tr>
                <th className="border-b border-white/10 px-2 py-2 text-left font-normal uppercase tracking-wider text-[#6B7280]">Cohort</th>
                <th className="border-b border-white/10 px-2 py-2 text-right font-normal uppercase tracking-wider text-[#6B7280]">Buyers</th>
                {offsets.map((m) => (
                  <th key={m} className="border-b border-white/10 px-2 py-2 text-center font-normal uppercase tracking-wider text-[#6B7280]">
                    M{m}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const byOffset = new Map(row.values.map((v) => [v.offset, v]));
                return (
                  <tr key={row.cohort} data-testid={`cohort-${row.cohort}`}>
                    <td className="border-b border-white/5 px-2 py-2 text-[#D1D5DB]">{row.cohort}</td>
                    <td className="border-b border-white/5 px-2 py-2 text-right text-[#9CA3AF]">{row.size}</td>
                    {offsets.map((m) => {
                      const cell = byOffset.get(m);
                      return (
                        <td
                          key={m}
                          className="border-b border-white/5 px-2 py-2 text-center text-white"
                          style={cell ? cellStyle(cell.rate) : undefined}
                          title={cell ? `${cell.retained} of ${row.size} bought again` : 'Not yet reached'}
                        >
                          {cell ? fmtPct(cell.rate, 0) : ''}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
