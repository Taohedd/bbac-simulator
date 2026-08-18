import React from 'react';
import { Shield, ShieldAlert, Eye, Clock } from 'lucide-react';
import { Badge, type BadgeVariant } from '../ui/Badge';
import { RiskBadge } from '../ui/RiskBadge';
import { UserRiskSummary, Decision } from '../../types';

interface UserTableProps {
  users: UserRiskSummary[];
  isLoading: boolean;
  onViewUser: (userId: string) => void;
}

// Typed lookup — returns a compile-time-checked BadgeVariant, not a plain
// string. Any new Decision value causes a TypeScript error here rather than
// silently rendering unstyled.
const DECISION_VARIANT: Record<Decision, BadgeVariant> = {
  ALLOW:         'allow',
  MFA_CHALLENGE: 'mfa',
  BLOCK:         'block',
};

// Accepts string | null — handles the null case the TypeScript type requires.
const formatDate = (isoString: string | null): string => {
  if (!isoString) return 'Never';
  return new Intl.DateTimeFormat('en-US', {
    month:  'short',
    day:    '2-digit',
    hour:   '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(isoString));
};

export const UserTable: React.FC<UserTableProps> = ({
  users,
  isLoading,
  onViewUser,
}) => {
  if (isLoading) {
    return (
      <div className="w-full p-8 flex flex-col items-center justify-center text-textMuted space-y-4">
        {/* Spinner uses theme colors — no blue */}
        <div className="w-8 h-8 border-4 border-border border-t-risk-low rounded-full animate-spin" />
        <p className="text-sm">Loading users...</p>
      </div>
    );
  }

  if (!users.length) {
    return (
      <div className="w-full p-8 flex flex-col items-center justify-center text-textMuted bg-surface/50 rounded-lg border border-border">
        <Shield className="w-12 h-12 mb-3 text-border" />
        <p className="text-sm">No users found.</p>
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full text-left text-sm whitespace-nowrap">
        <thead className="bg-background text-textMuted border-b border-border">
          <tr>
            <th className="px-6 py-4 font-medium">User</th>
            <th className="px-6 py-4 font-medium">Role</th>
            <th className="px-6 py-4 font-medium">Status</th>
            <th className="px-6 py-4 font-medium">Risk Profile</th>
            <th className="px-6 py-4 font-medium">Latest Decision</th>
            <th className="px-6 py-4 font-medium">Last Seen</th>
            <th className="px-6 py-4 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {users.map((user) => (
            <tr
              key={user.user_id}
              className="hover:bg-surfaceHover/30 transition-colors"
            >
              {/* Username + truncated UUID */}
              <td className="px-6 py-4">
                <div className="flex flex-col">
                  <span className="font-medium text-textMain">{user.username}</span>
                  <span className="text-xs text-textMuted font-mono mt-0.5">
                    {user.user_id.split('-')[0]}…
                  </span>
                </div>
              </td>

              {/* Role */}
              <td className="px-6 py-4 text-textMuted capitalize">
                {user.role.toLowerCase()}
              </td>

              {/* Active status */}
              <td className="px-6 py-4">
                <div className="flex items-center space-x-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      user.is_active ? 'bg-risk-low' : 'bg-border'
                    }`}
                  />
                  <span className="text-textMuted">
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </td>

              {/* Risk score + badge */}
              <td className="px-6 py-4">
                <div className="flex items-center space-x-2">
                  <RiskBadge
                    score={user.latest_score ?? undefined}
                    level={user.risk_level ?? undefined}   // null → undefined, no `any` cast
                  />
                  {user.risk_level === 'HIGH' && (
                    <ShieldAlert className="w-4 h-4 text-risk-high animate-pulse" />
                  )}
                </div>
              </td>

              {/* Latest decision */}
              <td className="px-6 py-4">
                {user.latest_decision ? (
                  <Badge variant={DECISION_VARIANT[user.latest_decision]}>
                    {user.latest_decision}
                  </Badge>
                ) : (
                  <span className="text-textMuted italic text-xs">None</span>
                )}
              </td>

              {/* Last seen — wrapper div so flex doesn't apply to <td> directly */}
              <td className="px-6 py-4 text-textMuted font-mono text-xs">
                <div className="flex items-center space-x-1.5">
                  <Clock className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>{formatDate(user.last_seen)}</span>
                </div>
              </td>

              {/* View action */}
              <td className="px-6 py-4 text-right">
                <button
                  onClick={() => onViewUser(user.user_id)}
                  title="View Details"
                  aria-label={`View details for ${user.username}`}
                  className="inline-flex items-center justify-center p-2 text-textMuted hover:text-textMain hover:bg-surfaceHover rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-border"
                >
                  <Eye className="w-4 h-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};