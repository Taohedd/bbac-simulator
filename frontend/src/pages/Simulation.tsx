import React from 'react';
import { Activity, AlertCircle, RefreshCw } from 'lucide-react';
import { useSimulation } from '../hooks/useSimulation';
import { SimulationControls } from '../components/simulation/SimulationControls';
import { ScenarioCard } from '../components/simulation/ScenarioCard';

export const Simulation: React.FC = () => {
  // Hook manages its own polling — no useEffect needed here
  const {
    isRunning,
    scenarios,
    activeScenarioId,
    isLoading,
    error,
    startSimulation,
    stopSimulation,
    resetSimulation,
    setScenario,
    clearScenario,
    triggerScenarioOnce,
    refetchStatus,
  } = useSimulation();

  return (
    <div className="space-y-6 h-full flex flex-col">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg border ${
            isRunning
              ? 'bg-risk-low/10 border-risk-low/20'
              : 'bg-surfaceHover border-border'
          }`}>
            <Activity className={`w-5 h-5 ${
              isRunning ? 'text-risk-low animate-pulse' : 'text-textMuted'
            }`} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-textMain">
              Simulation Control
            </h2>
            <p className="text-sm text-textMuted">
              Manage synthetic data generation and attack scenarios
            </p>
          </div>
        </div>

        <button
          onClick={() => void refetchStatus()}
          disabled={isLoading}
          className="flex items-center space-x-2 px-3 py-2 bg-surfaceHover hover:bg-border text-textMuted text-sm font-medium rounded-lg border border-border transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Status</span>
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="p-4 bg-decision-block/10 border border-decision-block/20 rounded-lg flex items-start space-x-3 text-decision-block">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Engine controls + explainer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <SimulationControls
            isRunning={isRunning}
            onStart={startSimulation}
            onStop={stopSimulation}
            onReset={resetSimulation}
          />
        </div>

        <div className="lg:col-span-2 bg-surface border border-border rounded-xl p-6 flex flex-col justify-center space-y-4">
          <h3 className="text-base font-semibold text-textMain">How it works</h3>
          <p className="text-sm text-textMuted leading-relaxed">
            The simulation engine generates synthetic user activity logs in real-time.
            When running, it creates realistic baseline behaviour for each virtual user
            based on their role profile — typical hours, locations, device fingerprints,
            and common actions.
          </p>
          <p className="text-sm text-textMuted leading-relaxed">
            Inject <span className="text-textMain font-medium">Threat Scenarios</span> below
            to test the BBAC detection pipeline. Scenarios can run continuously at a
            configurable injection rate, or be triggered once for an immediate single
            anomaly event. The ML engine will detect the deviation and issue a real-time
            BLOCK or MFA decision visible on the Dashboard.
          </p>
          <div className="grid grid-cols-3 gap-3 pt-2">
            {[
              { label: 'Score 0–30', decision: 'ALLOW', color: 'text-risk-low', bg: 'bg-risk-low/10 border-risk-low/20' },
              { label: 'Score 31–69', decision: 'MFA', color: 'text-risk-medium', bg: 'bg-risk-medium/10 border-risk-medium/20' },
              { label: 'Score 70–100', decision: 'BLOCK', color: 'text-risk-high', bg: 'bg-risk-high/10 border-risk-high/20' },
            ].map((tier) => (
              <div key={tier.decision} className={`rounded-lg border px-3 py-2 text-center ${tier.bg}`}>
                <p className={`text-xs font-bold ${tier.color}`}>{tier.decision}</p>
                <p className="text-xs text-textMuted font-mono mt-0.5">{tier.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Scenario grid */}
      <div>
        <h3 className="text-base font-semibold text-textMain mb-4 flex items-center gap-3">
          Threat Scenarios
          {activeScenarioId && (
            <span className="px-2.5 py-0.5 rounded-full bg-risk-low/10 text-risk-low text-xs font-medium border border-risk-low/20">
              1 Active
            </span>
          )}
        </h3>

        {isLoading && scenarios.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-textMuted space-y-4">
            <div className="w-8 h-8 border-4 border-border border-t-risk-low rounded-full animate-spin" />
            <p className="text-sm">Loading scenarios...</p>
          </div>
        ) : scenarios.length === 0 ? (
          <div className="text-center py-12 bg-surface/50 rounded-xl border border-border text-textMuted text-sm">
            No scenarios available — check that the backend is running.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {scenarios.map((scenario) => (
              <ScenarioCard
                key={scenario.id}
                scenario={scenario}
                isActive={activeScenarioId === scenario.id}
                onSetScenario={setScenario}
                onTriggerOnce={triggerScenarioOnce}
                onClearScenario={clearScenario}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};