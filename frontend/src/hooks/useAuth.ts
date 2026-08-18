import { useState } from 'react';
import axios from 'axios';
import { apiClient } from '../api/client';
import { useStore, selectIsAuthenticated } from '../store/useStore';

export const useAuth = () => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Selectors — each subscribes only to what it needs
  const isAuthenticated = useStore(selectIsAuthenticated);
  const authRole       = useStore((state) => state.authRole);
  const authUsername   = useStore((state) => state.authUsername);

  // Actions
  const setAuth        = useStore((state) => state.setAuth);
  const clearAuth      = useStore((state) => state.clearAuth);
  const clearLiveEvents = useStore((state) => state.clearLiveEvents);

  const login = async (username: string, password: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      // OAuth2PasswordRequestForm requires application/x-www-form-urlencoded,
      // not JSON — use URLSearchParams to build the correct body format.
      // Uses apiClient so the request goes to the correct backend URL in
      // both local dev (Vite proxy) and production (VITE_API_URL).
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const response = await apiClient.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const {
        access_token,
        role,
        username: returnedUsername,
      } = response.data as { access_token: string; role: 'admin' | 'user'; username: string };

      setAuth(access_token, role, returnedUsername);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response) {
        setError(
          (err.response.data as { detail?: string })?.detail ||
            'Invalid username or password'
        );
      } else {
        setError('An unexpected error occurred during login');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      // Read token directly from store state — no subscription needed here
      const token = useStore.getState().authToken;
      if (token) {
        await apiClient.post(
          '/auth/logout',
          {},
          { headers: { Authorization: `Bearer ${token}` } }
        );
      }
    } catch (err: unknown) {
      // Always proceed with local logout even if the server call fails.
      // JWTs are stateless — clearing the local token is what matters.
      console.error('Server logout notification failed:', err);
    } finally {
      clearAuth();
      clearLiveEvents();
      setIsLoading(false);
    }
  };

  return {
    isAuthenticated,
    authRole,
    authUsername,
    isLoading,
    error,
    login,
    logout,
  };
};