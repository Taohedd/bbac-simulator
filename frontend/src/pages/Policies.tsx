import React, { useEffect, useState, useCallback } from 'react';
import {
  Shield, Plus, Edit2, Trash2,
  CheckCircle2, AlertCircle, X, Save,
} from 'lucide-react';
import { api } from '../api/client';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Policy } from '../types';

// Form state — matches CreatePolicyPayload in api/client.ts exactly.
// The real backend policy model is a TWO-THRESHOLD system: name, low_threshold,
// high_threshold, is_active. There is no description or rules-engine concept.
interface PolicyFormState {
  name: string;
  low_threshold: number;
  high_threshold: number;
  is_active: boolean;
}

const DEFAULT_FORM: PolicyFormState = {
  name:           '',
  low_threshold:  30,
  high_threshold: 70,
  is_active:      false,
};

export const Policies: React.FC = () => {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
  const [formData, setFormData] = useState<PolicyFormState>(DEFAULT_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchPolicies = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Use namespaced api object — api.get() does not exist
      const data = await api.policies.getAll();
      setPolicies(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch policies');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { void fetchPolicies(); }, [fetchPolicies]);

  // Close modal on Escape
  useEffect(() => {
    if (!isModalOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') handleCloseModal(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isModalOpen]);

  const handleOpenModal = (policy?: Policy) => {
    setFormError(null);
    if (policy) {
      setEditingPolicy(policy);
      setFormData({
        name:           policy.name,
        low_threshold:  policy.low_threshold,
        high_threshold: policy.high_threshold,
        is_active:      policy.is_active,
      });
    } else {
      setEditingPolicy(null);
      setFormData(DEFAULT_FORM);
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingPolicy(null);
    setFormError(null);
  };

  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    // Client-side threshold validation (mirrors the backend CHECK constraint)
    if (formData.low_threshold >= formData.high_threshold) {
      setFormError(
        `Low threshold (${formData.low_threshold}) must be strictly less than high threshold (${formData.high_threshold}).`
      );
      return;
    }

    setIsSaving(true);
    try {
      if (editingPolicy) {
        await api.policies.update(editingPolicy.id, formData);
      } else {
        await api.policies.create(formData);
      }
      await fetchPolicies();
      handleCloseModal();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to save policy');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeletePolicy = async (id: string) => {
    if (!window.confirm('Delete this policy? This cannot be undone.')) return;
    setDeleteError(null);
    try {
      await api.policies.delete(id);
      await fetchPolicies();
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete policy');
    }
  };

  const handleSetActive = async (id: string) => {
    try {
      // The backend _deactivate_all_policies() handles deactivating others.
      // We only need to PATCH is_active=true on the chosen policy.
      await api.policies.update(id, { is_active: true });
      await fetchPolicies();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to activate policy');
    }
  };

  return (
    <div className="space-y-6 h-full flex flex-col">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-surfaceHover rounded-lg border border-border">
            <Shield className="w-5 h-5 text-textMuted" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-textMain">Access Policies</h2>
            <p className="text-sm text-textMuted">
              Configure risk score thresholds for ALLOW / MFA / BLOCK decisions
            </p>
          </div>
        </div>
        <button
          onClick={() => handleOpenModal()}
          className="flex items-center space-x-2 px-4 py-2 bg-risk-low/10 hover:bg-risk-low/20 text-risk-low text-sm font-medium rounded-lg border border-risk-low/20 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Create Policy</span>
        </button>
      </div>

      {/* Errors */}
      {error && (
        <div className="p-4 bg-decision-block/10 border border-decision-block/20 rounded-lg flex items-start space-x-3 text-decision-block">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <p className="text-sm">{error}</p>
        </div>
      )}
      {deleteError && (
        <div className="p-4 bg-decision-block/10 border border-decision-block/20 rounded-lg flex items-start space-x-3 text-decision-block">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <p className="text-sm">{deleteError}</p>
        </div>
      )}

      {/* Policy grid */}
      {isLoading ? (
        <div className="flex-1 flex flex-col items-center justify-center text-textMuted space-y-4">
          <div className="w-8 h-8 border-4 border-border border-t-risk-low rounded-full animate-spin" />
          <p className="text-sm">Loading policies...</p>
        </div>
      ) : policies.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-textMuted bg-surface/50 rounded-lg border border-border p-8">
          <Shield className="w-12 h-12 mb-4 text-border" />
          <p className="text-base font-medium text-textMain">No policies found</p>
          <p className="text-sm mt-1">Create a policy to start evaluating risk scores.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {policies.map((policy) => (
            <Card
              key={policy.id}
              className={`flex flex-col transition-all duration-300 ${
                policy.is_active
                  ? 'border-risk-low/40 bg-surface'
                  : 'border-border bg-background hover:border-surfaceHover'
              }`}
            >
              <div className="p-5 flex flex-col flex-1">

                {/* Name + status */}
                <div className="flex items-start justify-between mb-4">
                  <h3
                    className="text-base font-semibold text-textMain truncate pr-2"
                    title={policy.name}
                  >
                    {policy.name}
                  </h3>
                  {policy.is_active ? (
                    <Badge variant="low" className="shrink-0 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Active
                    </Badge>
                  ) : (
                    <Badge variant="default" className="shrink-0">Inactive</Badge>
                  )}
                </div>

                {/* Threshold visualisation — the core of what this policy actually does */}
                <div className="bg-background rounded-lg p-4 border border-border mb-4 space-y-3">
                  <p className="text-xs font-medium text-textMuted uppercase tracking-wider">
                    Risk Thresholds
                  </p>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-md bg-risk-low/10 border border-risk-low/20 px-2 py-2">
                      <p className="text-xs text-textMuted">ALLOW</p>
                      <p className="text-sm font-bold text-risk-low font-mono">
                        0 – {policy.low_threshold}
                      </p>
                    </div>
                    <div className="rounded-md bg-risk-medium/10 border border-risk-medium/20 px-2 py-2">
                      <p className="text-xs text-textMuted">MFA</p>
                      <p className="text-sm font-bold text-risk-medium font-mono">
                        {policy.low_threshold} – {policy.high_threshold}
                      </p>
                    </div>
                    <div className="rounded-md bg-risk-high/10 border border-risk-high/20 px-2 py-2">
                      <p className="text-xs text-textMuted">BLOCK</p>
                      <p className="text-sm font-bold text-risk-high font-mono">
                        {policy.high_threshold} – 100
                      </p>
                    </div>
                  </div>
                  <p className="text-xs text-textMuted font-mono">
                    Created: {new Date(policy.created_at).toLocaleDateString()}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between pt-3 border-t border-border mt-auto">
                  {!policy.is_active ? (
                    <button
                      onClick={() => handleSetActive(policy.id)}
                      className="text-sm font-medium text-risk-low hover:text-risk-low/80 transition-colors"
                    >
                      Set Active
                    </button>
                  ) : (
                    <span className="text-sm text-textMuted">Currently Active</span>
                  )}

                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => handleOpenModal(policy)}
                      title="Edit Policy"
                      className="p-2 text-textMuted hover:text-textMain hover:bg-surfaceHover rounded-md transition-colors"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeletePolicy(policy.id)}
                      disabled={policy.is_active}
                      title={policy.is_active ? 'Cannot delete the active policy' : 'Delete Policy'}
                      className="p-2 text-textMuted hover:text-decision-block hover:bg-decision-block/10 rounded-md transition-colors disabled:opacity-30 disabled:pointer-events-none"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Create / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
          <div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={handleCloseModal}
            aria-hidden="true"
          />
          <div className="relative w-full max-w-md bg-surface border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden">

            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-base font-semibold text-textMain">
                {editingPolicy ? 'Edit Policy' : 'Create New Policy'}
              </h2>
              <button
                onClick={handleCloseModal}
                className="p-2 text-textMuted hover:text-textMain hover:bg-surfaceHover rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSavePolicy} className="p-6 space-y-5">
              {formError && (
                <div className="p-3 bg-decision-block/10 border border-decision-block/20 rounded-lg text-sm text-decision-block flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                  {formError}
                </div>
              )}

              {/* Policy Name */}
              <div>
                <label className="block text-sm font-medium text-textMain mb-1.5">
                  Policy Name <span className="text-decision-block">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
                  placeholder="e.g., Strict MFA Policy"
                  className="block w-full px-3 py-2 border border-border rounded-lg bg-background text-textMain placeholder-textMuted focus:outline-none focus:ring-1 focus:ring-border text-sm"
                />
              </div>

              {/* Thresholds — the ONLY configurable values on this model */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-textMain mb-1.5">
                    Low Threshold
                    <span className="ml-1 text-xs text-textMuted">(ALLOW below this)</span>
                  </label>
                  <input
                    type="number"
                    required
                    min="0"
                    max="99"
                    value={formData.low_threshold}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, low_threshold: Number(e.target.value) }))
                    }
                    className="block w-full px-3 py-2 border border-border rounded-lg bg-background text-textMain text-sm font-mono focus:outline-none focus:ring-1 focus:ring-border"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-textMain mb-1.5">
                    High Threshold
                    <span className="ml-1 text-xs text-textMuted">(BLOCK at or above)</span>
                  </label>
                  <input
                    type="number"
                    required
                    min="1"
                    max="100"
                    value={formData.high_threshold}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, high_threshold: Number(e.target.value) }))
                    }
                    className="block w-full px-3 py-2 border border-border rounded-lg bg-background text-textMain text-sm font-mono focus:outline-none focus:ring-1 focus:ring-border"
                  />
                </div>
              </div>

              {/* MFA zone preview */}
              <p className="text-xs text-textMuted bg-background rounded-lg border border-border px-3 py-2 font-mono">
                MFA zone: {formData.low_threshold} – {formData.high_threshold - 1}
                &nbsp;·&nbsp;
                BLOCK at or above {formData.high_threshold}
              </p>

              {/* Set Active */}
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) =>
                    setFormData((f) => ({ ...f, is_active: e.target.checked }))
                  }
                  className="w-4 h-4 rounded border-border accent-current text-risk-low"
                />
                <label htmlFor="is_active" className="text-sm text-textMain">
                  Set as active policy
                  <span className="block text-xs text-textMuted mt-0.5">
                    This will deactivate any currently active policy.
                  </span>
                </label>
              </div>

              {/* Actions */}
              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="px-4 py-2 text-sm font-medium text-textMuted hover:text-textMain bg-surfaceHover hover:bg-border rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="flex items-center px-4 py-2 text-sm font-medium text-textMain bg-risk-low/10 hover:bg-risk-low/20 border border-risk-low/20 rounded-lg transition-colors disabled:opacity-50"
                >
                  {isSaving ? (
                    <div className="w-4 h-4 border-2 border-textMuted border-t-textMain rounded-full animate-spin mr-2" />
                  ) : (
                    <Save className="w-4 h-4 mr-2" />
                  )}
                  {editingPolicy ? 'Save Changes' : 'Create Policy'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};