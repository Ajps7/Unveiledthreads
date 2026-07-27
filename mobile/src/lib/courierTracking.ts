/**
 * Maps a courier name + tracking number to its public tracking URL.
 * Mirrors frontend/src/lib/courierTracking.js and the backend's
 * COURIER_TRACKING_URLS — keep all three in step when adding a courier.
 *
 * Returns null when we have no known URL pattern, in which case the UI shows
 * the bare tracking number rather than a dead link.
 */
type UrlBuilder = (trackingNumber: string) => string;

const COURIER_URLS: Record<string, UrlBuilder> = {
  'royal mail': (n) =>
    `https://www.royalmail.com/track-your-item#/tracking-results/${encodeURIComponent(n)}`,
  evri: (n) => `https://www.evri.com/track/parcel/${encodeURIComponent(n)}`,
  hermes: (n) => `https://www.evri.com/track/parcel/${encodeURIComponent(n)}`,
  'hermes uk': (n) => `https://www.evri.com/track/parcel/${encodeURIComponent(n)}`,
  dpd: (n) => `https://track.dpd.co.uk/parcels/${encodeURIComponent(n)}`,
  'dpd uk': (n) => `https://track.dpd.co.uk/parcels/${encodeURIComponent(n)}`,
  yodel: (n) => `https://www.yodel.co.uk/track/${encodeURIComponent(n)}`,
  ups: (n) => `https://www.ups.com/track?tracknum=${encodeURIComponent(n)}`,
  fedex: (n) => `https://www.fedex.com/fedextrack/?tracknumbers=${encodeURIComponent(n)}`,
};

export function getTrackingUrl(
  courier: string | null | undefined,
  trackingNumber: string | null | undefined,
): string | null {
  if (!courier || !trackingNumber) return null;
  const builder = COURIER_URLS[courier.trim().toLowerCase()];
  return builder ? builder(trackingNumber) : null;
}
