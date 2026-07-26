/** UK formatting helpers — the product is UK-only, so no locale switching. */

export function gbp(amount: number | null | undefined): string {
  const value = typeof amount === 'number' && Number.isFinite(amount) ? amount : 0;
  return `£${value.toFixed(2)}`;
}

/** "3 Mar 2026" — short, unambiguous, UK order. */
export function shortDate(input: string | Date | null | undefined): string {
  if (!input) return '';
  const date = typeof input === 'string' ? new Date(input) : input;
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/** "2 hours ago" for message and notification lists. */
export function relativeTime(input: string | Date | null | undefined): string {
  if (!input) return '';
  const date = typeof input === 'string' ? new Date(input) : input;
  if (Number.isNaN(date.getTime())) return '';

  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return 'just now';

  const units: [number, string][] = [
    [60, 'minute'],
    [3600, 'hour'],
    [86400, 'day'],
    [604800, 'week'],
  ];

  for (let i = units.length - 1; i >= 0; i -= 1) {
    const [unitSeconds, label] = units[i];
    if (seconds >= unitSeconds) {
      const count = Math.floor(seconds / unitSeconds);
      return `${count} ${label}${count === 1 ? '' : 's'} ago`;
    }
  }
  return shortDate(date);
}

/** Order/shipping status → human label. Mirrors the web timeline wording. */
export const SHIPPING_STATUS_LABELS: Record<string, string> = {
  confirmed: 'Order confirmed',
  processing: 'Being packed',
  shipped: 'Shipped',
  in_transit: 'In transit',
  out_for_delivery: 'Out for delivery',
  delivered: 'Delivered',
};

export function shippingLabel(status: string | null | undefined): string {
  if (!status) return 'Order confirmed';
  return SHIPPING_STATUS_LABELS[status] ?? status.replace(/_/g, ' ');
}
