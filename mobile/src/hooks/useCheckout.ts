import { useCallback, useRef, useState } from 'react';
import * as WebBrowser from 'expo-web-browser';
import { messageFromError } from './useAsyncData';
import { orders } from '../api/endpoints';

/**
 * Stripe Checkout from a native app.
 *
 * The backend creates a hosted Checkout session on the seller's connected
 * account and hands back a URL. We open it in an in-app browser (SFSafariView
 * / Custom Tab), which is what Stripe requires — their hosted page must not be
 * embedded in a plain WebView, and card autofill and 3-D Secure only work
 * properly in the real browser surface.
 *
 * When the sheet is dismissed we do NOT assume payment succeeded. The user may
 * have paid, abandoned, or hit the back button on the 3-D Secure step. The
 * server is the only authority, so we poll /api/orders/status/{session_id},
 * which itself re-checks Stripe and settles the order.
 */

export type CheckoutOutcome =
  | { kind: 'paid' }
  | { kind: 'not_paid'; paymentStatus: string }
  | { kind: 'cancelled' }
  | { kind: 'error'; message: string };

const POLL_ATTEMPTS = 5;
const POLL_INTERVAL_MS = 1500;

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function useCheckout() {
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);

  const start = useCallback(
    async (productId: string, size: string): Promise<CheckoutOutcome> => {
      // Double-tap on BUY must not create two Stripe sessions (and two orders).
      if (inFlight.current) return { kind: 'cancelled' };
      inFlight.current = true;
      setBusy(true);

      try {
        const session = await orders.checkout(productId, size);
        const result = await WebBrowser.openBrowserAsync(session.url, {
          // Match the app chrome so the handoff does not feel like leaving.
          toolbarColor: '#050505',
          controlsColor: '#39FF14',
          enableBarCollapsing: true,
        });

        // `dismiss` means the sheet closed — it says nothing about payment.
        if (result.type !== 'opened' && result.type !== 'dismiss') {
          return { kind: 'cancelled' };
        }

        // Stripe's webhook may land a beat after the redirect, so give the
        // server a few chances to report `paid` before calling it unpaid.
        let lastPaymentStatus = 'unknown';
        for (let attempt = 0; attempt < POLL_ATTEMPTS; attempt += 1) {
          const status = await orders.status(session.session_id);
          lastPaymentStatus = status.payment_status;
          if (status.payment_status === 'paid') return { kind: 'paid' };
          if (attempt < POLL_ATTEMPTS - 1) await wait(POLL_INTERVAL_MS);
        }

        return { kind: 'not_paid', paymentStatus: lastPaymentStatus };
      } catch (error) {
        return { kind: 'error', message: messageFromError(error) };
      } finally {
        inFlight.current = false;
        setBusy(false);
      }
    },
    [],
  );

  return { start, busy };
}
