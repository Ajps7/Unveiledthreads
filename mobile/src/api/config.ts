import Constants from 'expo-constants';

type Extra = { apiBaseUrl?: string; webBaseUrl?: string };

const extra = (Constants.expoConfig?.extra ?? {}) as Extra;

/**
 * Backend origin. Override per-environment in app.json `extra.apiBaseUrl`,
 * or with EXPO_PUBLIC_API_BASE_URL when running `expo start`.
 *
 * NOTE: auth cookies are issued Secure, so they are only stored over HTTPS.
 * Point this at an https:// origin (a tunnel is fine) — a plain http://
 * localhost backend will authenticate once and then appear logged out.
 * See mobile/README.md → "Auth in a native client".
 */
export const API_BASE_URL = (
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  extra.apiBaseUrl ||
  'https://unveiledthreads.co.uk'
).replace(/\/$/, '');

/**
 * Web origin. Used as `origin_url` on checkout so Stripe's success/cancel
 * redirects land on real pages, and to resolve relative /api/files/... image
 * paths returned by the API.
 */
export const WEB_BASE_URL = (
  process.env.EXPO_PUBLIC_WEB_BASE_URL ||
  extra.webBaseUrl ||
  'https://unveiledthreads.co.uk'
).replace(/\/$/, '');

/** The API returns image URLs as root-relative paths (/api/files/...). */
export function resolveImageUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  return `${API_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
}
