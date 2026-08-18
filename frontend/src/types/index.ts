// ============================================================
// Shared TypeScript types for the BBAC Simulator frontend.
// Every interface here is mapped 1:1 against the actual FastAPI
// Pydantic response schemas — not assumed or invented field names.
// ============================================================

export type Decision = 'ALLOW' | 'MFA_CHALLENGE' | 'BLOCK';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';
export type UserRole = 'admin' | 'analyst' | 'employee' | 'contractor' | 'viewer';

// ------------------------------------------------------------
// Dashboard
// ------------------------------------------------------------
export interface DecisionBreakdown {
  ALLOW: number;
  MFA_CHALLENGE: number;
  BLOCK: number;
}

export interface DashboardStats {
  total_active_accounts: number;
  users_active_24h: number;
  events_24h: number;
  decisions_24h: DecisionBreakdown;
  anomaly_rate_percent: number;
  average_risk_score_24h: number;
  connected_dashboard_clients: number;
}

export interface TimelineBucket {
  time: string;
  ALLOW: number;
  MFA_CHALLENGE: number;
  BLOCK: number;
  avg_risk_score: number;
}

export interface DashboardTimeline {
  timeline: TimelineBucket[];
}

// ------------------------------------------------------------
// Users
// Matches schemas/user.py: UserResponse, UserBaselineResponse,
// UserDetailResponse (flat — NOT a nested { user, baseline } wrapper)
// ------------------------------------------------------------
export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface UserBaseline {
  id: string;
  user_id: string;
  avg_login_hour: number | null;
  common_subnet: string | null;
  common_device: string | null;
  typical_actions_json: Record<string, number> | null;
  updated_at: string;
}

// UserDetailResponse extends User directly — baseline is the ONLY extra field.
// GET /api/users/{id} returns this exact flat shape.
export interface UserDetailResponse extends User {
  baseline: UserBaseline | null;
}

export interface UserRiskSummary {
  user_id: string;
  username: string;
  role: UserRole;
  is_active: boolean;
  latest_score: number | null;
  latest_decision: Decision | null;
  risk_level: RiskLevel | null;
  last_seen: string | null;
}

// ------------------------------------------------------------
// Risk Scores & Access Decisions
// Matches schemas/risk.py
// ------------------------------------------------------------
export interface RiskScore {
  id: string;
  user_id: string;
  log_id: string;
  score: number;
  features_json: Record<string, number> | null;
  computed_at: string;
  risk_level: RiskLevel | null;
}

// Matches AccessDecisionResponse exactly — note: decided_at, not timestamp;
// risk_score_id is present; there is no embedded "action" or "risk_score" field.
export interface AccessDecision {
  id: string;
  user_id: string;
  risk_score_id: string;
  decision: Decision;
  reason: string | null;
  decided_at: string;
}

// ------------------------------------------------------------
// Activity Logs
// Matches schemas/log.py: LogWithRiskResponse, PaginatedLogResponse
// ------------------------------------------------------------
export interface LogWithRiskResponse {
  id: string;
  user_id: string;
  timestamp: string;
  action: string;
  ip_address: string | null;
  location: string | null;
  device_fingerprint: string | null;
  resource_accessed: string | null;
  session_id: string | null;
  risk_score: number | null;
  risk_score_id: string | null;
  decision: Decision | null;
}

export interface PaginatedLogs {
  items: LogWithRiskResponse[];
  total: number;
  limit: number;
  offset: number;
}

// Matches the GET /logs/{id}/details response — a separate, richer shape
// that includes the raw ML feature vector. NOT the same as LogWithRiskResponse.
export interface LogDetail {
  log: {
    id: string;
    timestamp: string;
    action: string;
    ip_address: string | null;
    location: string | null;
    device_fingerprint: string | null;
    resource_accessed: string | null;
    session_id: string | null;
  };
  user: {
    id: string;
    username: string;
  };
  analysis: {
    risk_score_id: string | null;
    risk_score: number | null;
    features: Record<string, number> | null;
    computed_at: string | null;
  };
  enforcement: {
    decision: Decision | null;
    reason: string | null;
    decided_at: string | null;
  };
}

// ------------------------------------------------------------
// Policies
// Matches schemas/policy.py — a simple two-threshold model.
// There is NO rules-engine concept (no PolicyRule, no conditions/priority)
// anywhere in the actual backend.
// ------------------------------------------------------------
export interface Policy {
  id: string;
  name: string;
  low_threshold: number;
  high_threshold: number;
  is_active: boolean;
  created_at: string;
}

// Matches GET /policies/active — a single lightweight policy object,
// NOT an array wrapper.
export interface ActivePolicyResponse {
  id: string;
  name: string;
  low_threshold: number;
  high_threshold: number;
}

export interface PolicyCreateInput {
  name: string;
  low_threshold: number;
  high_threshold: number;
  is_active: boolean;
}

export type PolicyUpdateInput = Partial<PolicyCreateInput>;

// ------------------------------------------------------------
// Simulation
// Matches generator.get_status() and analytics_engine.get_status() exactly
// ------------------------------------------------------------
export interface ModelStatus {
  is_trained: boolean;
  training_sample_count: number;
  score_range: { min: number; max: number };
  contamination_rate: number;
  n_estimators: number;
  feature_count: number;
  features: string[];
}

export interface SimulationGeneratorStatus {
  is_running: boolean;
  active_scenario: string | null;
  anomaly_inject_rate: number;
  pending_trigger: string | null;
  total_logs_generated: number;
  total_anomalies_injected: number;
  interval_ms: number;
}

export interface SimulationAnalyticsStatus {
  is_running: boolean;
  total_logs_processed: number;
  total_alerts_raised: number;
  model_status: ModelStatus;
}

export interface SimulationStatus {
  generator: SimulationGeneratorStatus;
  analytics: SimulationAnalyticsStatus;
}

export interface ScenarioInfo {
  id: string;
  name: string;
  description: string;
  type: string;
}

// ------------------------------------------------------------
// WebSocket
// Matches the exact "risk_event" payload built in modules/analytics/engine.py
// ------------------------------------------------------------
export interface RiskEvent {
  type: 'risk_event';
  log_id: string;
  user_id: string;
  action: string;
  timestamp: string;
  risk_score: number;
  decision: Decision;
  reason: string | null;
  features: Record<string, number>;
}