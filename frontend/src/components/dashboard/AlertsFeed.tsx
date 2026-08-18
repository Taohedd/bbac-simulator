import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useStore, selectRecentAlerts } from '../../store/useStore';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge, type BadgeVariant } from '../ui/Badge';
import { RiskBadge } from '../ui/RiskBadge';
import { Decision } from '../../types';

// Maps Decision enum values to Badge variant strings.
// A lookup map is safer than a ternary chain — any future new decision type
// causes a TypeScript error here rather than silently falling through.
const DECISION_VARIANT: Record<Decision, BadgeVariant> = {
  ALLOW:         'allow',
  MFA_CHALLENGE: 'mfa',
  BLOCK:         'block',
};

export const AlertsFeed: React.FC = () => {
  // Use the pre-built selector from useStore — filters MFA + BLOCK events,
  // caps at MAX_RECENT_ALERTS (20), so filtering logic lives in exactly one place.
  const alerts = useStore(selectRecentAlerts);

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-risk-high">
          <AlertTriangle className="h-5 w-5" />
          Recent Security Alerts
          {alerts.length > 0 && (
            <span className="ml-auto text-xs font-mono text-textMuted font-normal">
              {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
            </span>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto pr-2">
        {alerts.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-textMuted">
            No recent alerts detected.
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.log_id}
                className="flex flex-col gap-2 rounded-md border border-border bg-background p-3"
              >
                {/* Timestamp + badges row */}
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-textMuted">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </span>
                  <div className="flex gap-2">
                    <RiskBadge score={alert.risk_score} />
                    <Badge variant={DECISION_VARIANT[alert.decision]}>
                      {alert.decision}
                    </Badge>
                  </div>
                </div>

                {/* Action + user row */}
                <div className="text-sm">
                  <span className="font-semibold text-textMain">{alert.action}</span>
                  <span className="text-textMuted"> by </span>
                  <span
                    className="font-mono text-xs text-textMain"
                    title={alert.user_id}
                  >
                    {alert.user_id.split('-')[0]}…
                  </span>
                </div>

                {/* Reason — null-safe with fallback */}
                <div className="text-xs text-textMuted">
                  <span className="font-medium text-textMain">Reason: </span>
                  {alert.reason ?? 'No reason provided'}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};