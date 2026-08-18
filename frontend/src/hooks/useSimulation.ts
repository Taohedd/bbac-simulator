import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { SimulationStatus, ScenarioInfo } from '../types';
import { useStore } from '../store/useStore';

interface UseSimulationReturn {
  isRunning: boolean;
  status: SimulationStatus | null;
  scenarios: ScenarioInfo[];
  activeScenarioId: string | null;
  isLoading: boolean;
  error: string | null;
  startSimulation: () => Promise<void>;
  stopSimulation: () => Promise<void>;
  resetSimulation: () => Promise<void>;
  setScenario: (scenarioId: string, injectRate: number) => Promise<void>;
  clearScenario: () => Promise<void>;
  triggerScenarioOnce: (scenarioId: string) => Promise<void>;
  refetchStatus: () => Promise<void>;
}

const POLL_INTERVAL_MS = 5_000;

export const useSimulation = (): UseSimulationReturn => {
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep Zustand store in sync so Sidebar shows live running indicator
  const setSimulationRunning = useStore((state) => state.setSimulationRunning);

  const fetchStatus = useCallback(async () => {
    try {
      // Use namespaced api — api.get() does not exist
      const data = await api.simulation.getStatus();
      setStatus(data);
      // Sync Zustand store — both generator AND analytics must be running
      setSimulationRunning(
        data.generator.is_running && data.analytics.is_running
      );
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    }
  }, [setSimulationRunning]);

  const fetchScenarios = useCallback(async () => {
    try {
      const data = await api.simulation.getScenarios();
      setScenarios(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch scenarios');
    }
  }, []);

  // Initial fetch + polling — hook manages its own lifecycle
  useEffect(() => {
    void fetchStatus();
    void fetchScenarios();

    const intervalId = setInterval(() => {
      void fetchStatus();
    }, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [fetchStatus, fetchScenarios]);

  // Helper — wraps a mutation with loading state and re-syncs status
  const withLoading = useCallback(
    async (action: () => Promise<void>): Promise<void> => {
      setIsLoading(true);
      setError(null);
      try {
        await action();
        await fetchStatus();
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Action failed';
        setError(message);
        throw new Error(message); // re-throw so SimulationControls can catch it
      } finally {
        setIsLoading(false);
      }
    },
    [fetchStatus]
  );

  const startSimulation = useCallback(
    () => withLoading(() => api.simulation.start()),
    [withLoading]
  );

  const stopSimulation = useCallback(
    () => withLoading(() => api.simulation.stop()),
    [withLoading]
  );

  const resetSimulation = useCallback(
    () => withLoading(() => api.simulation.reset()),
    [withLoading]
  );

  const setScenario = useCallback(
    (scenarioId: string, injectRate: number) =>
      withLoading(() => api.simulation.setScenario(scenarioId, injectRate)),
    [withLoading]
  );

  const clearScenario = useCallback(
    () => withLoading(() => api.simulation.clearScenario()),
    [withLoading]
  );

  const triggerScenarioOnce = useCallback(
    (scenarioId: string) =>
      withLoading(() => api.simulation.triggerOnce(scenarioId)),
    [withLoading]
  );

  return {
    isRunning: status?.generator.is_running ?? false,
    status,
    scenarios,
    activeScenarioId: status?.generator.active_scenario ?? null,
    isLoading,
    error,
    startSimulation,
    stopSimulation,
    resetSimulation,
    setScenario,
    clearScenario,
    triggerScenarioOnce,
    refetchStatus: fetchStatus,
  };
};