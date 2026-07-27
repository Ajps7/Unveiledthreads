import { useCallback, useEffect, useRef, useState } from 'react';
import { AppState } from 'react-native';
import { notifications } from '../api/endpoints';
import type { PollResponse } from '../api/types';

/**
 * Unread counts for the tab badges.
 *
 * The web app polls every 10s. On a phone that is wasteful — it burns battery
 * and radio for a badge nobody is looking at — so this polls every 45s while
 * the app is in the foreground and stops entirely when backgrounded, then
 * refreshes immediately on resume. Push notifications are the right long-term
 * answer (already on the backlog in memory/PRD.md).
 */
const POLL_INTERVAL_MS = 45_000;

export function useUnreadBadges(enabled: boolean) {
  const [counts, setCounts] = useState<PollResponse | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const poll = useCallback(async () => {
    if (!enabled) return;
    try {
      const result = await notifications.poll();
      if (mounted.current) setCounts(result);
    } catch {
      // A failed badge poll is not worth surfacing — keep the last known
      // counts and try again on the next tick.
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      setCounts(null);
      return;
    }

    void poll();
    timer.current = setInterval(() => void poll(), POLL_INTERVAL_MS);

    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        void poll();
        if (!timer.current) timer.current = setInterval(() => void poll(), POLL_INTERVAL_MS);
      } else if (timer.current) {
        clearInterval(timer.current);
        timer.current = null;
      }
    });

    return () => {
      subscription.remove();
      if (timer.current) {
        clearInterval(timer.current);
        timer.current = null;
      }
    };
  }, [enabled, poll]);

  return { counts, refresh: poll };
}
