import React from 'react';
import { Users, Activity, ShieldAlert, ShieldBan, TrendingUp } from 'lucide-react';
import { Card } from '../ui/Card';
import { cn } from '../ui/Card';
import { DashboardStats } from '../../types';

interface StatsCardsProps {
  stats: DashboardStats;
  isLoading: boolean;
  error: string | null;
}

export const StatsCards: React.FC<StatsCardsProps> = ({ stats, isLoading, error }) => {
  if (isLoading && !stats) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <Card key={i} className="h-28 animate-pulse bg-surface/50" />
        ))}
      </div>
    );
  }

  if (error && !stats) {
    return (
      <Card className="p-4 border-decision-block/20 bg-decision-block/10 text-decision-block flex items-center gap-2">
        <ShieldAlert className="w-5 h-5 flex-shrink-0" />
        <span className="text-sm font-medium">Failed to load dashboard statistics.</span>
      </Card>
    );
  }

  // Use same thresholds as backend (RISK_LOW=30, RISK_HIGH=70)
  const riskColor = (score: number) =>
    score >= 70 ? 'text-risk-high' : score >= 30 ? 'text-risk-medium' : 'text-risk-low';

  const riskBg = (score: number) =>
    score >= 70 ? 'bg-risk-high/10' : score >= 30 ? 'bg-risk-medium/10' : 'bg-risk-low/10';

  const statItems = [
    {
      title: 'Active Users (24h)',
      value: `${stats.users_active_24h} / ${stats.total_active_accounts}`,
      icon: Users,
      color: 'text-textMuted',
      bgColor: 'bg-surfaceHover',
    },
    {
      title: 'Total Events (24h)',
      value: stats.events_24h.toLocaleString(),
      icon: Activity,
      color: 'text-risk-low',
      bgColor: 'bg-risk-low/10',
    },
    {
      title: 'Avg Risk Score',
      value: stats.average_risk_score_24h.toFixed(1),
      icon: ShieldAlert,
      color: riskColor(stats.average_risk_score_24h),
      bgColor: riskBg(stats.average_risk_score_24h),
    },
    {
      title: 'Anomaly Rate',
      value: `${stats.anomaly_rate_percent.toFixed(1)}%`,
      icon: TrendingUp,
      color: riskColor(stats.anomaly_rate_percent),
      bgColor: riskBg(stats.anomaly_rate_percent),
    },
    {
      title: 'Blocked Actions',
      value: stats.decisions_24h.BLOCK.toLocaleString(),
      icon: ShieldBan,
      color: 'text-decision-block',
      bgColor: 'bg-decision-block/10',
    },
  ] as const;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      {statItems.map((item) => {
        const Icon = item.icon;
        return (
          <Card key={item.title} className="p-5 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-textMuted mb-1">{item.title}</p>
              <h3 className="text-2xl font-bold text-textMain">{item.value}</h3>
            </div>
            <div className={cn('p-3 rounded-lg', item.bgColor)}>
              <Icon className={cn('w-6 h-6', item.color)} />
            </div>
          </Card>
        );
      })}
    </div>
  );
};