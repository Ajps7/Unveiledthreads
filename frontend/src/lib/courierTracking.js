// Maps a courier name + tracking number to its public tracking URL.
// Returns null if we don't have a known URL pattern for that courier.

const COURIER_URLS = {
  'royal mail': (n) => `https://www.royalmail.com/track-your-item#/tracking-results/${encodeURIComponent(n)}`,
  'evri': (n) => `https://www.evri.com/track/parcel/${encodeURIComponent(n)}`,
  'hermes': (n) => `https://www.evri.com/track/parcel/${encodeURIComponent(n)}`,
  'hermes uk': (n) => `https://www.evri.com/track/parcel/${encodeURIComponent(n)}`,
  'dpd': (n) => `https://track.dpd.co.uk/parcels/${encodeURIComponent(n)}`,
  'dpd uk': (n) => `https://track.dpd.co.uk/parcels/${encodeURIComponent(n)}`,
  'yodel': (n) => `https://www.yodel.co.uk/track/${encodeURIComponent(n)}`,
  'ups': (n) => `https://www.ups.com/track?tracknum=${encodeURIComponent(n)}`,
  'fedex': (n) => `https://www.fedex.com/fedextrack/?tracknumbers=${encodeURIComponent(n)}`,
};

export function getTrackingUrl(courier, trackingNumber) {
  if (!courier || !trackingNumber) return null;
  const key = courier.trim().toLowerCase();
  const builder = COURIER_URLS[key];
  return builder ? builder(trackingNumber) : null;
}
