/**
 * Buyer Protection fee — MUST stay identical to:
 *   - backend  calculate_buyer_fee()   (backend/core.py)
 *   - frontend calcBuyerFee()          (frontend/src/lib/fees.js)
 *
 * min(subtotal * 5% + £0.49, £6.00), buyer-paid, charged on the item subtotal
 * only (never on shipping). Sellers keep 100% of price + shipping.
 *
 * The server is authoritative — this exists so the app can show an honest
 * price breakdown before the user commits, not to compute what they are
 * charged.
 */
export const PLATFORM_FEE_RATE = 0.05;
export const PLATFORM_FEE_FIXED = 0.49;
export const PLATFORM_FEE_CAP = 6.0;

export function calcBuyerFee(subtotal: number): number {
  const raw = Math.min(subtotal * PLATFORM_FEE_RATE + PLATFORM_FEE_FIXED, PLATFORM_FEE_CAP);
  return Math.round(raw * 100) / 100;
}

export const BUYER_PROTECTION_BLURB =
  'Buyer Protection (5% + £0.49, max £6): money-back guarantee, easy returns, and ' +
  'hand-vetted independent brands. This is how we keep the platform commission-free ' +
  'for independent brands.';

export interface PriceBreakdown {
  item: number;
  buyerProtection: number;
  shipping: number;
  total: number;
}

export function buildBreakdown(price: number, shippingCost: number): PriceBreakdown {
  const buyerProtection = calcBuyerFee(price);
  return {
    item: price,
    buyerProtection,
    shipping: shippingCost,
    total: Math.round((price + buyerProtection + shippingCost) * 100) / 100,
  };
}
