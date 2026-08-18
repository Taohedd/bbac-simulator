import { useState, useCallback } from 'react';
import { api } from '../api/client';
import { LogWithRiskResponse, PaginatedLogs } from '../types';
import { LogQueryParams } from '../api/client';

interface UseLogsReturn {
  logs: LogWithRiskResponse[];
  total: number;
  isLoading: boolean;
  error: string | null;
  refetch: (params?: LogQueryParams) => Promise<void>;
}

export const useLogs = (): UseLogsReturn => {
  const [logs, setLogs] = useState<LogWithRiskResponse[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async (params: LogQueryParams = {}) => {
    setIsLoading(true);
    setError(null);
    try {
      // Strip empty string values so they aren't sent as ?user_id=&action=
      const cleanParams = Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== '' && v != null)
      ) as LogQueryParams;

      // Use the namespaced api object — api.get() does not exist
      const data: PaginatedLogs = await api.logs.getLogs(cleanParams);
      setLogs(data.items);
      setTotal(data.total);
    } catch (err: unknown) {
      // Interceptor in api/client.ts already converts AxiosError → plain Error
      setError(err instanceof Error ? err.message : 'Failed to fetch logs');
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    logs,
    total,
    isLoading,
    error,
    refetch: fetchLogs,
  };
};