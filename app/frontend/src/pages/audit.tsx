// SPDX-License-Identifier: PROPRIETARY
/**
 * Audit Log Viewer Page
 *
 * Provides read-only UI for viewing policy audit logs:
 * - Policy changes (create, update, activate, deactivate, rollback)
 * - Preview vs activation trail
 * - Filter by tenant, user, action, time
 *
 * All operations are read-only. No mutations allowed.
 */
import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { API_BASE } from '@/lib/api';

interface AuditLog {
  action: string;
  policy_id: string;
  tenant_id: string;
  user_id: string;
  timestamp: string;
  version?: number;
}

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    policy_id: '',
    action: '',
    user_id: '',
  });

  const apiBase = API_BASE;

  useEffect(() => {
    loadAuditLogs();
  }, [filters]);

  const loadAuditLogs = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (filters.policy_id) params.append('policy_id', filters.policy_id);
      if (filters.action) params.append('action', filters.action);
      if (filters.user_id) params.append('user_id', filters.user_id);

      const response = await fetch(`${apiBase}/api/audit?${params.toString()}`);
      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new Error(`Failed to load audit logs: ${response.status} ${errorText}`);
      }
      const data = await response.json();
      setLogs(data.logs || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load audit logs';
      setError(errorMessage);
      console.error('Failed to load audit logs:', err);
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  const actionColors: Record<string, string> = {
    create: '#4caf50',
    update: '#2196f3',
    activate: '#ff9800',
    deactivate: '#f44336',
    rollback: '#9c27b0',
    preview: '#00bcd4',
  };

  const actionLabels: Record<string, string> = {
    create: 'Created',
    update: 'Updated',
    activate: 'Activated',
    deactivate: 'Deactivated',
    rollback: 'Rolled Back',
    preview: 'Previewed',
  };

  return (
    <>
      <Head>
        <title>Audit Log - Behavior Convergence</title>
      </Head>

      <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 1400, margin: '0 auto' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: 24 }}>Audit Log</h1>

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
          <Link href="/policies" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Policy Management
          </Link>
          <Link href="/audit" style={{ textDecoration: 'underline', color: '#0070f3', fontWeight: 'bold' }}>
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

        {/* Filters */}
        <section style={{ backgroundColor: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', borderRadius: 8, padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 16 }}>Filters</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: 4 }}>
                Policy ID
              </label>
              <input
                type="text"
                value={filters.policy_id}
                onChange={(e) => setFilters({ ...filters, policy_id: e.target.value })}
                placeholder="Filter by policy..."
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #ddd',
                  borderRadius: 4,
                  fontSize: '0.875rem',
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: 4 }}>
                Action
              </label>
              <select
                value={filters.action}
                onChange={(e) => setFilters({ ...filters, action: e.target.value })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #ddd',
                  borderRadius: 4,
                  fontSize: '0.875rem',
                }}
              >
                <option value="">All Actions</option>
                <option value="create">Create</option>
                <option value="update">Update</option>
                <option value="activate">Activate</option>
                <option value="deactivate">Deactivate</option>
                <option value="rollback">Rollback</option>
                <option value="preview">Preview</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: 4 }}>
                User ID
              </label>
              <input
                type="text"
                value={filters.user_id}
                onChange={(e) => setFilters({ ...filters, user_id: e.target.value })}
                placeholder="Filter by user..."
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #ddd',
                  borderRadius: 4,
                  fontSize: '0.875rem',
                }}
              />
            </div>
          </div>
        </section>

        {/* Audit Log Table */}
        <section style={{ backgroundColor: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', borderRadius: 8, padding: 24 }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 16 }}>
            Audit Trail ({logs.length} entries)
          </h2>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '32px 0' }}>Loading audit logs...</div>
          ) : logs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#666' }}>
              No audit logs found
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #ddd' }}>
                    <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600 }}>Timestamp</th>
                    <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600 }}>Action</th>
                    <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600 }}>Policy ID</th>
                    <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600 }}>Version</th>
                    <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600 }}>User</th>
                    <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600 }}>Tenant</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, index) => (
                    <tr
                      key={`${log.timestamp}-${index}`}
                      style={{
                        borderBottom: '1px solid #eee',
                        backgroundColor: index % 2 === 0 ? '#fff' : '#f9f9f9',
                      }}
                    >
                      <td style={{ padding: '12px 8px' }}>
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td style={{ padding: '12px 8px' }}>
                        <span
                          style={{
                            display: 'inline-block',
                            padding: '4px 8px',
                            borderRadius: 4,
                            backgroundColor: actionColors[log.action] || '#666',
                            color: '#fff',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            textTransform: 'uppercase',
                          }}
                        >
                          {actionLabels[log.action] || log.action}
                        </span>
                      </td>
                      <td style={{ padding: '12px 8px', fontFamily: 'monospace' }}>
                        {log.policy_id}
                      </td>
                      <td style={{ padding: '12px 8px' }}>
                        {log.version ? `v${log.version}` : '-'}
                      </td>
                      <td style={{ padding: '12px 8px' }}>{log.user_id}</td>
                      <td style={{ padding: '12px 8px' }}>{log.tenant_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Read-only Notice */}
        <div style={{ marginTop: 24, padding: 16, backgroundColor: '#e3f2fd', border: '1px solid #2196f3', borderRadius: 4 }}>
          <p style={{ fontSize: '0.875rem', color: '#1565c0', margin: 0 }}>
            <strong>Note:</strong> This audit log is read-only. All policy actions are automatically logged and cannot be modified or deleted.
          </p>
        </div>
      </main>
    </>
  );
}
