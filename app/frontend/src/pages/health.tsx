'use client';

import { useEffect, useState } from 'react';

interface HealthData {
  status: string;
  duration_ms?: number;
  uptime?: number;
  timestamp?: string;
  version?: string;
  checks?: Record<string, { status: string; error?: string }>;
  error?: string;
}

export default function HealthPage() {
  const [data, setData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/health')
      .then((res) => res.json())
      .then((d: HealthData) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setData({ status: 'error', error: 'Failed to fetch' });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div style={{ padding: '2rem', fontFamily: 'system-ui' }}>
        <h1>Health</h1>
        <p>Loading...</p>
      </div>
    );
  }

  const status = data?.status ?? 'unknown';
  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui' }}>
      <h1>Health</h1>
      <p><strong>Status:</strong> {status}</p>
      {data?.error && <p><strong>Error:</strong> {data.error}</p>}
      {data?.timestamp && <p><strong>Timestamp:</strong> {data.timestamp}</p>}
      {data?.checks && (
        <ul>
          {Object.entries(data.checks).map(([name, check]) => (
            <li key={name}>{name}: {check.status}{check.error ? ` (${check.error})` : ''}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
