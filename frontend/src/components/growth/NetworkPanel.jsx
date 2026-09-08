import { MapPin, Layers, AlertTriangle } from 'lucide-react';
import { EmptyNote, Panel, fmtMoney, fmtNum, fmtPct } from './shared';

// Cold-start view: which slice of the market is closest to working, how
// concentrated GMV is, and which brands have never sold.
export function NetworkPanel({ detail, metrics }) {
  const atomic = detail?.atomic_cell;
  const topBrands = detail?.top_brands || [];
  const stalled = detail?.stalled_brands || [];

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Panel
        title="Atomic network"
        subtitle="Liquidity is local. This is the densest category-and-market cell you have — the slice most likely to reach self-sustaining liquidity first, and therefore the one to over-serve."
        icon={MapPin}
        testId="growth-atomic"
      >
        {!atomic?.found ? (
          <EmptyNote>No completed orders yet, so no cell can be ranked.</EmptyNote>
        ) : (
          <>
            <div className="border border-[#39FF14]/30 bg-[#39FF14]/5 p-4">
              <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">Densest cell</p>
              <p className="mt-1 text-lg font-bold text-white" data-testid="atomic-top-cell">
                {atomic.top.category || 'Uncategorised'} · {atomic.top.market}
              </p>
              <div className="mt-3 grid grid-cols-4 gap-3 text-center">
                {[
                  ['Brands', atomic.top.brands],
                  ['Buyers', atomic.top.buyers],
                  ['Orders', atomic.top.orders],
                  ['Density', fmtNum(atomic.top.density, 2)],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">{label}</p>
                    <p className="text-base font-bold text-white">{value}</p>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-[11px] text-[#9CA3AF]">
                {fmtPct(atomic.concentration)} of all orders sit in this one cell.
              </p>
            </div>

            {atomic.cells.length > 1 && (
              <div className="mt-4 space-y-1">
                <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">Other cells</p>
                {atomic.cells.slice(1).map((cell) => (
                  <div key={`${cell.category}-${cell.market}`} className="flex items-baseline justify-between gap-2 text-xs">
                    <span className="text-[#D1D5DB]">{cell.category || 'Uncategorised'} · {cell.market}</span>
                    <span className="text-[#6B7280]">{cell.orders} orders · {cell.brands} brands</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </Panel>

      <Panel
        title="Concentration"
        subtitle="If a small number of brands carry GMV, the marketplace's numbers are really those brands' numbers — and they can leave."
        icon={Layers}
        testId="growth-concentration"
      >
        <div className="mb-4 grid grid-cols-3 gap-3">
          {[
            ['HHI', fmtNum(metrics?.gmv_hhi, 2)],
            ['Gini', fmtNum(metrics?.gmv_gini, 2)],
            ['Top 3 share', fmtPct(metrics?.top3_gmv_share)],
          ].map(([label, value]) => (
            <div key={label} className="border border-white/10 p-3 text-center">
              <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">{label}</p>
              <p className="mt-1 text-lg font-bold text-white">{value}</p>
            </div>
          ))}
        </div>

        {topBrands.length === 0 ? (
          <EmptyNote>No brand has sold anything in this window.</EmptyNote>
        ) : (
          <div className="space-y-2">
            {topBrands.slice(0, 6).map((brand) => (
              <div key={brand.brand_id} data-testid={`top-brand-${brand.brand_id}`}>
                <div className="flex items-baseline justify-between gap-2 text-xs">
                  <span className="truncate text-[#D1D5DB]">{brand.name}</span>
                  <span className="shrink-0 text-[#9CA3AF]">
                    {fmtMoney(brand.gmv)} · {fmtPct(brand.gmv_share, 0)}
                  </span>
                </div>
                <div className="mt-1 h-1 w-full bg-white/10">
                  <div className="h-full bg-[#39FF14]" style={{ width: `${Math.min(100, brand.gmv_share * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}

        {stalled.length > 0 && (
          <div className="mt-5 border-t border-white/10 pt-4">
            <p className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-amber-400">
              <AlertTriangle className="h-3 w-3" />
              {detail.stalled_brand_count} brands have never sold
            </p>
            <div className="mt-2 space-y-1">
              {stalled.slice(0, 5).map((brand) => (
                <div key={brand.id} className="flex items-baseline justify-between gap-2 text-xs">
                  <span className="truncate text-[#D1D5DB]">{brand.name || 'Unnamed brand'}</span>
                  <span className="shrink-0 text-[#6B7280]">
                    {brand.days_since_join}d in · {brand.has_listings ? 'has listings' : 'never listed'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Panel>
    </div>
  );
}
