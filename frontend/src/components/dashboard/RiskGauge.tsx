import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card } from '../ui/Card';
import { RiskLevel } from '../../types';

interface RiskGaugeProps {
  score: number;
  title?: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: number;
}

// SVG gauge dimensions
const SIZE = 160;
const STROKE_WIDTH = 12;
const RADIUS = (SIZE - STROKE_WIDTH) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

// Maps risk level to theme token class names — MUST use tailwind.config.js
// custom tokens (text-risk-*) not raw Tailwind colors (text-emerald-*), so
// a palette change in tailwind.config.js propagates here automatically.
const RISK_CONFIG: Record<RiskLevel, { textClass: string; label: string }> = {
  LOW:    { textClass: 'text-risk-low',    label: 'LOW'    },
  MEDIUM: { textClass: 'text-risk-medium', label: 'MEDIUM' },
  HIGH:   { textClass: 'text-risk-high',   label: 'HIGH'   },
};

// Thresholds match RISK_LOW_THRESHOLD=30, RISK_HIGH_THRESHOLD=70 in .env
function scoreToLevel(score: number): RiskLevel {
  if (score < 30) return 'LOW';
  if (score >= 70) return 'HIGH';
  return 'MEDIUM';
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({
  score,
  title = 'Average Risk Score',
  subtitle = 'Last 24 Hours',
  trend,
  trendValue,
}) => {
  // Guard against NaN/Infinity before any math
  const safeScore = Number.isFinite(score)
    ? Math.min(Math.max(Math.round(score), 0), 100)
    : 0;

  const strokeDashoffset =
    CIRCUMFERENCE - (safeScore / 100) * CIRCUMFERENCE;

  const level = scoreToLevel(safeScore);
  const config = RISK_CONFIG[level];

  return (
    <Card className="flex flex-col items-center justify-center p-6 h-full">

      {/* Title */}
      <div className="text-center mb-4">
        <h3 className="text-sm font-medium text-textMuted uppercase tracking-wider">
          {title}
        </h3>
        {subtitle && (
          <p className="text-xs text-textMuted opacity-70 mt-1">{subtitle}</p>
        )}
      </div>

      {/* SVG Gauge */}
      <div className="relative flex items-center justify-center">
        <svg
          width={SIZE}
          height={SIZE}
          className="transform -rotate-90"
          aria-label={`Risk score: ${safeScore} — ${level}`}
        >
          {/* Background track */}
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            className="text-surfaceHover"
            strokeWidth={STROKE_WIDTH}
            stroke="currentColor"
            fill="transparent"
          />
          {/* Progress arc */}
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            className={`${config.textClass} transition-all duration-1000 ease-out`}
            strokeWidth={STROKE_WIDTH}
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            stroke="currentColor"
            fill="transparent"
          />
        </svg>

        {/* Center label */}
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span className={`text-4xl font-bold font-mono ${config.textClass}`}>
            {safeScore}
          </span>
          <span className={`text-xs font-bold tracking-widest mt-1 ${config.textClass}`}>
            {config.label}
          </span>
        </div>
      </div>

      {/* Trend indicator — only rendered when trend prop is provided */}
      {trend && (
        <div className="mt-6 flex items-center space-x-2 text-sm">
          {trend === 'up'     && <TrendingUp   className="w-4 h-4 text-risk-high"   />}
          {trend === 'down'   && <TrendingDown className="w-4 h-4 text-risk-low"    />}
          {trend === 'stable' && <Minus        className="w-4 h-4 text-textMuted"   />}

          <span className="text-textMuted">
            {trend === 'up' && trendValue != null && (
              <span className="text-risk-high font-medium">+{trendValue}%</span>
            )}
            {trend === 'down' && trendValue != null && (
              <span className="text-risk-low font-medium">-{trendValue}%</span>
            )}
            {trend === 'stable' && <span>Stable</span>}
            {' '}vs yesterday
          </span>
        </div>
      )}
    </Card>
  );
};