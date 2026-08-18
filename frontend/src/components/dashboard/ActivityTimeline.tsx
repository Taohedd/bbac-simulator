import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  type TooltipProps,
} from 'recharts';
import { Card } from '../ui/Card';
import { TimelineBucket } from '../../types';

// Theme hex values for chart stroke/fill — must match tailwind.config.js
// since Recharts doesn't read CSS variables, only concrete hex values.
const CHART_COLORS = {
  allow:       '#10b981', // decision.allow / risk.low
  mfa:         '#f59e0b', // decision.mfa  / risk.medium
  block:       '#ef4444', // decision.block / risk.high
  riskLine:    '#f59e0b', // amber — risk trend line in amber so it's neutral
  axis:        '#64748b', // slate-500 approximate
  grid:        '#334155', // border token approximate
};

// Defined OUTSIDE the component so Recharts never sees a changed reference
// on re-renders, which would force tooltip to remount.
const CustomTooltip: React.FC<TooltipProps<number, string>> = ({
  active,
  payload,
  label,
}) => {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-surface border border-border p-3 rounded-md shadow-xl">
      <p className="text-textMain font-medium mb-2 font-mono">{label as string}</p>
      {payload.map((entry) => (
        <div
          key={entry.name}
          className="flex items-center justify-between gap-4 text-sm mb-1"
        >
          <span style={{ color: entry.color }}>{entry.name}:</span>
          <span className="font-mono text-textMain">
            {entry.name === 'Avg Risk'
              ? Number(entry.value).toFixed(1)
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
};

interface ActivityTimelineProps {
  // Passed from Dashboard.tsx — useDashboard() is called once at the page
  // level, not per-component, to avoid duplicate polling intervals.
  timeline: TimelineBucket[] | null;
  isLoading: boolean;
  error: string | null;
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({
  timeline,
  isLoading,
  error,
}) => {
  if (isLoading) {
    return (
      <Card className="p-6 h-[400px] flex flex-col">
        <h3 className="text-lg font-medium text-textMain mb-4">
          Activity &amp; Risk Timeline
        </h3>
        <div className="flex-1 animate-pulse bg-surface/50 rounded-md" />
      </Card>
    );
  }

  if (error || !timeline) {
    return (
      <Card className="p-6 h-[400px] flex flex-col justify-center items-center text-textMuted">
        <p>Failed to load timeline data.</p>
      </Card>
    );
  }

  return (
    <Card className="p-6 h-[400px] flex flex-col">
      <h3 className="text-lg font-medium text-textMain mb-6">
        Activity &amp; Risk Timeline (24h)
      </h3>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={timeline}
            margin={{ top: 5, right: 0, left: -20, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={CHART_COLORS.grid}
              vertical={false}
            />
            <XAxis
              dataKey="time"
              // "time" is already "HH:00" from the backend — no Date parsing needed.
              // new Date("14:00") is not a valid ISO string in most browsers.
              tickFormatter={(val: string) => val}
              stroke={CHART_COLORS.axis}
              fontSize={11}
              tickMargin={8}
            />
            <YAxis
              yAxisId="left"
              stroke={CHART_COLORS.axis}
              fontSize={11}
              tickFormatter={(val: number) => Math.floor(val).toString()}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke={CHART_COLORS.axis}
              fontSize={11}
              domain={[0, 100]}
              tickFormatter={(val: number) => `${val}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: '20px', fontSize: '12px' }}
            />
            <Bar
              yAxisId="left"
              dataKey="ALLOW"
              name="Allow"
              stackId="a"
              fill={CHART_COLORS.allow}
            />
            <Bar
              yAxisId="left"
              dataKey="MFA_CHALLENGE"
              name="MFA"
              stackId="a"
              fill={CHART_COLORS.mfa}
            />
            <Bar
              yAxisId="left"
              dataKey="BLOCK"
              name="Block"
              stackId="a"
              fill={CHART_COLORS.block}
              radius={[4, 4, 0, 0]}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="avg_risk_score"
              name="Avg Risk"
              stroke={CHART_COLORS.riskLine}
              strokeWidth={2}
              dot={false}
              activeDot={{
                r: 5,
                fill: CHART_COLORS.riskLine,
                stroke: '#1e293b',
                strokeWidth: 2,
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};