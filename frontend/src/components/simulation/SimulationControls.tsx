import React, { useState } from 'react';
import { Play, Square, RotateCcw, Activity, AlertCircle } from 'lucide-react';
import { Card } from '../ui/Card';

interface SimulationControlsProps {
  isRunning: boolean;
  onStart: () => Promise<void>;
  onStop: () => Promise<void>;
  onReset: () => Promise<void>;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({
  isRunning,
  onStart,
  onStop,
  onReset,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAction = async (action: () => Promise<void>) => {
    setIsLoading(true);
    setError(null);
    try {
      await action();
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : 'An unexpected error occurred'
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Reset is also disabled while running — the backend rejects reset
  // with HTTP 400 if the simulation is active (see api/routes/simulation.py).
  const resetDisabled = isLoading || isRunning;

  return (
    <Card className="p-6 flex flex-col h-full">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div
            className={`p-2 rounded-lg ${
              isRunning ? 'bg-risk-low/10' : 'bg-surfaceHover'
            }`}
          >
            <Activity
              className={`w-5 h-5 ${
                isRunning ? 'text-risk-low animate-pulse' : 'text-textMuted'
              }`}
            />
          </div>
          <div>
            <h2 className="text-base font-semibold text-textMain">
              Simulation Engine
            </h2>
            <p className="text-sm text-textMuted">
              Control the synthetic data generator
            </p>
          </div>
        </div>

        {/* Live status indicator */}
        <div className="flex items-center space-x-2">
          <span className="relative flex h-3 w-3">
            {isRunning && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-risk-low opacity-75" />
            )}
            <span
              className={`relative inline-flex rounded-full h-3 w-3 ${
                isRunning ? 'bg-risk-low' : 'bg-border'
              }`}
            />
          </span>
          <span
            className={`text-sm font-medium uppercase tracking-wider ${
              isRunning ? 'text-risk-low' : 'text-textMuted'
            }`}
          >
            {isRunning ? 'Running' : 'Stopped'}
          </span>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mb-6 p-3 bg-decision-block/10 border border-decision-block/20 rounded-lg flex items-start space-x-2 text-decision-block text-sm">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Control buttons */}
      <div className="grid grid-cols-3 gap-4 mt-auto">

        {/* Start */}
        <button
          onClick={() => handleAction(onStart)}
          disabled={isRunning || isLoading}
          aria-label="Start simulation"
          className={`flex flex-col items-center justify-center py-4 px-2 rounded-lg border transition-all ${
            isRunning || isLoading
              ? 'bg-background border-border text-textMuted cursor-not-allowed opacity-50'
              : 'bg-risk-low/10 border-risk-low/20 text-risk-low hover:bg-risk-low/20 hover:border-risk-low/30'
          }`}
        >
          <Play className="w-6 h-6 mb-2" />
          <span className="text-sm font-medium">Start</span>
        </button>

        {/* Stop */}
        <button
          onClick={() => handleAction(onStop)}
          disabled={!isRunning || isLoading}
          aria-label="Stop simulation"
          className={`flex flex-col items-center justify-center py-4 px-2 rounded-lg border transition-all ${
            !isRunning || isLoading
              ? 'bg-background border-border text-textMuted cursor-not-allowed opacity-50'
              : 'bg-decision-block/10 border-decision-block/20 text-decision-block hover:bg-decision-block/20 hover:border-decision-block/30'
          }`}
        >
          <Square className="w-6 h-6 mb-2" />
          <span className="text-sm font-medium">Stop</span>
        </button>

        {/* Reset — disabled while running since backend rejects it */}
        <button
          onClick={() => handleAction(onReset)}
          disabled={resetDisabled}
          aria-label="Reset ML model"
          title={isRunning ? 'Stop the simulation before resetting' : 'Reset the ML model to untrained state'}
          className={`flex flex-col items-center justify-center py-4 px-2 rounded-lg border transition-all ${
            resetDisabled
              ? 'bg-background border-border text-textMuted cursor-not-allowed opacity-50'
              : 'bg-decision-mfa/10 border-decision-mfa/20 text-decision-mfa hover:bg-decision-mfa/20 hover:border-decision-mfa/30'
          }`}
        >
          <RotateCcw
            className={`w-6 h-6 mb-2 ${isLoading ? 'animate-spin' : ''}`}
          />
          <span className="text-sm font-medium">Reset</span>
        </button>
      </div>
    </Card>
  );
};