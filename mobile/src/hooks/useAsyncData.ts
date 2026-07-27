import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, NetworkError } from '../api/client';

/**
 * Load-once-with-refresh helper used by every list screen.
 *
 * Aborts the in-flight request on unmount and on re-run, so a fast tab switch
 * cannot land a stale response on top of a newer one. Never sets state after
 * unmount.
 */

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  reload: () => void;
  refresh: () => void;
  /** Apply a local change without a round trip (e.g. optimistic wishlist toggle). */
  setData: (updater: (current: T | null) => T | null) => void;
}

export function messageFromError(error: unknown): string {
  if (error instanceof NetworkError) return error.message;
  if (error instanceof ApiError) {
    if (error.isRateLimited) return 'Slow down a moment — too many requests.';
    return error.detail;
  }
  return 'Something went wrong. Pull to refresh.';
}

export function useAsyncData<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  deps: unknown[] = [],
): AsyncState<T> {
  const [data, setDataState] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mounted = useRef(true);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      controller.current?.abort();
    };
  }, []);

  const run = useCallback(
    async (isRefresh: boolean) => {
      controller.current?.abort();
      const next = new AbortController();
      controller.current = next;

      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      try {
        const result = await loader(next.signal);
        if (!mounted.current || next.signal.aborted) return;
        setDataState(result);
      } catch (err) {
        if (!mounted.current || next.signal.aborted) return;
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(messageFromError(err));
      } finally {
        if (mounted.current && !next.signal.aborted) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    deps,
  );

  useEffect(() => {
    void run(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run]);

  const setData = useCallback((updater: (current: T | null) => T | null) => {
    setDataState((current) => updater(current));
  }, []);

  return {
    data,
    loading,
    refreshing,
    error,
    reload: () => void run(false),
    refresh: () => void run(true),
    setData,
  };
}
