import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { UserRiskSummary } from '../types';

interface UseUsersReturn {
  users: UserRiskSummary[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

const POLL_INTERVAL_MS = 5_000; // 5 seconds — risk scores update frequently

export const useUsers = (): UseUsersReturn => {
  const [users, setUsers] = useState<UserRiskSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true); // true avoids empty-state flash
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = useCallback(async (showLoadingIndicator = true) => {
    if (showLoadingIndicator) setIsLoading(true);
    setError(null);
    try {
      // Use the namespaced api object — api.get() does not exist
      const data = await api.users.getSummary();
      setUsers(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch users');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial fetch with loading indicator
    void fetchUsers(true);

    // Background poll — silent update without flashing loading state
    const intervalId = setInterval(() => {
      void fetchUsers(false);
    }, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [fetchUsers]);

  return {
    users,
    isLoading,
    error,
    refetch: () => fetchUsers(true),
  };
};