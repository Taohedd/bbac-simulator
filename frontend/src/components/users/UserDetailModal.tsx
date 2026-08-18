import React, { useEffect, useState, useCallback } from 'react';
import { X, User, Monitor, Clock, Shield, Activity, AlertCircle } from 'lucide-react';
import { api } from '../../api/client';
import { Badge, type BadgeVariant } from '../ui/Badge';
import { UserDetailResponse, AccessDecision, Decision } from '../../types';

interface UserDetailModalProps {
  userId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

// Typed lookup — same pattern as UserTable and AlertsFeed
const DECISION_VARIANT: Record<Decision, BadgeVariant> = {
  ALLOW:         'allow',
  MFA_CHALLENGE: 'mfa',
  BLOCK:         'block',
};

const formatDate = (isoString: string | null): string => {
  if (!isoString) return '—';
  return new Intl.DateTimeFormat('en-US', {
    month:  'short',
    day:    '2-digit',
    hour:   '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(isoString));
};

export const UserDetailModal: React.FC<UserDetailModalProps> = ({
  userId,
  isOpen,
  onClose,
}) => {
  const [user, setUser] = useState<UserDetailResponse | null>(null);
  const [decisions, setDecisions] = useState<AccessDecision[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!userId) return;
    setIsLoading(true);
    setError(null);
    try {
      // Use the correct namespaced api methods from client.ts
      const [userData, decisionsData] = await Promise.all([
        api.users.getById(userId),
        api.users.getDecisions(userId),
      ]);
      setUser(userData);
      setDecisions(decisionsData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load user details');
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (isOpen && userId) {
      void fetchData();
    } else {
      // Reset state when modal closes so stale data doesn't flash on next open
      setUser(null);
      setDecisions([]);
      setError(null);
    }
  }, [isOpen, userId, fetchData]);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-surface border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-surfaceHover rounded-lg">
              <User className="w-5 h-5 text-textMuted" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-textMain">User Details</h2>
              <p className="text-xs text-textMuted font-mono mt-0.5">{userId}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-2 text-textMuted hover:text-textMain hover:bg-surfaceHover rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">

          {isLoading && (
            <div className="flex flex-col items-center justify-center h-64 space-y-4">
              <div className="w-8 h-8 border-4 border-border border-t-risk-low rounded-full animate-spin" />
              <p className="text-textMuted text-sm">Loading user profile...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center h-64 space-y-3 text-decision-block bg-decision-block/10 rounded-lg border border-decision-block/20 p-6">
              <AlertCircle className="w-10 h-10" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          {!isLoading && !error && user && (
            <div className="space-y-8">

              {/* Profile + Baseline grid */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Profile */}
                <div className="bg-background border border-border rounded-lg p-5 space-y-4">
                  <h3 className="text-xs font-medium text-textMuted uppercase tracking-wider flex items-center gap-2">
                    <Shield className="w-4 h-4" /> Profile
                  </h3>
                  <div>
                    <p className="text-xs text-textMuted mb-1">Username</p>
                    <p className="text-base font-medium text-textMain">{user.username}</p>
                  </div>
                  <div>
                    <p className="text-xs text-textMuted mb-1">Email</p>
                    <p className="text-sm text-textMain font-mono">{user.email}</p>
                  </div>
                  <div>
                    <p className="text-xs text-textMuted mb-1">Role</p>
                    <Badge variant="default" className="capitalize">
                      {user.role.toLowerCase()}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-xs text-textMuted mb-1">Status</p>
                    <div className="flex items-center space-x-2">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          user.is_active ? 'bg-risk-low' : 'bg-border'
                        }`}
                      />
                      <span className="text-sm text-textMuted">
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-textMuted mb-1">Created</p>
                    <p className="text-xs text-textMuted font-mono">
                      {formatDate(user.created_at)}
                    </p>
                  </div>
                </div>

                {/* Behavioral Baseline — uses real field names from UserBaseline in types/index.ts */}
                <div className="lg:col-span-2 bg-background border border-border rounded-lg p-5">
                  <h3 className="text-xs font-medium text-textMuted uppercase tracking-wider flex items-center gap-2 mb-4">
                    <Activity className="w-4 h-4" /> Behavioral Baseline
                  </h3>

                  {user.baseline ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">

                      <div>
                        <div className="flex items-center gap-2 text-textMuted mb-2">
                          <Clock className="w-4 h-4" />
                          <span className="text-sm font-medium text-textMain">Avg Login Hour</span>
                        </div>
                        <p className="text-sm text-textMuted font-mono">
                          {user.baseline.avg_login_hour != null
                            ? `${user.baseline.avg_login_hour.toFixed(1)}h (24h clock)`
                            : <span className="italic">No data</span>}
                        </p>
                      </div>

                      <div>
                        <div className="flex items-center gap-2 text-textMuted mb-2">
                          <Monitor className="w-4 h-4" />
                          <span className="text-sm font-medium text-textMain">Common Device</span>
                        </div>
                        <p className="text-sm text-textMuted font-mono truncate">
                          {user.baseline.common_device ?? <span className="italic">No data</span>}
                        </p>
                      </div>

                      <div>
                        <p className="text-sm font-medium text-textMain mb-2">Common Subnet</p>
                        <p className="text-sm text-textMuted font-mono">
                          {user.baseline.common_subnet ?? <span className="italic">No data</span>}
                        </p>
                      </div>

                      <div>
                        <p className="text-sm font-medium text-textMain mb-2">Typical Actions</p>
                        {user.baseline.typical_actions_json ? (
                          <div className="flex flex-wrap gap-1.5">
                            {Object.entries(user.baseline.typical_actions_json)
                              .sort(([, a], [, b]) => b - a)
                              .slice(0, 5)
                              .map(([action, freq]) => (
                                <span
                                  key={action}
                                  className="px-2 py-0.5 bg-surfaceHover text-textMuted text-xs rounded border border-border font-mono"
                                  title={`${(freq * 100).toFixed(1)}% of activity`}
                                >
                                  {action}
                                </span>
                              ))}
                          </div>
                        ) : (
                          <span className="text-textMuted italic text-sm">No data</span>
                        )}
                      </div>

                      <div className="sm:col-span-2">
                        <p className="text-xs text-textMuted">
                          Last updated:{' '}
                          <span className="font-mono">{formatDate(user.baseline.updated_at)}</span>
                        </p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-textMuted text-sm italic">
                      Baseline not yet computed — user needs at least 50 activity logs.
                    </p>
                  )}
                </div>
              </div>

              {/* Recent Decisions — uses real AccessDecision fields: decided_at, decision, reason */}
              <div>
                <h3 className="text-xs font-medium text-textMuted uppercase tracking-wider mb-4">
                  Recent Access Decisions
                </h3>
                <div className="border border-border rounded-lg overflow-hidden bg-background">
                  {decisions.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-surface text-textMuted border-b border-border">
                          <tr>
                            <th className="px-4 py-3 font-medium">Decided At</th>
                            <th className="px-4 py-3 font-medium">Decision</th>
                            <th className="px-4 py-3 font-medium">Reason</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/50">
                          {decisions.map((dec) => (
                            <tr key={dec.id} className="hover:bg-surfaceHover/30 transition-colors">
                              <td className="px-4 py-3 text-textMuted font-mono text-xs">
                                {formatDate(dec.decided_at)}
                              </td>
                              <td className="px-4 py-3">
                                <Badge variant={DECISION_VARIANT[dec.decision]}>
                                  {dec.decision}
                                </Badge>
                              </td>
                              <td
                                className="px-4 py-3 text-textMuted text-xs truncate max-w-xs"
                                title={dec.reason ?? undefined}
                              >
                                {dec.reason ?? '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-8 text-center text-textMuted text-sm">
                      No recent access decisions found for this user.
                    </div>
                  )}
                </div>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
};