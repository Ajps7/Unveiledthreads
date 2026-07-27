import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { ApiError, onSessionExpired } from '../api/client';
import { auth } from '../api/endpoints';
import type { User } from '../api/types';

/**
 * Session state for the whole app.
 *
 * Because the session lives in httpOnly cookies the app cannot read, the only
 * honest way to answer "is this user signed in?" is to ask the server. We do
 * that once on boot, then keep the answer in memory. `status` distinguishes
 * "still checking" from "definitely signed out" so the navigator doesn't flash
 * the login screen at a user who is in fact signed in.
 */

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

interface AuthContextValue {
  status: AuthStatus;
  user: User | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name: string) => Promise<void>;
  signOut: () => Promise<void>;
  /** Re-fetch the current user, e.g. after a profile change. */
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<User | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const loadSession = useCallback(async () => {
    try {
      const me = await auth.me();
      if (!mounted.current) return;
      setUser(me);
      setStatus('authenticated');
    } catch (error) {
      if (!mounted.current) return;
      // A 401 here is the normal signed-out case, not an error worth showing.
      // Anything else (offline, 5xx) also lands here — the user simply starts
      // at the sign-in screen and can retry.
      setUser(null);
      setStatus('unauthenticated');
      if (error instanceof ApiError && !error.isAuthError) {
        console.warn('[auth] session check failed:', error.detail);
      }
    }
  }, []);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  // The API client fires this when a refresh attempt fails, so an expired
  // session drops us back to the sign-in screen instead of leaving dead UI.
  useEffect(
    () =>
      onSessionExpired(() => {
        if (!mounted.current) return;
        setUser(null);
        setStatus('unauthenticated');
      }),
    [],
  );

  const signIn = useCallback(async (email: string, password: string) => {
    const me = await auth.login(email.trim().toLowerCase(), password);
    setUser(me);
    setStatus('authenticated');
  }, []);

  const signUp = useCallback(async (email: string, password: string, name: string) => {
    const me = await auth.register(email.trim().toLowerCase(), password, name.trim());
    setUser(me);
    setStatus('authenticated');
  }, []);

  const signOut = useCallback(async () => {
    try {
      await auth.logout();
    } catch {
      // Even if the call fails the local session must end — the cookies are
      // either already gone or will expire. Never trap a user in a bad session.
    } finally {
      setUser(null);
      setStatus('unauthenticated');
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, signIn, signUp, signOut, refresh: loadSession }),
    [status, user, signIn, signUp, signOut, loadSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside an AuthProvider');
  return context;
}
