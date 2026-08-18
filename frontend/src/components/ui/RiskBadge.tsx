import React from 'react';
import { Badge } from './Badge';
import { cn } from './Card';
import { RiskLevel } from '../../types';

export interface RiskBadgeProps {
  score?: number;
  level?: RiskLevel;
  showScore?: boolean;
  className?: string;
}

// Maps a numeric score to a RiskLevel using the SAME thresholds
// as the backend (RISK_LOW_THRESHOLD=30, RISK_HIGH_THRESHOLD=70).
// The frontend and backend must agree on these boundaries — if the
// backend changes them via the Policies page, update this to match.
function scoreToLevel(score: number): RiskLevel {
  if (score < 30) return 'LOW';
  if (score >= 70) return 'HIGH';
  return 'MEDIUM';
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  score,
  level,
  showScore = false,
  className,
}) => {
  // Resolve the display level: explicit prop wins, otherwise derive from score
  const derivedLevel: RiskLevel | null =
    level ?? (score !== undefined ? scoreToLevel(score) : null);

  if (!derivedLevel) {
    return (
      <Badge variant="default" className={className}>
        N/A
      </Badge>
    );
  }

  // Map RiskLevel to the Badge variant defined in Badge.tsx
  const variantMap: Record<RiskLevel, 'low' | 'medium' | 'high'> = {
    LOW: 'low',
    MEDIUM: 'medium',
    HIGH: 'high',
  };

  const label = showScore && score !== undefined
    ? `${Math.round(score)} · ${derivedLevel}`
    : derivedLevel;

  return (
    <Badge
      variant={variantMap[derivedLevel]}
      className={cn(className)}
    >
      {label}
    </Badge>
  );
};