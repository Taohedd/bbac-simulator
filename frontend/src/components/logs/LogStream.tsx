import React, { useEffect, useRef, useState } from 'react';
import { Play, Pause, Activity, AlertCircle } from 'lucide-react';
import { Card } from '../ui/Card';
import { LogEntry } from './LogEntry';
import { LogWithRiskResponse } from '../../types';

interface LogStreamProps {
  logs: LogWithRiskResponse[];
  title?: string;
  isLive?: boolean;
  maxHeight?: string;
  onLogClick?: (logId: string) => void;
}

export const LogStream: React.FC<LogStreamProps> = ({
  logs,
  title = 'Live Activity Stream',
  isLive = true,
  maxHeight = 'h-[600px]',
  onLogClick,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Logs arrive newest-first (both from GET /logs/ and from the WebSocket store).
  // Scroll to TOP when new entries arrive so the freshest log is always visible.
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [logs, autoScroll]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    // Disable auto-scroll if user scrolls down away from the top
    const { scrollTop } = e.currentTarget;
    setAutoScroll(scrollTop < 10);
  };

  return (
    <Card className="flex flex-col overflow-hidden">

      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-surface/50">
        <div className="flex items-center space-x-2">
          <Activity
            className={`w-5 h-5 ${isLive ? 'text-risk-low animate-pulse' : 'text-textMuted'}`}
          />
          <h3 className="text-sm font-medium text-textMain uppercase tracking-wider">
            {title}
          </h3>
          <span className="ml-2 px-2 py-0.5 rounded-full bg-surfaceHover text-textMuted text-xs font-mono">
            {logs.length} events
          </span>
        </div>

        {isLive && (
          <button
            onClick={() => setAutoScroll((prev) => !prev)}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              autoScroll
                ? 'bg-risk-low/10 text-risk-low hover:bg-risk-low/20'
                : 'bg-surfaceHover text-textMuted hover:bg-border'
            }`}
          >
            {autoScroll ? (
              <>
                <Pause className="w-3.5 h-3.5" />
                <span>Pause Scroll</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" />
                <span>Resume Scroll</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Column headers — must match LogEntry column widths exactly */}
      <div className="flex items-center gap-4 px-4 py-3 border-b border-border bg-background text-xs font-medium text-textMuted uppercase tracking-wider">
        <div className="w-28 shrink-0">Timestamp</div>
        <div className="w-48 shrink-0">Action / User</div>
        <div className="flex-1 min-w-0">Location / IP</div>  {/* matches LogEntry middle column */}
        <div className="w-24 shrink-0 text-center">Risk Score</div>
        <div className="w-36 shrink-0 text-right">Decision</div>
        {onLogClick && <div className="w-6 shrink-0" />}
      </div>

      {/* Log list */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className={`overflow-y-auto ${maxHeight} bg-background`}
      >
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-textMuted space-y-3 p-8">
            <AlertCircle className="w-8 h-8 text-border" />
            <p className="text-sm">No logs available in the stream.</p>
          </div>
        ) : (
          <div className="flex flex-col">
            {logs.map((log) => (
              // Use log.id — not log.log_id (which is the WebSocket RiskEvent field)
              <div key={log.id} className="px-1">
                <LogEntry log={log} onClick={onLogClick} />
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
};