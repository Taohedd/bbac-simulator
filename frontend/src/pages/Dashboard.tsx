import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { useDashboard } from '../hooks/useDashboard';
import { useStore } from '../store/useStore';
import { StatsCards } from '../components/dashboard/StatsCards';
import { RiskGauge } from '../components/dashboard/RiskGauge';
import { ActivityTimeline } from '../components/dashboard/ActivityTimeline';
import { AlertsFeed } from '../components/dashboard/AlertsFeed';
import { LogStream } from '../components/logs/LogStream';
import { LogWithRiskResponse } from '../types';

export const Dashboard: React.FC = () => {
  // useDashboard manages its own 10-second polling interval internally.
  // No additional useEffect/setInterval is needed here.
  const { stats, timeline, isLoading, error, refetch } = useDashboard();

  // Live WebSocket events — field is liveEvents in the Zustand store
  const liveEvents = useStore((state) => state.liveEvents);

  // Map RiskEvent shape → LogWithRiskResponse shape for the LogStream component.
  // WebSocket events don't carry ip_address/location/device — those are null here;
  // the full data is only available via GET /logs/{id}/details.
  const streamLogs: LogWithRiskResponse[] = liveEvents.map((e) => ({
    id: e.log_id,
    user_id: e.user_id,
    timestamp: e.timestamp,
    action: e.action,
    ip_address: null,
    location: null,
    device_fingerprint: null,
    resource_accessed: null,
    session_id: null,
    risk_score: e.risk_score,
    risk_score_id: null,
    decision: e.decision,
  }));

  if (isLoading && !stats) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] space-y-4">
        <div className="w-10 h-10 border-4 border-border border-t-risk-low rounded-full animate-spin" />
        <p className="text-textMuted font-medium">Loading dashboard data...</p>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)]">
        <div className="bg-decision-block/10 border border-decision-block/20 p-6 rounded-xl flex flex-col items-center max-w-md text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-decision-block" />
          <div>
            <h3 className="text-base font-semibold text-decision-block mb-1">
              Failed to load dashboard
            </h3>
            <p className="text-sm text-textMuted">{error}</p>
          </div>
          <button
            onClick={() => void refetch()}
            className="flex items-center space-x-2 px-4 py-2 bg-surfaceHover hover:bg-border text-textMain rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Retry</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      {/* Manual refresh */}
      <div className="flex justify-end">
        <button
          onClick={() => void refetch()}
          disabled={isLoading}
          className="flex items-center space-x-2 px-3 py-2 bg-surfaceHover hover:bg-border text-textMuted text-sm font-medium rounded-lg border border-border transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Stats</span>
        </button>
      </div>

      {/* Stats summary cards — props-based, no internal useDashboard call */}
      {stats && (
        <StatsCards
          stats={stats}
          isLoading={isLoading}
          error={error}
        />
      )}

      {/* Timeline + Risk Gauge */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ActivityTimeline
            timeline={timeline?.timeline ?? null}
            isLoading={isLoading}
            error={error}
          />
        </div>
        <div className="lg:col-span-1">
          <RiskGauge
            score={stats?.average_risk_score_24h ?? 0}
            title="Avg Risk Score"
            subtitle="Last 24 Hours"
            trend={
              (stats?.average_risk_score_24h ?? 0) >= 70
                ? 'up'
                : (stats?.average_risk_score_24h ?? 0) >= 30
                ? 'stable'
                : 'down'
            }
          />
        </div>
      </div>

      {/* Alerts feed + Live log stream */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <AlertsFeed />
        </div>
        <div className="lg:col-span-2">
          <LogStream
            logs={streamLogs}
            title="Live Access Events"
            isLive={true}
            maxHeight="h-[400px]"
          />
        </div>
      </div>

    </div>
  );
};