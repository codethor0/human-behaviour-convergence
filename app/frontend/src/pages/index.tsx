import { useEffect, useState } from 'react';
import Link from 'next/link';
import Head from 'next/head';

type Forecast = Record<string, any>;
type Metric = Record<string, any>;

export default function HomePage() {
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
    Promise.all([
      fetch(`${base}/api/forecasts`).then((r) => r.json()),
      fetch(`${base}/api/metrics`).then((r) => r.json()),
    ])
      .then(([f, m]) => {
        setForecasts(f.data || []);
        setMetrics(m.data || []);
      })
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <>
      <Head>
        <title>Behavior Convergence Explorer</title>
        <meta name="description" content="Public-data-driven behavioral forecasting application" />
      </Head>
      <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 1200, margin: '0 auto' }}>
        <h1>Behavior Convergence Explorer</h1>
        <p style={{ color: '#555', marginBottom: 24 }}>
          Public-data-driven behavioral forecasting application using economic and environmental signals.
        </p>

        <nav style={{ marginBottom: 32, display: 'flex', gap: 16 }}>
          <Link href="/forecast" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Generate Forecast
          </Link>
          <Link href="/" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Results Dashboard
          </Link>
        </nav>

        {error && (
          <section style={{ padding: 16, backgroundColor: '#f8d7da', color: '#721c24', borderRadius: 4, marginBottom: 24 }}>
            <strong>Error:</strong> {error}
          </section>
        )}

        <section style={{ marginBottom: 32 }}>
          <h2>Recent Forecasts (first 10)</h2>
          <DataTable rows={forecasts.slice(0, 10)} emptyMessage="No forecast data available" />
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2>Metrics</h2>
          <DataTable rows={metrics} emptyMessage="No metrics data available" />
        </section>
      </main>
    </>
  );
}

function DataTable({ rows, emptyMessage }: { rows: Record<string, any>[]; emptyMessage?: string }) {
  if (!rows || rows.length === 0) return <p>{emptyMessage || 'No data'}</p>;
  const columnSet = rows.reduce<Set<string>>((set, r) => {
    Object.keys(r).forEach((k) => set.add(k));
    return set;
  }, new Set<string>());
  const columns = Array.from(columnSet);
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', minWidth: 600 }}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} style={{ borderBottom: '1px solid #ddd', textAlign: 'left', padding: '6px 8px' }}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c} style={{ borderBottom: '1px solid #f0f0f0', padding: '6px 8px', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace' }}>
                  {String(r[c] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
