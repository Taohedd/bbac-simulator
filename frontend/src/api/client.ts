import axios, { AxiosError } from 'axios';
import { useStore } from '../store/useStore';
import {
  DashboardStats,
  DashboardTimeline,
  User,
  UserRole,
  UserRiskSummary,
  UserDetailResponse,
  AccessDecision,
  UserBaseline,
  PaginatedLogs,
  LogDetail,
  Policy,
  ActivePolicyResponse,
  SimulationStatus,
  ScenarioInfo,
} from '../types';

// Relative baseURL — requests go through the Vite dev server proxy
// configured in vite.config.ts ('/api' -> http://localhost:8000)
const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// ---------------------------------------------------------------------------
// Request interceptor — attaches JWT Bearer token to every API request.
// Reads token directly from Zustand store state (no React hook needed).
// ---------------------------------------------------------------------------
apiClient.interceptors.request.use(
  (config) => {
    const token = useStore.getState().authToken;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ---------------------------------------------------------------------------
// Response interceptor — unwraps FastAPI error bodies and auto-logouts on 401.
// ---------------------------------------------------------------------------
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    // Auto-logout when token is expired or invalid
    if (error.response?.status === 401) {
      useStore.getState().clearAuth();
    }
    // Unwrap FastAPI's { detail: string } error format into a plain Error
    // so every hook can catch a consistent Error instead of raw Axios errors.
    const detail = error.response?.data?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : error.message || 'An unexpected error occurred';
    return Promise.reject(new Error(message));
  }
);

// ---------------------------------------------------------------------------
// Payload interfaces
// ---------------------------------------------------------------------------

export interface LogQueryParams {
  user_id?: string;
  action?: string;
  min_score?: number;
  max_score?: number;
  start_time?: string;
  end_time?: string;
  limit?: number;
  offset?: number;
}

// Matches schemas/user.py UserCreate — email is required, not optional
export interface CreateUserPayload {
  username: string;
  email: string;
  role: UserRole;
  is_active?: boolean;
}

export interface UpdateUserPayload {
  username?: string;
  email?: string;
  role?: UserRole;
  is_active?: boolean;
}

// Matches schemas/policy.py PolicyCreate — two-threshold model only.
// There is no rules-engine concept on the backend.
export interface CreatePolicyPayload {
  name: string;
  low_threshold: number;
  high_threshold: number;
  is_active: boolean;
}

export type UpdatePolicyPayload = Partial<CreatePolicyPayload>;

// ---------------------------------------------------------------------------
// Namespaced API methods
// ---------------------------------------------------------------------------

export const api = {
  dashboard: {
    getStats: async (): Promise<DashboardStats> => {
      const response = await apiClient.get<DashboardStats>('/dashboard/stats');
      return response.data;
    },
    getTimeline: async (): Promise<DashboardTimeline> => {
      const response = await apiClient.get<DashboardTimeline>('/dashboard/timeline');
      return response.data;
    },
  },

  users: {
    getAll: async (): Promise<User[]> => {
      const response = await apiClient.get<User[]>('/users/');
      return response.data;
    },
    getSummary: async (): Promise<UserRiskSummary[]> => {
      const response = await apiClient.get<UserRiskSummary[]>('/users/summary');
      return response.data;
    },
    getById: async (id: string): Promise<UserDetailResponse> => {
      const response = await apiClient.get<UserDetailResponse>(`/users/${id}`);
      return response.data;
    },
    getDecisions: async (id: string, limit = 20): Promise<AccessDecision[]> => {
      const response = await apiClient.get<AccessDecision[]>(
        `/users/${id}/decisions`,
        { params: { limit } }
      );
      return response.data;
    },
    getBaseline: async (id: string): Promise<UserBaseline> => {
      const response = await apiClient.get<UserBaseline>(`/users/${id}/baseline`);
      return response.data;
    },
    create: async (payload: CreateUserPayload): Promise<User> => {
      const response = await apiClient.post<User>('/users/', payload);
      return response.data;
    },
    update: async (id: string, payload: UpdateUserPayload): Promise<User> => {
      const response = await apiClient.patch<User>(`/users/${id}`, payload);
      return response.data;
    },
    delete: async (id: string): Promise<void> => {
      await apiClient.delete(`/users/${id}`);
    },
  },

  logs: {
    getLogs: async (params?: LogQueryParams): Promise<PaginatedLogs> => {
      const response = await apiClient.get<PaginatedLogs>('/logs/', { params });
      return response.data;
    },
    // Returns LogDetail — the distinct nested { log, user, analysis, enforcement }
    // shape from GET /logs/{id}/details, NOT the flat LogWithRiskResponse
    getDetails: async (id: string): Promise<LogDetail> => {
      const response = await apiClient.get<LogDetail>(`/logs/${id}/details`);
      return response.data;
    },
  },

  policies: {
    getAll: async (): Promise<Policy[]> => {
      const response = await apiClient.get<Policy[]>('/policies/');
      return response.data;
    },
    getActive: async (): Promise<ActivePolicyResponse> => {
      const response = await apiClient.get<ActivePolicyResponse>('/policies/active');
      return response.data;
    },
    create: async (payload: CreatePolicyPayload): Promise<Policy> => {
      const response = await apiClient.post<Policy>('/policies/', payload);
      return response.data;
    },
    update: async (id: string, payload: UpdatePolicyPayload): Promise<Policy> => {
      const response = await apiClient.patch<Policy>(`/policies/${id}`, payload);
      return response.data;
    },
    delete: async (id: string): Promise<void> => {
      await apiClient.delete(`/policies/${id}`);
    },
  },

  simulation: {
    getStatus: async (): Promise<SimulationStatus> => {
      const response = await apiClient.get<SimulationStatus>('/simulation/status');
      return response.data;
    },
    start: async (): Promise<void> => {
      await apiClient.post('/simulation/start');
    },
    stop: async (): Promise<void> => {
      await apiClient.post('/simulation/stop');
    },
    reset: async (): Promise<void> => {
      await apiClient.post('/simulation/reset');
    },
    getScenarios: async (): Promise<ScenarioInfo[]> => {
      const response = await apiClient.get<ScenarioInfo[]>('/simulation/scenarios');
      return response.data;
    },
    setScenario: async (scenarioId: string, injectRate?: number): Promise<void> => {
      await apiClient.post('/simulation/scenario/set', {
        scenario_id: scenarioId,
        inject_rate: injectRate,
      });
    },
    clearScenario: async (): Promise<void> => {
      await apiClient.post('/simulation/scenario/clear');
    },
    triggerOnce: async (scenarioId: string): Promise<void> => {
      await apiClient.post('/simulation/scenario/trigger-once', {
        scenario_id: scenarioId,
      });
    },
  },

  // User panel actions — called by the regular user role only
 userPanel: {
    triggerAction: async (
      action: string,
      resource?: string
    ) => {
      const response = await apiClient.post<{
        log_id: string;
        action: string;
        timestamp: string;
        message: string;
      }>('/user/trigger-action', { action, resource });
      return response.data;
    },

    getMyRiskScore: async () => {
      const response = await apiClient.get<{
        score: number | null;
        risk_level: string | null;
        decision: string | null;
        computed_at: string | null;
      }>('/user/my-risk-score');
      return response.data;
    },

    getMyRecentActivity: async () => {
      type ActivityEntry = {
        id: string;
        timestamp: string;
        action: string;
        resource_accessed: string | null;
        risk_score: number | null;
        decision: string;
      };
      const response = await apiClient.get<ActivityEntry[]>('/user/my-recent-activity');
      return response.data;
    },
  },
};