import { useState } from 'react';
import axios from 'axios';
import { Button } from '../ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  CheckCircle2,
  CreditCard,
  Loader2,
  AlertTriangle,
  ExternalLink,
  RefreshCw,
  Flag,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Allowed banking countries for the brand reset flow. Sourced from
// STRIPE_SUPPORTED_COUNTRIES in backend/core.py — keep in sync when adding
// new regions. The backend is the source of truth and will reject anything
// else; this just avoids showing an option that would 400 immediately.
const COUNTRY_OPTIONS = [
  { code: 'GB', label: 'United Kingdom' },
  { code: 'IE', label: 'Republic of Ireland' },
  { code: 'FR', label: 'France' },
  { code: 'DE', label: 'Germany' },
  { code: 'ES', label: 'Spain' },
  { code: 'IT', label: 'Italy' },
  { code: 'NL', label: 'Netherlands' },
  { code: 'PT', label: 'Portugal' },
];

/**
 * Stripe Connect onboarding / status panel for the brand dashboard.
 *
 * Three states:
 *  - fully connected  → green, "open Stripe dashboard"
 *  - partially connected → yellow, resume onboarding + list what Stripe still needs
 *  - not connected   → yellow, connect with Stripe
 *
 * Extra: when the account is INCOMPLETE (not fully connected) a brand can
 * reset their Stripe account and change their registered country. This fixes
 * the case where an Irish brand started onboarding on a GB-defaulted account
 * and got stuck with a greyed-out address field.
 */
export function StripeConnectPanel({ connectStatus, connectLoading, onConnect, onOpenDashboard, onReset }) {
  const fullyConnected = connectStatus && connectStatus.charges_enabled && connectStatus.payouts_enabled;
  const partiallyConnected = connectStatus && connectStatus.stripe_account_id && !fullyConnected;
  const [showCountryChange, setShowCountryChange] = useState(false);
  const [newCountry, setNewCountry] = useState(connectStatus?.stripe_country || 'GB');
  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState('');

  const handleReset = async () => {
    setResetError('');
    const label = COUNTRY_OPTIONS.find((c) => c.code === newCountry)?.label || newCountry;
    const ok = window.confirm(
      `Reset Stripe and set your banking country to ${label}?\n\n` +
      `This deletes your incomplete Stripe account and starts over. Your brand profile, ` +
      `listings and buyers are untouched. Once reset, click Connect with Stripe to onboard fresh.`
    );
    if (!ok) return;
    setResetting(true);
    try {
      await axios.post(
        `${API}/api/connect/reset-account`,
        { stripe_country: newCountry },
        { withCredentials: true }
      );
      setShowCountryChange(false);
      if (onReset) await onReset();
    } catch (e) {
      setResetError(e.response?.data?.detail || 'Could not reset the Stripe account');
    } finally {
      setResetting(false);
    }
  };

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

              {/* Change country / restart — only when onboarding is incomplete.
                  Stripe fixes country once a connected account is created, so
                  the only way to correct a wrong country is to delete and
                  recreate the account. */}
              <div className="mt-6 pt-4 border-t border-white/10">
                {!showCountryChange ? (
                  <button
                    type="button"
                    onClick={() => setShowCountryChange(true)}
                    className="text-xs text-[#9CA3AF] hover:text-white underline inline-flex items-center gap-1"
                    data-testid="change-stripe-country-button"
                  >
                    <Flag className="w-3 h-3" />
                    Stuck on the wrong country? Change it and restart
                  </button>
                ) : (
                  <div className="space-y-3" data-testid="change-stripe-country-form">
                    <p className="text-[11px] text-[#9CA3AF] uppercase tracking-wider">
                      Reset &amp; change banking country
                    </p>
                    <p className="text-xs text-[#9CA3AF]">
                      Your Stripe connected account&apos;s country is permanent once set, so if your address
                      field is locked to the wrong country we have to delete and restart. Your brand profile
                      and listings aren&apos;t affected.
                    </p>
                    <div className="flex items-center gap-2">
                      <Select value={newCountry} onValueChange={setNewCountry}>
                        <SelectTrigger
                          className="flex-1 bg-transparent border-white/20 rounded-none text-white"
                          data-testid="reset-country-select"
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                          {COUNTRY_OPTIONS.map((c) => (
                            <SelectItem
                              key={c.code}
                              value={c.code}
                              className="text-white hover:bg-white/10 rounded-none"
                            >
                              {c.label} ({c.code})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        className="btn-secondary"
                        onClick={handleReset}
                        disabled={resetting}
                        data-testid="reset-stripe-country-confirm"
                      >
                        {resetting ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                      </Button>
                    </div>
                    <p className="text-[11px] text-yellow-300">
                      This sets your payout country and can&apos;t be changed later.
                    </p>
                    {resetError && (
                      <p className="text-xs text-red-400" data-testid="reset-stripe-error">
                        {resetError}
                      </p>
                    )}
                    <button
                      type="button"
                      onClick={() => { setShowCountryChange(false); setResetError(''); }}
                      className="text-[11px] text-[#9CA3AF] hover:text-white underline"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
