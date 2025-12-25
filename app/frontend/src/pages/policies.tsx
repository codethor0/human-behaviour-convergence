// SPDX-License-Identifier: PROPRIETARY
/**
 * Policy Management Page
 * 
 * Provides UI for:
 * - Viewing policies
 * - Creating/editing policies
 * - Previewing policy impact
 * - Activating policies
 * 
 * All preview operations are read-only and never mutate state.
 */
import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { API_BASE } from '@/lib/api';

interface Policy {
  policy_id: string;
  version: number;
  active: boolean;
  created_by: string;
  created_at: string;
}

interface PreviewResult {
  preview_valid: boolean;
  policy_id: string;
  current_alert_count: number;
  preview_alert_count: number;
  alert_count_delta: number;
  current_severity_distribution: Record<string, number>;
  preview_severity_distribution: Record<string, number>;
  noise_reduction_estimate: number;
  suppressed_alerts: Array<Record<string, any>>;
  new_alerts: Array<Record<string, any>>;
}

interface ImpactDiff {
  alert_count_change: number;
  severity_changes: Record<string, {
    current: number;
    preview: number;
    delta: number;
  }>;
  noise_reduction: number;
  new_alerts_count: number;
  suppressed_alerts_count: number;
}

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPolicy, setSelectedPolicy] = useState<string | null>(null);
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null);
  const [impactDiff, setImpactDiff] = useState<ImpactDiff | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [activating, setActivating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiBase = API_BASE;

  useEffect(() => {
    loadPolicies();
  }, []);

  const loadPolicies = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${apiBase}/api/policies`);
      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new Error(`Failed to load policies: ${response.status} ${errorText}`);
      }
      const data = await response.json();
      setPolicies(data.policies || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load policies';
      setError(errorMessage);
      console.error('Failed to load policies:', err);
      // Set empty array on error so page still renders
      setPolicies([]);
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async (policyId: string) => {
    try {
      setPreviewing(true);
      setError(null);
      
      // Get policy definition (simplified - in production, fetch from API)
      const policy = {
        alert_thresholds: {
          factor_id: 'economic_stress',
          threshold: 0.7,
          direction: 'above',
        },
      };

      const response = await fetch(`${apiBase}/api/policies/${policyId}/preview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          policy,
          tenant_id: 'default',
          user_id: 'current_user',
        }),
      });

      if (!response.ok) {
        throw new Error('Preview failed');
      }

      const data = await response.json();
      if (data.success) {
        setPreviewResult(data.preview);
        setImpactDiff(data.impact_diff);
        setSelectedPolicy(policyId);
      } else {
        throw new Error(data.error || 'Preview failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed');
    } finally {
      setPreviewing(false);
    }
  };

  const handleActivate = async (policyId: string) => {
    if (!previewResult) {
      setError('Policy must be previewed before activation');
      return;
    }

    try {
      setActivating(true);
      setError(null);

      const response = await fetch(`${apiBase}/api/policies/${policyId}/activate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          preview_result: previewResult,
          tenant_id: 'default',
          user_id: 'current_user',
        }),
      });

      if (!response.ok) {
        throw new Error('Activation failed');
      }

      const data = await response.json();
      if (data.success) {
        // Reload policies
        await loadPolicies();
        // Clear preview
        setPreviewResult(null);
        setImpactDiff(null);
        setSelectedPolicy(null);
      } else {
        throw new Error(data.error || 'Activation failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Activation failed');
    } finally {
      setActivating(false);
    }
  };

  return (
    <>
      <Head>
        <title>Policy Management - Behavior Convergence</title>
      </Head>

      <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 1200, margin: '0 auto' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: 24 }}>Policy Management</h1>

        <nav style={{ marginBottom: 32, display: 'flex', gap: 16 }}>
          <Link href="/forecast" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Generate Forecast
          </Link>
          <Link href="/playground" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Live Playground
          </Link>
          <Link href="/live" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Live Monitoring
          </Link>
          <Link href="/policies" style={{ textDecoration: 'underline', color: '#0070f3', fontWeight: 'bold' }}>
            Policy Management
          </Link>
          <Link href="/audit" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Audit Log
          </Link>
          <Link href="/" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Results Dashboard
          </Link>
        </nav>

        {error && (
          <div style={{ padding: 16, backgroundColor: '#f8d7da', color: '#721c24', borderRadius: 4, marginBottom: 24 }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: 'center', padding: '32px 0' }}>Loading policies...</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 24 }}>
            {/* Policies List */}
            <section style={{ backgroundColor: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', borderRadius: 8, padding: 24 }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 16 }}>Policies</h2>
              {policies.length === 0 ? (
                <p style={{ color: '#666' }}>No policies found</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {policies.map((policy) => (
                    <div
                      key={`${policy.policy_id}-${policy.version}`}
                      style={{
                        border: '1px solid #ddd',
                        borderRadius: 4,
                        padding: 16,
                        backgroundColor: selectedPolicy === policy.policy_id ? '#e3f2fd' : '#fff',
                        borderColor: selectedPolicy === policy.policy_id ? '#2196f3' : '#ddd',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <h3 style={{ fontWeight: 600, marginBottom: 4 }}>{policy.policy_id}</h3>
                          <p style={{ fontSize: '0.875rem', color: '#666', marginBottom: 4 }}>
                            Version {policy.version} •{' '}
                            {policy.active ? (
                              <span style={{ color: '#4caf50' }}>Active</span>
                            ) : (
                              <span style={{ color: '#999' }}>Inactive</span>
                            )}
                          </p>
                          <p style={{ fontSize: '0.75rem', color: '#999', marginTop: 4 }}>
                            Created by {policy.created_by} • {new Date(policy.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button
                            onClick={() => handlePreview(policy.policy_id)}
                            disabled={previewing || policy.active}
                            style={{
                              padding: '4px 12px',
                              fontSize: '0.875rem',
                              backgroundColor: previewing || policy.active ? '#ccc' : '#2196f3',
                              color: '#fff',
                              border: 'none',
                              borderRadius: 4,
                              cursor: previewing || policy.active ? 'not-allowed' : 'pointer',
                            }}
                          >
                            {previewing ? 'Previewing...' : 'Preview'}
                          </button>
                          {previewResult && selectedPolicy === policy.policy_id && (
                            <button
                              onClick={() => handleActivate(policy.policy_id)}
                              disabled={activating || policy.active}
                              style={{
                                padding: '4px 12px',
                                fontSize: '0.875rem',
                                backgroundColor: activating || policy.active ? '#ccc' : '#4caf50',
                                color: '#fff',
                                border: 'none',
                                borderRadius: 4,
                                cursor: activating || policy.active ? 'not-allowed' : 'pointer',
                              }}
                            >
                              {activating ? 'Activating...' : 'Activate'}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Preview Panel */}
            <section style={{ backgroundColor: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', borderRadius: 8, padding: 24 }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 16 }}>
                Policy Preview
                {previewResult && (
                  <span style={{ marginLeft: 8, fontSize: '0.875rem', fontWeight: 'normal', color: '#ff9800' }}>
                    (Preview — Not Active)
                  </span>
                )}
              </h2>

              {!previewResult ? (
                <div style={{ color: '#666', textAlign: 'center', padding: '32px 0' }}>
                  Select a policy and click &quot;Preview&quot; to see impact analysis
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {/* Alert Count Delta */}
                  <div style={{ border: '1px solid #ddd', borderRadius: 4, padding: 16 }}>
                    <h3 style={{ fontWeight: 600, marginBottom: 8 }}>Alert Count Impact</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                      <div>
                        <p style={{ fontSize: '0.875rem', color: '#666', marginBottom: 4 }}>Current</p>
                        <p style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{previewResult.current_alert_count}</p>
                      </div>
                      <div>
                        <p style={{ fontSize: '0.875rem', color: '#666', marginBottom: 4 }}>Preview</p>
                        <p style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{previewResult.preview_alert_count}</p>
                      </div>
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <p style={{ fontSize: '0.875rem' }}>
                        Change:{' '}
                        <span
                          style={{
                            fontWeight: 600,
                            color:
                              previewResult.alert_count_delta > 0
                                ? '#f44336'
                                : previewResult.alert_count_delta < 0
                                ? '#4caf50'
                                : '#666',
                          }}
                        >
                          {previewResult.alert_count_delta > 0 ? '+' : ''}
                          {previewResult.alert_count_delta}
                        </span>
                      </p>
                    </div>
                  </div>

                  {/* Impact Diff */}
                  {impactDiff && (
                    <div style={{ border: '1px solid #ddd', borderRadius: 4, padding: 16 }}>
                      <h3 style={{ fontWeight: 600, marginBottom: 8 }}>Impact Summary</h3>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        <div>
                          <p style={{ fontSize: '0.875rem', color: '#666', marginBottom: 4 }}>Noise Reduction</p>
                          <p style={{ fontSize: '1.125rem', fontWeight: 600, color: '#4caf50' }}>
                            {impactDiff.noise_reduction} alerts suppressed
                          </p>
                        </div>
                        <div>
                          <p style={{ fontSize: '0.875rem', color: '#666', marginBottom: 4 }}>New Alerts</p>
                          <p style={{ fontSize: '1.125rem', fontWeight: 600 }}>
                            {impactDiff.new_alerts_count} alerts would be created
                          </p>
                        </div>
                        {Object.keys(impactDiff.severity_changes).length > 0 && (
                          <div>
                            <p style={{ fontSize: '0.875rem', color: '#666', marginBottom: 4 }}>Severity Changes</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              {Object.entries(impactDiff.severity_changes).map(([severity, change]) => (
                                <div key={severity} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                                  <span style={{ textTransform: 'capitalize' }}>{severity}:</span>
                                  <span
                                    style={{
                                      color: change.delta > 0 ? '#f44336' : change.delta < 0 ? '#4caf50' : '#666',
                                    }}
                                  >
                                    {change.delta > 0 ? '+' : ''}
                                    {change.delta} ({change.current} → {change.preview})
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Activation Warning */}
                  <div style={{ backgroundColor: '#fff9c4', border: '1px solid #ffc107', borderRadius: 4, padding: 16 }}>
                    <p style={{ fontSize: '0.875rem', color: '#856404' }}>
                      <strong>Note:</strong> This is a preview. The policy is not yet active.
                      Click &quot;Activate&quot; to apply this policy.
                    </p>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}
      </main>
    </>
  );
}
