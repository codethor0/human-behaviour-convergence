import { useEffect, useState } from 'react';
import Link from 'next/link';

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
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24 }}>
      <h1>Behavior Convergence Explorer</h1>
      <p style={{ color: '#555' }}>Public-data-driven behavioral forecasting application.</p>

      <nav style={{ marginBottom: 32, display: 'flex', gap: 16 }}>
        <Link href="/forecast" style={{ textDecoration: 'underline', color: '#0070f3' }}>
          Generate Forecast
        </Link>
        <Link href="/" style={{ textDecoration: 'underline', color: '#0070f3' }}>
          Results Dashboard
        </Link>
      </nav>

      {error && (
        <p style={{ color: 'crimson' }}>Failed to load data: {error}</p>
      )}

      <section>
        <h2>Forecasts (first 10)</h2>
        <DataTable rows={forecasts.slice(0, 10)} emptyMessage="No forecast data" />
      </section>

      <section>
        <h2>Metrics</h2>
        <DataTable rows={metrics} emptyMessage="No metrics data" />
      </section>
    </main>
  );
}

function DataTable({ rows, emptyMessage }: { rows: Record<string, any>[]; emptyMessage?: string }) {
  if (!rows || rows.length === 0) return <p>{emptyMessage || 'No data'}</p>;
  const columns = Array.from(
    rows.reduce((set, r) => {
      Object.keys(r).forEach((k) => set.add(k));
      return set;
    }, new Set<string>())
  );
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
import Head from 'next/head'
import Link from 'next/link'

export default function Home() {
  return (
    <>
      <Head>
        <title>Behavior Convergence Explorer</title>
        <meta name="description" content="Visualize behavior convergence results and diagrams" />
      </Head>
      <main style={{ padding: '2rem', fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>Behavior Convergence Explorer</h1>
        <p style={{ marginBottom: '1.5rem', color: '#555' }}>
          Explore the Mermaid diagram and browse research results from this repository.
        </p>
        <nav style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <Link href="/diagram" style={{ textDecoration: 'underline' }}>Diagram</Link>
          <Link href="/results" style={{ textDecoration: 'underline' }}>Results</Link>
          <a href="https://github.com/thor/human-behaviour-convergence" target="_blank" rel="noreferrer" style={{ textDecoration: 'underline' }}>
            GitHub Repo
          </a>
        </nav>
      </main>
    </>
  )
}
