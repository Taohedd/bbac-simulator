import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { DashboardStats, DashboardTimeline } from '../types';

interface UseDashboardReturn {
  stats: DashboardStats | null;
  timeline: DashboardTimeline | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

const POLL_INTERVAL_MS = 10_000; // 10 seconds

export const useDashboard = (): UseDashboardReturn => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [timeline, setTimeline] = useState<DashboardTimeline | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async (showLoadingIndicator = true) => {
    if (showLoadingIndicator) {
      setIsLoading(true);
    }
    setError(null);

    try {
      // Use the namespaced api object from client.ts — NOT api.get() which
      // doesn't exist. The api export is a plain object, not an Axios instance.
      const [statsData, timelineData] = await Promise.all([
        api.dashboard.getStats(),
        api.dashboard.getTimeline(),
      ]);

      setStats(statsData);
      setTimeline(timelineData);
    } catch (err: unknown) {
      // Our api/client.ts interceptor already unwraps AxiosError into a plain
      // Error with a readable message, so we just handle Error here.
      const message =
        err instanceof Error ? err.message : 'Failed to fetch dashboard data';
      setError(message);
    } finally {
      // Always clear the loading state — unconditional so no timing edge-case
      // can leave isLoading stuck as true.
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial fetch with loading indicator
    void fetchDashboardData(true);

    // Background poll — no loading flash, just silently updates state
    const intervalId = setInterval(() => {
      void fetchDashboardData(false);
    }, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [fetchDashboardData]);

  return {
    stats,
    timeline,
    isLoading,
    error,
    refetch: () => fetchDashboardData(true),
  };
};