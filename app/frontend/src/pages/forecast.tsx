import { useState, useEffect } from 'react';
import Head from 'next/head';

interface ForecastRequest {
  latitude: number;
  longitude: number;
  region_name: string;
  days_back: number;
  forecast_horizon: number;
}

interface ForecastResponse {
  history: Array<{ timestamp: string; behavior_index: number }>;
  forecast: Array<{ timestamp: string; prediction: number; lower_bound: number; upper_bound: number }>;
  sources: string[];
  metadata: Record<string, any>;
}

const PRESET_REGIONS = [
  { name: 'New York City', lat: 40.7128, lon: -74.0060 },
  { name: 'London', lat: 51.5074, lon: -0.1278 },
  { name: 'Tokyo', lat: 35.6762, lon: 139.6503 },
];

export default function ForecastPage() {
  const [selectedRegion, setSelectedRegion] = useState(PRESET_REGIONS[0]);
  const [daysBack, setDaysBack] = useState(30);
  const [forecastHorizon, setForecastHorizon] = useState(7);
  const [loading, setLoading] = useState(false);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dataSources, setDataSources] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);

  const fetchDataSources = async () => {
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
      const response = await fetch(`${base}/api/forecasting/data-sources`);
      const data = await response.json();
      setDataSources(data);
    } catch (e) {
      console.error('Failed to fetch data sources:', e);
    }
  };

  const fetchModels = async () => {
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
      const response = await fetch(`${base}/api/forecasting/models`);
      const data = await response.json();
      setModels(data);
    } catch (e) {
      console.error('Failed to fetch models:', e);
    }
  };

  const runForecast = async () => {
    setLoading(true);
    setError(null);
    setForecastData(null);

    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
      const request: ForecastRequest = {
        latitude: selectedRegion.lat,
        longitude: selectedRegion.lon,
        region_name: selectedRegion.name,
        days_back: daysBack,
        forecast_horizon: forecastHorizon,
      };

      const response = await fetch(`${base}/api/forecast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Forecast request failed');
      }

      const data: ForecastResponse = await response.json();
      setForecastData(data);
    } catch (e: any) {
      setError(e.message || 'Failed to generate forecast');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDataSources();
    fetchModels();
  }, []);

  return (
    <>
      <Head>
        <title>Behavior Forecast - Behavior Convergence Explorer</title>
      </Head>
      <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 1200, margin: '0 auto' }}>
        <h1>Behavior Forecast</h1>
        <p style={{ color: '#555', marginBottom: 24 }}>
          Generate behavioral forecasts using public economic and environmental data.
        </p>

        <section style={{ marginBottom: 32, padding: 20, border: '1px solid #ddd', borderRadius: 8 }}>
          <h2 style={{ marginTop: 0 }}>Forecast Configuration</h2>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 'bold' }}>
              Region:
            </label>
            <select
              value={selectedRegion.name}
              onChange={(e) => {
                const region = PRESET_REGIONS.find((r) => r.name === e.target.value) || PRESET_REGIONS[0];
                setSelectedRegion(region);
              }}
              style={{ padding: 8, fontSize: 14, minWidth: 200 }}
            >
              {PRESET_REGIONS.map((r) => (
                <option key={r.name} value={r.name}>
                  {r.name} ({r.lat}, {r.lon})
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 'bold' }}>
              Historical Days: {daysBack}
            </label>
            <input
              type="range"
              min="7"
              max="365"
              value={daysBack}
              onChange={(e) => setDaysBack(parseInt(e.target.value))}
              style={{ width: '100%', maxWidth: 400 }}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 'bold' }}>
              Forecast Horizon (days): {forecastHorizon}
            </label>
            <input
              type="range"
              min="1"
              max="30"
              value={forecastHorizon}
              onChange={(e) => setForecastHorizon(parseInt(e.target.value))}
              style={{ width: '100%', maxWidth: 400 }}
            />
          </div>

          <button
            onClick={runForecast}
            disabled={loading}
            style={{
              padding: '12px 24px',
              fontSize: 16,
              backgroundColor: loading ? '#ccc' : '#0070f3',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Generating Forecast...' : 'Generate Forecast'}
          </button>
        </section>

        {dataSources.length > 0 && (
          <section style={{ marginBottom: 32 }}>
            <h2>Available Data Sources</h2>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {dataSources.map((source) => (
                <div
                  key={source.name}
                  style={{
                    padding: 12,
                    border: '1px solid #ddd',
                    borderRadius: 4,
                    minWidth: 200,
                  }}
                >
                  <strong>{source.name.replace('_', ' ')}</strong>
                  <p style={{ margin: '8px 0 0 0', fontSize: 14, color: '#666' }}>
                    {source.description}
                  </p>
                  <span
                    style={{
                      display: 'inline-block',
                      marginTop: 8,
                      padding: '4px 8px',
                      backgroundColor: source.status === 'active' ? '#d4edda' : '#f8d7da',
                      color: source.status === 'active' ? '#155724' : '#721c24',
                      borderRadius: 4,
                      fontSize: 12,
                    }}
                  >
                    {source.status}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {error && (
          <section style={{ padding: 16, backgroundColor: '#f8d7da', color: '#721c24', borderRadius: 4, marginBottom: 24 }}>
            <strong>Error:</strong> {error}
          </section>
        )}

        {forecastData && (
          <section>
            <h2>Forecast Results</h2>

            {forecastData.metadata && (
              <div style={{ marginBottom: 24, padding: 16, backgroundColor: '#f8f9fa', borderRadius: 4 }}>
                <h3 style={{ marginTop: 0 }}>Metadata</h3>
                <p><strong>Region:</strong> {forecastData.metadata.region_name}</p>
                <p><strong>Model:</strong> {forecastData.metadata.model_type || 'Unknown'}</p>
                <p><strong>Forecast Date:</strong> {forecastData.metadata.forecast_date}</p>
                <p><strong>Historical Data Points:</strong> {forecastData.metadata.historical_data_points || 0}</p>
              </div>
            )}

            {forecastData.sources && forecastData.sources.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <strong>Data Sources:</strong>{' '}
                {forecastData.sources.join(', ')}
              </div>
            )}

            {forecastData.history && forecastData.history.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <h3>Historical Data ({forecastData.history.length} points)</h3>
                <div style={{ overflowX: 'auto', maxHeight: 300, overflowY: 'auto' }}>
                  <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 14 }}>
                    <thead>
                      <tr style={{ backgroundColor: '#f8f9fa', position: 'sticky', top: 0 }}>
                        <th style={{ padding: 8, textAlign: 'left', borderBottom: '2px solid #ddd' }}>Date</th>
                        <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Behavior Index</th>
                      </tr>
                    </thead>
                    <tbody>
                      {forecastData.history.slice(-10).map((item, i) => (
                        <tr key={i}>
                          <td style={{ padding: 8, borderBottom: '1px solid #eee' }}>{item.timestamp}</td>
                          <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee' }}>
                            {item.behavior_index.toFixed(3)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {forecastData.forecast && forecastData.forecast.length > 0 && (
              <div>
                <h3>Forecast ({forecastData.forecast.length} days ahead)</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 14 }}>
                    <thead>
                      <tr style={{ backgroundColor: '#f8f9fa' }}>
                        <th style={{ padding: 8, textAlign: 'left', borderBottom: '2px solid #ddd' }}>Date</th>
                        <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Prediction</th>
                        <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Lower Bound</th>
                        <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Upper Bound</th>
                      </tr>
                    </thead>
                    <tbody>
                      {forecastData.forecast.map((item, i) => (
                        <tr key={i}>
                          <td style={{ padding: 8, borderBottom: '1px solid #eee' }}>{item.timestamp}</td>
                          <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee', fontWeight: 'bold' }}>
                            {item.prediction.toFixed(3)}
                          </td>
                          <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee', color: '#666' }}>
                            {item.lower_bound.toFixed(3)}
                          </td>
                          <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee', color: '#666' }}>
                            {item.upper_bound.toFixed(3)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {forecastData.history && forecastData.history.length === 0 && forecastData.forecast && forecastData.forecast.length === 0 && (
              <p style={{ color: '#666' }}>No forecast data available. Check error message or try different parameters.</p>
            )}
          </section>
        )}

        <section style={{ marginTop: 48, padding: 16, backgroundColor: '#e7f3ff', borderRadius: 4 }}>
          <p style={{ margin: 0, fontSize: 14 }}>
            <strong>Status:</strong> Live Public Data Connection{' '}
            <span style={{ color: dataSources.some((s) => s.status === 'active') ? '#28a745' : '#dc3545' }}>
              {dataSources.some((s) => s.status === 'active') ? 'Active' : 'Inactive'}
            </span>
          </p>
        </section>
      </main>
    </>
  );
}
