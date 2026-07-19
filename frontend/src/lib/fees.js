export const PLATFORM_FEE_RATE = 0.05;
export const PLATFORM_FEE_FIXED = 0.49;
export const PLATFORM_FEE_CAP = 6.0;

export const calcBuyerFee = (subtotal) =>
  Math.round(Math.min(subtotal * PLATFORM_FEE_RATE + PLATFORM_FEE_FIXED, PLATFORM_FEE_CAP) * 100) / 100;

export const BUYER_PROTECTION_TOOLTIP =
  'Buyer Protection (5% + £0.49, max £6): money-back guarantee, easy returns, and hand-vetted independent brands. This is how we keep the platform commission-free for independent brands.';
