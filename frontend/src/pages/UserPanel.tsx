import React, { useEffect, useState, useCallback } from 'react';
import {
  LogOut, Activity, Shield, AlertTriangle,
  Loader2, CheckCircle, Zap,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { api } from '../api/client';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Badge, type BadgeVariant } from '../components/ui/Badge';
import { RiskBadge } from '../components/ui/RiskBadge';
import { RiskGauge } from '../components/dashboard/RiskGauge';
import { Decision } from '../types';

// ---------------------------------------------------------------------------
// Types — match the real api.userPanel response shapes from client.ts
// ---------------------------------------------------------------------------
interface RiskScoreData {
  score: number | null;
  risk_level: string | null;
  decision: string | null;
  computed_at: string | null;
}

interface ActivityEntry {
  id: string;
  timestamp: string;
  action: string;
  resource_accessed: string | null;  // matches api response field name exactly
  risk_score: number | null;
  decision: string;
}

type ActionCategory = 'normal' | 'suspicious' | 'dangerous';

interface ActionDef {
  id: string;
  label: string;
  category: ActionCategory;
}

// ---------------------------------------------------------------------------
// Action definitions
// ---------------------------------------------------------------------------
const ACTIONS: ActionDef[] = [
  { id: 'LOGIN',                label: 'Login',              category: 'normal'     },
  { id: 'FILE_READ',            label: 'Read File',          category: 'normal'     },
  { id: 'FILE_WRITE',           label: 'Write File',         category: 'normal'     },
  { id: 'DB_QUERY',             label: 'DB Query',           category: 'normal'     },
  { id: 'EMAIL_SEND',           label: 'Send Email',         category: 'normal'     },
  { id: 'REPORT_VIEW',          label: 'View Report',        category: 'normal'     },
  { id: 'PASSWORD_CHANGE',      label: 'Change Password',    category: 'suspicious' },
  { id: 'API_CALL',             label: 'API Call',           category: 'suspicious' },
  { id: 'BULK_DOWNLOAD',        label: 'Bulk Download',      category: 'suspicious' },
  { id: 'CONFIG_CHANGE',        label: 'Change Config',      category: 'suspicious' },
  { id: 'DB_EXPORT',            label: 'Export DB',          category: 'dangerous'  },
  { id: 'DATA_EXFIL',           label: 'Data Exfiltration',  category: 'dangerous'  },
  { id: 'LATERAL_MOVE',         label: 'Lateral Movement',   category: 'dangerous'  },
  { id: 'PRIVILEGE_ESCALATION', label: 'Escalate Privileges',category: 'dangerous'  },
];

const CATEGORY_CLASSES: Record<ActionCategory, string> = {
  normal:     'bg-risk-low/10 text-risk-low border-risk-low/20 hover:bg-risk-low/20',
  suspicious: 'bg-risk-medium/10 text-risk-medium border-risk-medium/20 hover:bg-risk-medium/20',
  dangerous:  'bg-risk-high/10 text-risk-high border-risk-high/20 hover:bg-risk-high/20',
};

// Typed lookup — avoids ternary chains, consistent with all other components
const DECISION_VARIANT: Record<Decision, BadgeVariant> = {
  ALLOW:         'allow',
  MFA_CHALLENGE: 'mfa',
  BLOCK:         'block',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export const UserPanel: React.FC = () => {
  const { authUsername, logout } = useAuth();

  const [scoreData, setScoreData] = useState<RiskScoreData | null>(null);
  const [recentActivity, setRecentActivity] = useState<ActivityEntry[]>([]);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [toast, setToast] = useState<{
    message: string;
    type: 'success' | 'error';
  } | null>(null);

  const fetchData = useCallback(async () => {
    try {
      // api.userPanel is defined in client.ts — no any cast needed
      const [score, activity] = await Promise.all([
        api.userPanel.getMyRiskScore(),
        api.userPanel.getMyRecentActivity(),
      ]);
      setScoreData(score);
      setRecentActivity(activity);
    } catch (err: unknown) {
      console.error('Failed to fetch user panel data:', err);
    }
  }, []);

  useEffect(() => {
    void fetchData();
    const interval = setInterval(() => void fetchData(), 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const showToast = useCallback(
    (message: string, type: 'success' | 'error') => {
      setToast({ message, type });
      setTimeout(() => setToast(null), 3000);
    },
    []
  );

  const handleTriggerAction = async (actionId: string) => {
    setLoadingAction(actionId);
    try {
      await api.userPanel.triggerAction(actionId);
      showToast(`Action '${actionId}' triggered — scoring in progress...`, 'success');
      // Brief delay then refresh so the ML pipeline has time to score
      setTimeout(() => void fetchData(), 1500);
    } catch (err: unknown) {
      showToast(
        err instanceof Error ? err.message : `Failed to trigger ${actionId}`,
        'error'
      );
    } finally {
      setLoadingAction(null);
    }
  };

  // Safe score for RiskGauge — null becomes 0
  const safeScore = scoreData?.score ?? 0;
  const safeDecision = scoreData?.decision as Decision | null;

  return (
    <div className="min-h-screen bg-background text-textMain p-6 space-y-6">

      {/* Toast notification */}
      {toast && (
        <div
          className={`fixed top-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-md border shadow-lg ${
            toast.type === 'success'
              ? 'bg-risk-low/10 border-risk-low/20 text-risk-low'
              : 'bg-risk-high/10 border-risk-high/20 text-risk-high'
          }`}
        >
          {toast.type === 'success' ? (
            <CheckCircle className="h-4 w-4 flex-shrink-0" />
          ) : (
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          )}
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      )}

      {/* Header */}
      <header className="flex items-center justify-between bg-surface border border-border rounded-card p-4 shadow-card">
        <div className="flex items-center gap-3">
          <div className="bg-risk-low/10 p-2 rounded-full border border-risk-low/20">
            <Shield className="h-5 w-5 text-risk-low" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight">
              Welcome, <span className="text-risk-low">{authUsername}</span>
            </h1>
            <p className="text-xs text-textMuted">BBAC User Simulation Panel</p>
          </div>
        </div>
        <button
          onClick={() => void logout()}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-textMuted hover:text-textMain bg-surfaceHover hover:bg-border rounded-md border border-border transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </header>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left — Risk score */}
        <div className="lg:col-span-1">
          <Card className="h-full flex flex-col">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Activity className="h-4 w-4 text-textMuted" />
                Your Current Risk Score
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col items-center justify-center py-4 gap-6">
              {scoreData !== null ? (
                <>
                  <div className="w-full max-w-[200px]">
                    <RiskGauge
                      score={safeScore}
                      title="Risk Score"
                      subtitle="Live"
                    />
                  </div>
                  <div className="text-center space-y-2">
                    <p className="text-xs text-textMuted uppercase tracking-wider font-medium">
                      Current Access Status
                    </p>
                    {safeDecision && safeDecision in DECISION_VARIANT ? (
                      <Badge
                        variant={DECISION_VARIANT[safeDecision]}
                        className="text-sm px-4 py-1"
                      >
                        {safeDecision}
                      </Badge>
                    ) : (
                      <Badge variant="default" className="text-sm px-4 py-1">
                        PENDING
                      </Badge>
                    )}
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center gap-3 text-textMuted">
                  <Loader2 className="h-8 w-8 animate-spin" />
                  <p className="text-sm">Loading score...</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right — Action buttons */}
        <div className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Zap className="h-4 w-4 text-textMuted" />
                Trigger an Action
              </CardTitle>
              <p className="text-xs text-textMuted mt-1">
                Click any action to simulate it. The BBAC engine scores your
                behaviour in real time — dangerous actions trigger alerts on
                the admin dashboard.
              </p>
              <div className="flex gap-4 mt-3 text-xs text-textMuted">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-risk-low inline-block" />
                  Normal
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-risk-medium inline-block" />
                  Suspicious
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-risk-high inline-block" />
                  Dangerous
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {ACTIONS.map((action) => (
                  <button
                    key={action.id}
                    onClick={() => void handleTriggerAction(action.id)}
                    disabled={loadingAction !== null}
                    className={`relative flex flex-col items-center justify-center p-3 h-24 rounded-md border transition-all text-center disabled:opacity-50 disabled:cursor-not-allowed ${CATEGORY_CLASSES[action.category]}`}
                  >
                    {loadingAction === action.id ? (
                      <Loader2 className="h-5 w-5 animate-spin mb-1.5" />
                    ) : (
                      <Activity className="h-5 w-5 mb-1.5 opacity-70" />
                    )}
                    <span className="text-xs font-semibold leading-tight">
                      {action.label}
                    </span>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Recent activity table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Recent Activity</CardTitle>
          <p className="text-xs text-textMuted mt-1">
            Your last 10 actions — updates every 3 seconds
          </p>
        </CardHeader>
        <CardContent>
          {recentActivity.length === 0 ? (
            <div className="text-center py-8 text-textMuted text-sm">
              No activity yet. Click an action above to get started.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-textMuted uppercase bg-surfaceHover/50">
                  <tr>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">Action</th>
                    <th className="px-4 py-3">Resource</th>
                    <th className="px-4 py-3">Risk Score</th>
                    <th className="px-4 py-3">Decision</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {recentActivity.map((entry) => (
                    <tr
                      key={entry.id}
                      className="hover:bg-surfaceHover/30 transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-xs text-textMuted">
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="px-4 py-3 font-medium text-textMain">
                        {entry.action}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-textMuted">
                        {/* Field is resource_accessed from api — not resource */}
                        {entry.resource_accessed ?? '—'}
                      </td>
                      <td className="px-4 py-3">
                        {entry.risk_score != null ? (
                          <RiskBadge score={entry.risk_score} showScore />
                        ) : (
                          <span className="text-xs text-textMuted italic">
                            Pending
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {entry.decision in DECISION_VARIANT ? (
                          <Badge
                            variant={
                              DECISION_VARIANT[entry.decision as Decision]
                            }
                          >
                            {entry.decision}
                          </Badge>
                        ) : (
                          <Badge variant="default">{entry.decision}</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};