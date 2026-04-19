import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Set up axios interceptor for automatic token refresh
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        if (
          error.response?.status === 401 &&
          !originalRequest._retry &&
          !originalRequest.url.includes('/auth/refresh') &&
          !originalRequest.url.includes('/auth/login') &&
          !originalRequest.url.includes('/auth/me')
        ) {
          originalRequest._retry = true;
          try {
            await axios.post(`${API}/api/auth/refresh`, {}, { withCredentials: true });
            return axios(originalRequest);
          } catch (refreshError) {
            setUser(false);
            return Promise.reject(refreshError);
          }
        }
        return Promise.reject(error);
      }
    );
    return () => axios.interceptors.response.eject(interceptor);
  }, []);

  const checkAuth = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/api/auth/me`, { withCredentials: true });
      setUser(response.data);
    } catch (error) {
      // Access token may be expired — try refreshing
      if (error.response?.status === 401) {
        try {
          await axios.post(`${API}/api/auth/refresh`, {}, { withCredentials: true });
          const retryResponse = await axios.get(`${API}/api/auth/me`, { withCredentials: true });
          setUser(retryResponse.data);
        } catch (refreshError) {
          setUser(false);
        }
      } else {
        setUser(false);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    const response = await axios.post(`${API}/api/auth/login`, { email, password }, { withCredentials: true });
    setUser(response.data);
    return response.data;
  };

  const register = async (email, password, name) => {
    const response = await axios.post(`${API}/api/auth/register`, { email, password, name }, { withCredentials: true });
    setUser(response.data);
    return response.data;
  };

  const logout = async () => {
    await axios.post(`${API}/api/auth/logout`, {}, { withCredentials: true });
    setUser(false);
  };

  const refreshToken = async () => {
    try {
      await axios.post(`${API}/api/auth/refresh`, {}, { withCredentials: true });
      await checkAuth();
    } catch (error) {
      setUser(false);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshToken, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
