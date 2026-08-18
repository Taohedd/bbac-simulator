import React from 'react';
import { ChevronRight } from 'lucide-react';
import { Badge, type BadgeVariant } from '../ui/Badge';
import { RiskBadge } from '../ui/RiskBadge';
import { LogWithRiskResponse, Decision } from '../../types';

interface LogEntryProps {
  log: LogWithRiskResponse;
  onClick?: (logId: string) => void;
}

// Typed lookup — consistent with every other component using Decision variants
const DECISION_VARIANT: Record<Decision, BadgeVariant> = {
  ALLOW:         'allow',
  MFA_CHALLENGE: 'mfa',
  BLOCK:         'block',
};

const formatTime = (isoString: string): string => {
  if (!isoString) return '--:--:--';
  const date = new Date(isoString);
  const time = date.toLocaleTimeString('en-US', {
    hour12:  false,
    hour:    '2-digit',
    minute:  '2-digit',
    second:  '2-digit',
  });
  const ms = date.getMilliseconds().toString().padStart(3, '0');
  return `${time}.${ms}`;
};

export const LogEntry: React.FC<LogEntryProps> = ({ log, onClick }) => {
  // Use log.id, not log.log_id — LogWithRiskResponse uses id (not log_id,
  // which is the field name on the WebSocket RiskEvent type).
  const handleClick = () => onClick?.(log.id);

  const shortUserId = log.user_id
    ? `${log.user_id.substring(0, 8)}…`
    : 'Unknown';

  return (
    <div
      onClick={handleClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && handleClick() : undefined}
      className={`flex items-center gap-4 p-3 border-b border-border/50 bg-surface/50 hover:bg-surfaceHover/80 transition-colors group ${
        onClick ? 'cursor-pointer' : ''
      }`}
    >
      {/* Timestamp */}
      <div className="w-28 shrink-0 text-xs font-mono text-textMuted">
        {formatTime(log.timestamp)}
      </div>

      {/* Action + truncated user ID */}
      <div className="w-48 shrink-0 flex flex-col">
        <span
          className="text-sm font-medium text-textMain truncate"
          title={log.action}
        >
          {log.action}
        </span>
        <span
          className="text-xs font-mono text-textMuted truncate mt-0.5"
          title={log.user_id}
        >
          {shortUserId}
        </span>
      </div>

      {/* Location / IP — replaces the "Reason" column since LogWithRiskResponse
          has no reason field (reason lives only on AccessDecision, not on logs) */}
      <div className="flex-1 min-w-0">
        <p
          className="text-xs font-mono text-textMuted truncate"
          title={[log.ip_address, log.location].filter(Boolean).join(' · ')}
        >
          {log.ip_address && (
            <span className="text-textMuted">{log.ip_address}</span>
          )}
          {log.ip_address && log.location && (
            <span className="text-border mx-1">·</span>
          )}
          {log.location && (
            <span className="text-textMuted">{log.location}</span>
          )}
          {!log.ip_address && !log.location && (
            <span className="italic text-textMuted opacity-50">No location data</span>
          )}
        </p>
        {log.resource_accessed && (
          <p className="text-xs text-textMuted opacity-70 truncate mt-0.5">
            → {log.resource_accessed}
          </p>
        )}
      </div>

      {/* Risk score — null-safe */}
      <div className="w-24 shrink-0 flex justify-center">
        {log.risk_score != null ? (
          <RiskBadge score={log.risk_score} />
        ) : (
          <span className="text-xs text-textMuted italic">Pending</span>
        )}
      </div>

      {/* Decision — null-safe */}
      <div className="w-36 shrink-0 flex justify-end">
        {log.decision ? (
          <Badge variant={DECISION_VARIANT[log.decision]}>
            {log.decision}
          </Badge>
        ) : (
          <span className="text-xs text-textMuted italic">Pending</span>
        )}
      </div>

      {/* Expand chevron */}
      {onClick && (
        <div className="w-6 shrink-0 flex justify-end text-textMuted group-hover:text-textMain transition-colors">
          <ChevronRight className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};