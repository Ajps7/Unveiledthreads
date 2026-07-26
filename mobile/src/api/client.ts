import { API_BASE_URL } from './config';

/**
 * Thin fetch wrapper over the Unveiled Threads API.
 *
 * AUTH MODEL — read this before changing anything here.
 *
 * The backend issues httpOnly access/refresh cookies (see backend/routes/auth.py).
 * React Native's networking stack keeps a native cookie jar on both platforms
 * (NSURLSession on iOS, ForwardingCookieHandler/OkHttp on Android), so those
 * cookies are attached automatically and the app needs no token storage. That
 * is deliberate: httpOnly cookies cannot be read by JS, which is the whole
 * point — there is no token for a compromised bundle to exfiltrate.
 *
 * The consequence is that we cannot inspect the session locally. "Am I logged
 * in?" is answered by calling /api/auth/me, not by reading storage. AuthContext
 * does exactly that on boot.
 *
 * `get_current_user` also accepts `Authorization: Bearer <token>`
 * (backend/core.py), so a token mode is a small change if you ever need one —
 * but it requires a backend change first, because login currently returns the
 * token only as a cookie and never in the response body. README covers it.
 */

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }

  get isAuthError(): boolean {
    return this.status === 401;
  }

  get isRateLimited(): boolean {
    return this.status === 429;
  }
}

/** Raised when the device cannot reach the API at all — distinct from a 5xx. */
export class NetworkError extends Error {
  constructor(message = 'Cannot reach Unveiled Threads. Check your connection.') {
    super(message);
    this.name = 'NetworkError';
  }
}

type Method = 'GET' | 'POST' | 'PUT' | 'DELETE';

/** Query string values we know how to serialise. */
export type QueryParams = Record<string, string | number | boolean | undefined | null>;

interface RequestOptions {
  method?: Method;
  body?: unknown;
  /** Query params; undefined, null and empty-string values are dropped. */
  query?: QueryParams;
  signal?: AbortSignal;
  /** Skip the automatic refresh-and-retry on 401. Used by the refresh call. */
  skipRefresh?: boolean;
}

/** Listeners fired when a session is definitively gone, so the UI can react. */
type SessionExpiredListener = () => void;
const sessionExpiredListeners = new Set<SessionExpiredListener>();

export function onSessionExpired(listener: SessionExpiredListener): () => void {
  sessionExpiredListeners.add(listener);
  return () => sessionExpiredListeners.delete(listener);
}

function notifySessionExpired(): void {
  sessionExpiredListeners.forEach((listener) => listener());
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const base = `${API_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
  if (!query) return base;

  const params = Object.entries(query)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);

  return params.length ? `${base}?${params.join('&')}` : base;
}

async function parseError(response: Response): Promise<ApiError> {
  let detail = `Request failed (${response.status})`;
  try {
    const payload = await response.json();
    if (typeof payload?.detail === 'string') {
      detail = payload.detail;
    } else if (Array.isArray(payload?.detail) && payload.detail.length > 0) {
      // FastAPI validation errors arrive as a list of {loc, msg, type}.
      detail = payload.detail[0]?.msg ?? detail;
    }
  } catch {
    // Non-JSON error body (proxy HTML, empty 502) — keep the generic message.
  }
  return new ApiError(response.status, detail);
}

/**
 * A single in-flight refresh shared by all callers, so a burst of parallel
 * 401s triggers one /auth/refresh rather than one per request.
 */
let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const response = await fetch(buildUrl('/api/auth/refresh'), {
          method: 'POST',
          credentials: 'include',
          headers: { Accept: 'application/json' },
        });
        return response.ok;
      } catch {
        return false;
      } finally {
        // Cleared on the next tick so concurrent callers all observe this result.
        setTimeout(() => {
          refreshInFlight = null;
        }, 0);
      }
    })();
  }
  return refreshInFlight;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, signal, skipRefresh = false } = options;

  const send = async (): Promise<Response> => {
    try {
      return await fetch(buildUrl(path, query), {
        method,
        credentials: 'include',
        signal,
        headers: {
          Accept: 'application/json',
          ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') throw error;
      throw new NetworkError();
    }
  };

  let response = await send();

  // The access cookie lasts an hour, the refresh cookie a week. On a 401 we
  // spend one refresh attempt before declaring the session dead.
  if (response.status === 401 && !skipRefresh) {
    const refreshed = await refreshSession();
    if (refreshed) {
      response = await send();
    } else {
      notifySessionExpired();
      throw await parseError(response);
    }
  }

  if (!response.ok) {
    const error = await parseError(response);
    if (error.isAuthError) notifySessionExpired();
    throw error;
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export const api = {
  get: <T>(path: string, query?: RequestOptions['query'], signal?: AbortSignal) =>
    request<T>(path, { method: 'GET', query, signal }),
  post: <T>(path: string, body?: unknown, options?: Partial<RequestOptions>) =>
    request<T>(path, { ...options, method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};
