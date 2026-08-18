import React, { useEffect, useState, useCallback } from 'react';
import {
  Search, Filter, RefreshCw, AlertCircle,
  ChevronLeft, ChevronRight, FileText, X,
} from 'lucide-react';
import { useLogs } from '../hooks/useLogs';
import { LogStream } from '../components/logs/LogStream';
import { Card } from '../components/ui/Card';
import { RiskBadge } from '../components/ui/RiskBadge';
import { Badge, type BadgeVariant } from '../components/ui/Badge';
import { LogDetail, Decision } from '../types';
import { api } from '../api/client';

const LIMIT = 50;

// LogAction values must match the real backend LogAction Literal exactly
const LOG_ACTIONS = [
  'LOGIN', 'LOGOUT', 'FILE_READ', 'FILE_WRITE', 'FILE_DELETE',
  'DB_QUERY', 'API_CALL', 'EMAIL_SEND', 'REPORT_VIEW', 'SETTINGS_VIEW',
  'MFA_VERIFY', 'PASSWORD_CHANGE', 'DB_EXPORT', 'BULK_DOWNLOAD',
  'CONFIG_CHANGE', 'ADMIN_ACTION', 'PRIVILEGE_ESCALATION',
  'DATA_EXFIL', 'LATERAL_MOVE',
];

// Typed decision variant lookup — consistent with every other component
const DECISION_VARIANT: Record<Decision, BadgeVariant> = {
  ALLOW:         'allow',
  MFA_CHALLENGE: 'mfa',
  BLOCK:         'block',
};

export const Logs: React.FC = () => {
  const { logs, total, isLoading, error, refetch } = useLogs();

  // Filter state — page resets to 0 only on explicit Apply, not on every keystroke
  const [pendingFilters, setPendingFilters] = useState({
    user_id:   '',
    action:    '',
    min_score: '',
    max_score: '',
  });
  const [page, setPage] = useState(0);

  // Log detail modal state
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);
  const [logDetail, setLogDetail] = useState<LogDetail | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const loadLogs = useCallback(() => {
    void refetch({
      user_id:   pendingFilters.user_id   || undefined,
      action:    pendingFilters.action    || undefined,
      min_score: pendingFilters.min_score ? Number(pendingFilters.min_score) : undefined,
      max_score: pendingFilters.max_score ? Number(pendingFilters.max_score) : undefined,
      limit:  LIMIT,
      offset: page * LIMIT,
    });
  }, [refetch, pendingFilters, page]);

  // Fetch when page changes (filter changes only fire on form submit)
  useEffect(() => {
    loadLogs();
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleApplyFilters = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    loadLogs();
  };

  const handleClearFilters = () => {
    setPendingFilters({ user_id: '', action: '', min_score: '', max_score: '' });
    setPage(0);
    void refetch({ limit: LIMIT, offset: 0 });
  };

  const handleLogClick = async (logId: string) => {
    setSelectedLogId(logId);
    setLogDetail(null);
    setDetailError(null);
    setIsDetailLoading(true);
    try {
      // Use the correct namespaced method — api.get() does not exist
      const detail = await api.logs.getDetails(logId);
      setLogDetail(detail);
    } catch (err: unknown) {
      setDetailError(err instanceof Error ? err.message : 'Failed to load details');
    } finally {
      setIsDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setSelectedLogId(null);
    setLogDetail(null);
    setDetailError(null);
  };

  // Close detail on Escape
  useEffect(() => {
    if (!selectedLogId) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') closeDetail(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [selectedLogId]);

  const totalPages = Math.max(1, Math.ceil(total / LIMIT));

  return (
    <div className="space-y-6 h-full flex flex-col">

      {/* Header */}
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-surfaceHover rounded-lg border border-border">
          <FileText className="w-5 h-5 text-textMuted" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-textMain">Audit Logs</h2>
          <p className="text-sm text-textMuted">
            Historical access events and risk analysis
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <form onSubmit={handleApplyFilters} className="flex flex-wrap items-end gap-4">

          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs font-medium text-textMuted mb-1.5">User ID</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-textMuted pointer-events-none" />
              <input
                type="text"
                value={pendingFilters.user_id}
                onChange={(e) => setPendingFilters((p) => ({ ...p, user_id: e.target.value }))}
                placeholder="UUID..."
                className="block w-full pl-9 pr-3 py-2 border border-border rounded-lg bg-background text-textMain placeholder-textMuted focus:outline-none focus:ring-1 focus:ring-border text-sm"
              />
            </div>
          </div>

          <div className="w-44">
            <label className="block text-xs font-medium text-textMuted mb-1.5">Action</label>
            <select
              value={pendingFilters.action}
              onChange={(e) => setPendingFilters((p) => ({ ...p, action: e.target.value }))}
              className="block w-full px-3 py-2 border border-border rounded-lg bg-background text-textMain text-sm focus:outline-none focus:ring-1 focus:ring-border"
            >
              <option value="">All Actions</option>
              {LOG_ACTIONS.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </div>

          <div className="w-24">
            <label className="block text-xs font-medium text-textMuted mb-1.5">Min Risk</label>
            <input
              type="number"
              value={pendingFilters.min_score}
              onChange={(e) => setPendingFilters((p) => ({ ...p, min_score: e.target.value }))}
              min="0" max="100" placeholder="0"
              className="block w-full px-3 py-2 border border-border rounded-lg bg-background text-textMain text-sm focus:outline-none focus:ring-1 focus:ring-border"
            />
          </div>

          <div className="w-24">
            <label className="block text-xs font-medium text-textMuted mb-1.5">Max Risk</label>
            <input
              type="number"
              value={pendingFilters.max_score}
              onChange={(e) => setPendingFilters((p) => ({ ...p, max_score: e.target.value }))}
              min="0" max="100" placeholder="100"
              className="block w-full px-3 py-2 border border-border rounded-lg bg-background text-textMain text-sm focus:outline-none focus:ring-1 focus:ring-border"
            />
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 bg-risk-low/10 hover:bg-risk-low/20 text-risk-low text-sm font-medium rounded-lg border border-risk-low/20 transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <Filter className="w-4 h-4" />
              Apply
            </button>
            <button
              type="button"
              onClick={handleClearFilters}
              className="px-4 py-2 bg-surfaceHover hover:bg-border text-textMuted text-sm font-medium rounded-lg border border-border transition-colors"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={loadLogs}
              disabled={isLoading}
              className="p-2 bg-surfaceHover hover:bg-border text-textMuted rounded-lg border border-border transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </form>
      </Card>

      {/* Error */}
      {error && (
        <div className="p-4 bg-decision-block/10 border border-decision-block/20 rounded-lg flex items-start space-x-3 text-decision-block">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Log stream */}
      <div className="flex-1 min-h-0 flex flex-col">
        <LogStream
          logs={logs}
          title="Historical Events"
          isLive={false}
          maxHeight="h-[calc(100vh-26rem)]"
          onLogClick={handleLogClick}
        />

        {/* Pagination */}
        <div className="flex items-center justify-between mt-4 px-1">
          <p className="text-sm text-textMuted">
            Showing{' '}
            <span className="font-medium text-textMain">
              {total > 0 ? page * LIMIT + 1 : 0}
            </span>{' '}
            –{' '}
            <span className="font-medium text-textMain">
              {Math.min((page + 1) * LIMIT, total)}
            </span>{' '}
            of{' '}
            <span className="font-medium text-textMain">{total}</span>
          </p>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || isLoading}
              className="p-2 bg-surfaceHover hover:bg-border text-textMuted rounded-lg border border-border disabled:opacity-50 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm text-textMuted px-2 font-mono">
              {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1 || isLoading}
              className="p-2 bg-surfaceHover hover:bg-border text-textMuted rounded-lg border border-border disabled:opacity-50 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Log Detail Modal */}
      {selectedLogId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
          <div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={closeDetail}
            aria-hidden="true"
          />
          <div className="relative w-full max-w-3xl max-h-[90vh] bg-surface border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden">

            {/* Modal header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-base font-semibold text-textMain">Log Details</h2>
              <button
                onClick={closeDetail}
                className="p-2 text-textMuted hover:text-textMain hover:bg-surfaceHover rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal body */}
            <div className="flex-1 overflow-y-auto p-6">
              {isDetailLoading && (
                <div className="flex justify-center items-center h-40">
                  <div className="w-8 h-8 border-4 border-border border-t-risk-low rounded-full animate-spin" />
                </div>
              )}

              {detailError && (
                <div className="text-center text-decision-block py-8">{detailError}</div>
              )}

              {/* Use the real LogDetail nested shape from types/index.ts */}
              {!isDetailLoading && !detailError && logDetail && (
                <div className="space-y-6">

                  {/* Log fields */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-textMuted mb-1">Log ID</p>
                      <p className="text-xs font-mono text-textMain">{logDetail.log.id}</p>
                    </div>
                    <div>
                      <p className="text-xs text-textMuted mb-1">Timestamp</p>
                      <p className="text-xs font-mono text-textMain">
                        {new Date(logDetail.log.timestamp).toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-textMuted mb-1">User</p>
                      <p className="text-xs font-mono text-textMain">{logDetail.user.username}</p>
                    </div>
                    <div>
                      <p className="text-xs text-textMuted mb-1">Action</p>
                      <p className="text-sm font-medium text-textMain">{logDetail.log.action}</p>
                    </div>
                    <div>
                      <p className="text-xs text-textMuted mb-1">IP Address</p>
                      <p className="text-xs font-mono text-textMain">
                        {logDetail.log.ip_address ?? '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-textMuted mb-1">Location</p>
                      <p className="text-xs text-textMain">
                        {logDetail.log.location ?? '—'}
                      </p>
                    </div>
                  </div>

                  {/* Risk + Decision */}
                  <div className="flex items-center space-x-6 p-4 bg-background rounded-lg border border-border">
                    <div>
                      <p className="text-xs text-textMuted mb-2">Risk Score</p>
                      {logDetail.analysis.risk_score != null ? (
                        <RiskBadge score={logDetail.analysis.risk_score} showScore />
                      ) : (
                        <span className="text-xs text-textMuted italic">Pending</span>
                      )}
                    </div>
                    <div>
                      <p className="text-xs text-textMuted mb-2">Decision</p>
                      {logDetail.enforcement.decision ? (
                        <Badge variant={DECISION_VARIANT[logDetail.enforcement.decision]}>
                          {logDetail.enforcement.decision}
                        </Badge>
                      ) : (
                        <span className="text-xs text-textMuted italic">Pending</span>
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-xs text-textMuted mb-1">Reason</p>
                      <p className="text-sm text-textMain">
                        {logDetail.enforcement.reason ?? '—'}
                      </p>
                    </div>
                  </div>

                  {/* ML feature vector */}
                  {logDetail.analysis.features && (
                    <div>
                      <p className="text-xs font-medium text-textMuted uppercase tracking-wider mb-3">
                        ML Feature Vector
                      </p>
                      <pre className="bg-background p-4 rounded-lg border border-border text-xs text-textMuted font-mono overflow-x-auto">
                        {JSON.stringify(logDetail.analysis.features, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};