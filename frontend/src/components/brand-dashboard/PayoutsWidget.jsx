import { Banknote } from 'lucide-react';

/** Map Stripe currency codes to the symbol most brands expect to see.
 * Falls back to the uppercase ISO code for anything exotic (CHF, NOK, PLN…).
 */
const CURRENCY_SYMBOLS = {
  gbp: '£',
  eur: '€',
  usd: '$',
  cad: 'C$',
  aud: 'A$',
  nzd: 'NZ$',
  jpy: '¥',
  chf: 'CHF ',
  sek: 'kr ',
  dkk: 'kr ',
  nok: 'kr ',
};

const fmt = (amount, currency = 'gbp') => {
  const c = (currency || 'gbp').toLowerCase();
  const sym = CURRENCY_SYMBOLS[c] || `${c.toUpperCase()} `;
  // JPY is a zero-decimal currency in Stripe; everything else is two.
  const dp = c === 'jpy' ? 0 : 2;
  return `${sym}${Number(amount || 0).toFixed(dp)}`;
};

/**
 * Stripe payouts widget (available / pending / next payout + last + history).
 * Renders nothing when `payouts` is null/disconnected.
 *
 * All amounts are formatted in the connected account's own currency so an
 * IE brand sees € and a GB brand sees £ — never a mismatched symbol.
 */
export function PayoutsWidget({ payouts }) {
  if (!payouts?.connected) return null;
  const accountCurrency = payouts.currency || 'gbp';

  return (
    <div className="mb-12 border border-white/10 bg-[#0A0A0A] p-6" data-testid="payouts-widget">
      <div className="flex items-start gap-4">
        <Banknote className="w-8 h-8 text-[#39FF14] flex-shrink-0" />
        <div className="flex-1">
          <h3 className="text-xl font-bold text-white mb-4" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            PAYOUTS
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="border border-white/5 bg-[#0F0F0F] p-4">
              <p className="text-xs uppercase tracking-wider text-[#9CA3AF] mb-1">Available now</p>
              <p className="text-2xl font-bold text-[#39FF14]" data-testid="payouts-available">
                {fmt(payouts.available, accountCurrency)}
              </p>
              <p className="text-[10px] text-[#9CA3AF] mt-1">Ready to pay out to your bank</p>
            </div>
            <div className="border border-white/5 bg-[#0F0F0F] p-4">
              <p className="text-xs uppercase tracking-wider text-[#9CA3AF] mb-1">Pending</p>
              <p className="text-2xl font-bold text-white" data-testid="payouts-pending">
                {fmt(payouts.pending, accountCurrency)}
              </p>
              <p className="text-[10px] text-[#9CA3AF] mt-1">Recent sales still settling with Stripe</p>
            </div>
            <div className="border border-white/5 bg-[#0F0F0F] p-4">
              <p className="text-xs uppercase tracking-wider text-[#9CA3AF] mb-1">Next payout</p>
              {payouts.next_payout ? (
                <>
                  <p className="text-2xl font-bold text-white" data-testid="payouts-next">
                    {fmt(payouts.next_payout.amount, payouts.next_payout.currency || accountCurrency)}
                  </p>
                  <p className="text-[10px] text-[#9CA3AF] mt-1">
                    Arrives{' '}
                    {new Date(payouts.next_payout.arrival_date).toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'short',
                    })}
                  </p>
                </>
              ) : (
                <>
                  <p className="text-2xl font-bold text-white" data-testid="payouts-next">—</p>
                  <p className="text-[10px] text-[#9CA3AF] mt-1">
                    {payouts.schedule_interval === 'manual'
                      ? 'Manual payouts — trigger from your Stripe dashboard'
                      : `Paid out ${payouts.schedule_interval || 'automatically'} once funds are available`}
                  </p>
                </>
              )}
            </div>
          </div>
          {payouts.last_payout && (
            <p className="text-xs text-[#9CA3AF] mt-4" data-testid="payouts-last">
              Last payout: {fmt(payouts.last_payout.amount, payouts.last_payout.currency || accountCurrency)} on{' '}
              {new Date(payouts.last_payout.arrival_date).toLocaleDateString('en-GB', {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
              })}
            </p>
          )}
          {payouts.history?.length > 0 && (
            <div className="mt-6" data-testid="payout-history">
              <p className="text-xs uppercase tracking-wider text-[#9CA3AF] mb-2">Payout history</p>
              <div className="border border-white/5 divide-y divide-white/5 max-h-64 overflow-y-auto">
                {payouts.history.map((p, i) => (
                  <div
                    key={`${p.arrival_date}-${i}`}
                    className="flex items-center justify-between px-4 py-2.5 text-sm"
                    data-testid={`payout-row-${i}`}
                  >
                    <span className="text-[#9CA3AF]">
                      {new Date(p.arrival_date).toLocaleDateString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </span>
                    <span
                      className={`text-[10px] uppercase tracking-wider px-2 py-0.5 border ${
                        p.status === 'paid'
                          ? 'text-[#39FF14] border-[#39FF14]/30 bg-[#39FF14]/5'
                          : p.status === 'failed' || p.status === 'canceled'
                          ? 'text-red-400 border-red-500/30 bg-red-500/5'
                          : 'text-yellow-400 border-yellow-500/30 bg-yellow-500/5'
                      }`}
                    >
                      {p.status.replace('_', ' ')}
                    </span>
                    <span className="text-white font-bold">{fmt(p.amount, p.currency || accountCurrency)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
