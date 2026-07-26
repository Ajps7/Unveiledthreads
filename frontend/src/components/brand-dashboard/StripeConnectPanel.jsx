import { Button } from '../ui/button';
import { CheckCircle2, CreditCard, Loader2, AlertTriangle, ExternalLink } from 'lucide-react';

/**
 * Stripe Connect onboarding / status panel for the brand dashboard.
 *
 * Three states:
 *  - fully connected  → green, "open Stripe dashboard"
 *  - partially connected → yellow, resume onboarding + list what Stripe still needs
 *  - not connected   → yellow, connect with Stripe
 */
export function StripeConnectPanel({ connectStatus, connectLoading, onConnect, onOpenDashboard }) {
  const fullyConnected = connectStatus && connectStatus.charges_enabled && connectStatus.payouts_enabled;
  const partiallyConnected = connectStatus && connectStatus.stripe_account_id && !fullyConnected;

  return (
    <div
      className={`mb-12 border p-6 ${
        fullyConnected ? 'border-[#39FF14]/30 bg-[#39FF14]/5' : 'border-yellow-500/30 bg-yellow-500/5'
      }`}
      data-testid="stripe-connect-panel"
    >
      <div className="flex items-start gap-4">
        {fullyConnected ? (
          <CheckCircle2 className="w-8 h-8 text-[#39FF14] flex-shrink-0" />
        ) : (
          <CreditCard className="w-8 h-8 text-yellow-500 flex-shrink-0" />
        )}
        <div className="flex-1">
          <h3 className="text-xl font-bold text-white mb-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            {fullyConnected
              ? 'STRIPE PAYOUTS CONNECTED'
              : partiallyConnected
              ? 'FINISH STRIPE ONBOARDING'
              : 'CONNECT STRIPE TO START SELLING'}
          </h3>
          {fullyConnected ? (
            <>
              <p className="text-[#9CA3AF] mb-4">
                Your brand is set up to receive payments. Buyers pay through Unveiled Threads plus a small Buyer
                Protection fee (5% + £0.49, max £6 per order) — you keep 100% of your listed price and shipping,
                paid straight to your bank via Stripe.
              </p>
              <Button className="btn-secondary" onClick={onOpenDashboard} data-testid="open-stripe-dashboard-button">
                <ExternalLink className="w-4 h-4 mr-2" />
                Open Stripe Dashboard
              </Button>
            </>
          ) : (
            <>
              <p className="text-[#9CA3AF] mb-2">
                We use <strong className="text-white">Stripe Express</strong> to handle your payouts securely.
                Stripe collects your bank details, ID and tax info — Unveiled Threads never sees your sensitive data.
              </p>
              <p className="text-[#9CA3AF] mb-4 text-sm">
                ⚡ Onboarding takes about 5 minutes. You won&apos;t be able to receive payouts until this is complete,
                and your products won&apos;t appear in the public shop.
              </p>
              {partiallyConnected && connectStatus.requirements_due?.length > 0 && (
                <div className="border border-yellow-500/30 bg-[#0A0A0A] p-3 mb-4 text-xs">
                  <div className="flex items-center gap-2 mb-1 text-yellow-400 font-bold">
                    <AlertTriangle className="w-3 h-3" /> Stripe still needs:
                  </div>
                  <ul className="text-[#9CA3AF] list-disc list-inside">
                    {connectStatus.requirements_due.slice(0, 5).map((r) => (
                      <li key={r}>{r.replace(/_/g, ' ')}</li>
                    ))}
                  </ul>
                </div>
              )}
              <Button
                className="btn-primary"
                onClick={onConnect}
                disabled={connectLoading}
                data-testid="connect-stripe-button"
              >
                {connectLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <CreditCard className="w-4 h-4 mr-2" />
                )}
                {partiallyConnected ? 'Resume Onboarding' : 'Connect with Stripe'}
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
