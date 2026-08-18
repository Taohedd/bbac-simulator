import React, { useState } from 'react';
import {
  Zap, ShieldAlert, Clock, Download,
  UserX, Server, Shield, CheckCircle2, AlertCircle,
} from 'lucide-react';
import { Card } from '../ui/Card';
import { ScenarioInfo } from '../../types';

interface ScenarioCardProps {
  scenario: ScenarioInfo;
  isActive: boolean;
  onSetScenario: (scenarioId: string, injectRate: number) => Promise<void>;
  onTriggerOnce: (scenarioId: string) => Promise<void>;
  onClearScenario: () => Promise<void>;
}

// Maps real AnomalyType values (from scenarios.py) to icons and accent colors.
// Keys match the AnomalyType enum strings the backend sends in ScenarioInfo.type.
const TYPE_CONFIG: Record<string, { icon: React.ReactNode; accent: string; border: string }> = {
  IMPOSSIBLE_TRAVEL:      { icon: <Server className="w-5 h-5 text-risk-medium" />,   accent: 'text-risk-medium', border: 'border-risk-medium/40' },
  OFF_HOURS_ACCESS:       { icon: <Clock className="w-5 h-5 text-risk-medium" />,    accent: 'text-risk-medium', border: 'border-risk-medium/40' },
  UNRECOGNIZED_DEVICE:    { icon: <UserX className="w-5 h-5 text-risk-medium" />,    accent: 'text-risk-medium', border: 'border-risk-medium/40' },
  DATA_EXFILTRATION:      { icon: <Download className="w-5 h-5 text-risk-high" />,   accent: 'text-risk-high',   border: 'border-risk-high/40'   },
  PRIVILEGE_ESCALATION:   { icon: <ShieldAlert className="w-5 h-5 text-risk-high" />,accent: 'text-risk-high',   border: 'border-risk-high/40'   },
  COMPROMISED_CREDENTIAL: { icon: <ShieldAlert className="w-5 h-5 text-risk-high" />,accent: 'text-risk-high',   border: 'border-risk-high/40'   },
  BRUTE_FORCE:            { icon: <AlertCircle className="w-5 h-5 text-risk-high" />,accent: 'text-risk-high',   border: 'border-risk-high/40'   },
  LATERAL_MOVEMENT:       { icon: <Server className="w-5 h-5 text-risk-high" />,     accent: 'text-risk-high',   border: 'border-risk-high/40'   },
};

const DEFAULT_CONFIG = {
  icon:   <Shield className="w-5 h-5 text-textMuted" />,
  accent: 'text-textMuted',
  border: 'border-border',
};

export const ScenarioCard: React.FC<ScenarioCardProps> = ({
  scenario,
  isActive,
  onSetScenario,
  onTriggerOnce,
  onClearScenario,
}) => {
  const [injectRate, setInjectRate] = useState<number>(0.2);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAction = async (action: () => Promise<void>) => {
    setIsLoading(true);
    setError(null);
    try {
      await action();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setIsLoading(false);
    }
  };

  const typeConfig = TYPE_CONFIG[scenario.type] ?? DEFAULT_CONFIG;

  return (
    <Card
      className={`flex flex-col h-full transition-all duration-300 ${
        isActive ? typeConfig.border : 'border-border'
      } ${isActive ? 'bg-surface' : 'bg-background'}`}
    >
      <div className="p-5 flex-1 flex flex-col">

        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-surfaceHover">
              {typeConfig.icon}
            </div>
            <h3 className="text-sm font-semibold text-textMain">{scenario.name}</h3>
          </div>
          {isActive && (
            <span className="flex items-center text-xs font-medium text-risk-low bg-risk-low/10 px-2 py-1 rounded-full flex-shrink-0">
              <CheckCircle2 className="w-3 h-3 mr-1" /> Active
            </span>
          )}
        </div>

        {/* Description */}
        <p className="text-xs text-textMuted mb-4 flex-1 leading-relaxed">
          {scenario.description}
        </p>

        {/* Error */}
        {error && (
          <div className="mb-4 p-2 bg-decision-block/10 border border-decision-block/20 rounded text-xs text-decision-block">
            {error}
          </div>
        )}

        {/* Continuous injection controls */}
        <div className="bg-background p-3 rounded-lg border border-border mb-3">
          <label className="block text-xs font-medium text-textMuted mb-2">
            Injection rate:{' '}
            <span className={`font-mono ${typeConfig.accent}`}>
              {Math.round(injectRate * 100)}%
            </span>
          </label>
          <input
            type="range"
            min="0.05"
            max="1.0"
            step="0.05"
            value={injectRate}
            onChange={(e) => setInjectRate(parseFloat(e.target.value))}
            disabled={isLoading || isActive}
            className="w-full h-1.5 bg-surfaceHover rounded-lg appearance-none cursor-pointer accent-current disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ accentColor: isActive ? '#64748b' : '#f59e0b' }}
          />

          <div className="mt-3">
            {isActive ? (
              <button
                onClick={() => handleAction(onClearScenario)}
                disabled={isLoading}
                className="w-full py-1.5 px-3 bg-surfaceHover hover:bg-border text-textMuted text-xs font-medium rounded border border-border transition-colors disabled:opacity-50"
              >
                Stop Scenario
              </button>
            ) : (
              <button
                onClick={() => handleAction(() => onSetScenario(scenario.id, injectRate))}
                disabled={isLoading}
                className={`w-full py-1.5 px-3 text-xs font-medium rounded border transition-colors disabled:opacity-50 bg-risk-medium/10 border-risk-medium/20 hover:bg-risk-medium/20 ${typeConfig.accent}`}
              >
                Set Active
              </button>
            )}
          </div>
        </div>

        {/* One-shot trigger */}
        <button
          onClick={() => handleAction(() => onTriggerOnce(scenario.id))}
          disabled={isLoading}
          className="w-full flex items-center justify-center py-2 px-4 bg-surfaceHover hover:bg-border text-textMuted text-xs font-medium rounded-lg border border-border transition-colors disabled:opacity-50 group"
        >
          <Zap className="w-4 h-4 mr-2 text-decision-mfa group-hover:scale-110 transition-transform" />
          Trigger Once Now
        </button>
      </div>
    </Card>
  );
};