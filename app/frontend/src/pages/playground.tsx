import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';

interface Region {
  id: string;
  name: string;
  country: string;
  region_type: string;
  latitude: number;
  longitude: number;
  region_group?: string;
}

interface ForecastResponse {
  history: Array<Record<string, unknown>>;
  forecast: Array<Record<string, unknown>>;
  sources: string[];
  metadata: Record<string, unknown>;
  explanations?: Record<string, unknown>;
}

interface PlaygroundResult {
  region_id: string;
  region_name: string;
  forecast: ForecastResponse;
  explanations?: Record<string, unknown>;
  scenario_applied?: boolean;
  scenario_description?: string;
}

interface PlaygroundResponse {
  config: {
    historical_days: number;
    forecast_horizon_days: number;
    include_explanations: boolean;
    scenario_applied: boolean;
  };
  results: PlaygroundResult[];
  errors: Array<{ region_id: string; error: string }>;
}

export default function PlaygroundPage() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);
  const [daysBack, setDaysBack] = useState(30);
  const [forecastHorizon, setForecastHorizon] = useState(7);
  const [includeExplanations, setIncludeExplanations] = useState(true);
  const [scenario, setScenario] = useState<{
    economic_stress_offset?: number;
    environmental_stress_offset?: number;
    mobility_activity_offset?: number;
    digital_attention_offset?: number;
    public_health_stress_offset?: number;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [playgroundData, setPlaygroundData] = useState<PlaygroundResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchRegions = async () => {
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8100';
      const response = await fetch(`${base}/api/forecasting/regions`);
      const data = await response.json();
      setRegions(data);
      // Set default selections
      const defaultIds = ['us_dc', 'us_mn', 'city_nyc'].filter(id =>
        data.some((r: Region) => r.id === id)
      );
      if (defaultIds.length > 0) {
        setSelectedRegions(defaultIds);
      }
    } catch (e) {
      console.error('Failed to fetch regions:', e);
      setError('Failed to load regions');
    }
  };

  const runComparison = async () => {
    if (selectedRegions.length === 0) {
      setError('Please select at least one region');
      return;
    }

    setLoading(true);
    setError(null);
    setPlaygroundData(null);

    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8100';
      const request: {
        regions: string[];
        historical_days: number;
        forecast_horizon_days: number;
        include_explanations: boolean;
        scenario?: Record<string, number>;
      } = {
        regions: selectedRegions,
        historical_days: daysBack,
        forecast_horizon_days: forecastHorizon,
        include_explanations: includeExplanations,
      };

      if (scenario && Object.keys(scenario).length > 0) {
        request.scenario = scenario;
      }

      const response = await fetch(`${base}/api/playground/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Playground comparison failed');
      }

      const data: PlaygroundResponse = await response.json();
      setPlaygroundData(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to generate comparison');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRegions();
  }, []);

  return (
    <>
      <Head>
        <title>Playground - Behavior Convergence Explorer</title>
      </Head>
      <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 1400, margin: '0 auto' }}>
        <h1>Live Playground</h1>
        <p style={{ color: '#555', marginBottom: 24 }}>
          Compare behavioral forecasts across multiple regions and explore "what-if" scenarios.
          <strong style={{ display: 'block', marginTop: 8, color: '#dc3545' }}>
            Experimental Feature: Scenario adjustments are post-processing transformations for exploration only.
          </strong>
        </p>

        <nav style={{ marginBottom: 32, display: 'flex', gap: 16 }}>
          <Link href="/forecast" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Single Forecast
          </Link>
          <Link href="/live" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Live Monitoring
          </Link>
          <Link href="/" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Results Dashboard
          </Link>
        </nav>

        <section style={{ marginBottom: 32, padding: 20, border: '1px solid #ddd', borderRadius: 8, backgroundColor: '#f8f9fa' }}>
          <h2 style={{ marginTop: 0 }}>Configuration</h2>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 'bold' }}>
              Select Regions (multi-select):
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8, maxHeight: 200, overflowY: 'auto', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}>
              {regions.map((region) => (
                <label key={region.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={selectedRegions.includes(region.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedRegions([...selectedRegions, region.id]);
                      } else {
                        setSelectedRegions(selectedRegions.filter(id => id !== region.id));
                      }
                    }}
                  />
                  <span style={{ fontSize: 14 }}>{region.name}</span>
                </label>
              ))}
            </div>
            <p style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              Selected: {selectedRegions.length} region{selectedRegions.length !== 1 ? 's' : ''}
            </p>
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

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={includeExplanations}
                onChange={(e) => setIncludeExplanations(e.target.checked)}
              />
              <span>Include Explanations</span>
            </label>
          </div>

          <div style={{ marginBottom: 16, padding: 16, backgroundColor: '#fff3cd', borderRadius: 4, border: '1px solid #ffc107' }}>
            <h3 style={{ marginTop: 0, fontSize: 16 }}>Optional Scenario Adjustments (Experimental)</h3>
            <p style={{ fontSize: 12, color: '#856404', marginBottom: 12 }}>
              These adjustments are post-processing transformations for exploration only. They do not affect the underlying forecasting model.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, marginBottom: 4 }}>
                  Economic Stress Offset:
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="-1"
                  max="1"
                  value={scenario?.economic_stress_offset || ''}
                  onChange={(e) => {
                    const val = e.target.value ? parseFloat(e.target.value) : undefined;
                    setScenario(prev => ({
                      ...prev,
                      economic_stress_offset: val,
                    }));
                  }}
                  placeholder="0.0"
                  style={{ width: '100%', padding: 4, fontSize: 12 }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, marginBottom: 4 }}>
                  Environmental Stress Offset:
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="-1"
                  max="1"
                  value={scenario?.environmental_stress_offset || ''}
                  onChange={(e) => {
                    const val = e.target.value ? parseFloat(e.target.value) : undefined;
                    setScenario(prev => ({
                      ...prev,
                      environmental_stress_offset: val,
                    }));
                  }}
                  placeholder="0.0"
                  style={{ width: '100%', padding: 4, fontSize: 12 }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, marginBottom: 4 }}>
                  Digital Attention Offset:
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="-1"
                  max="1"
                  value={scenario?.digital_attention_offset || ''}
                  onChange={(e) => {
                    const val = e.target.value ? parseFloat(e.target.value) : undefined;
                    setScenario(prev => ({
                      ...prev,
                      digital_attention_offset: val,
                    }));
                  }}
                  placeholder="0.0"
                  style={{ width: '100%', padding: 4, fontSize: 12 }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, marginBottom: 4 }}>
                  Public Health Stress Offset:
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="-1"
                  max="1"
                  value={scenario?.public_health_stress_offset || ''}
                  onChange={(e) => {
                    const val = e.target.value ? parseFloat(e.target.value) : undefined;
                    setScenario(prev => ({
                      ...prev,
                      public_health_stress_offset: val,
                    }));
                  }}
                  placeholder="0.0"
                  style={{ width: '100%', padding: 4, fontSize: 12 }}
                />
              </div>
            </div>
            <button
              onClick={() => setScenario(null)}
              style={{
                marginTop: 12,
                padding: '6px 12px',
                fontSize: 12,
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              Clear Scenario
            </button>
          </div>

          <button
            onClick={runComparison}
            disabled={loading || selectedRegions.length === 0}
            style={{
              padding: '12px 24px',
              fontSize: 16,
              backgroundColor: loading || selectedRegions.length === 0 ? '#ccc' : '#0070f3',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              cursor: loading || selectedRegions.length === 0 ? 'not-allowed' : 'pointer',
            }}
            data-testid="playground-compare-button"
          >
            {loading ? 'Generating Comparison...' : 'Compare Regions'}
          </button>
        </section>

        {error && (
          <section style={{ padding: 16, backgroundColor: '#f8d7da', color: '#721c24', borderRadius: 4, marginBottom: 24 }}>
            <strong>Error:</strong> {error}
          </section>
        )}

        {playgroundData && (
          <section data-testid="playground-results">
            <h2>Comparison Results</h2>

            {playgroundData.config.scenario_applied && (
              <div style={{ marginBottom: 24, padding: 16, backgroundColor: '#fff3cd', borderRadius: 4, border: '1px solid #ffc107' }}>
                <strong>Scenario Applied:</strong> Hypothetical what-if adjustments are active. Results show adjusted values for exploration purposes.
              </div>
            )}

            {playgroundData.errors && playgroundData.errors.length > 0 && (
              <div style={{ marginBottom: 24, padding: 16, backgroundColor: '#f8d7da', color: '#721c24', borderRadius: 4 }}>
                <strong>Errors:</strong>
                <ul style={{ marginTop: 8 }}>
                  {playgroundData.errors.map((err, idx) => (
                    <li key={`error-${err.region_id}-${idx}`}>{err.region_id}: {err.error}</li>
                  ))}
                </ul>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 24 }}>
              {playgroundData.results.map((result) => {
                const latestHistory = result.forecast.history && result.forecast.history.length > 0
                  ? result.forecast.history[result.forecast.history.length - 1]
                  : null;
                const behaviorIndex = typeof latestHistory?.behavior_index === 'number'
                  ? latestHistory.behavior_index
                  : 0.5;
                const subIndices = latestHistory?.sub_indices;

                return (
                  <div key={result.region_id} style={{ padding: 20, border: '1px solid #ddd', borderRadius: 8, backgroundColor: 'white' }}>
                    <h3 style={{ marginTop: 0, marginBottom: 8 }}>
                      {result.region_name} ({result.region_id})
                    </h3>

                    {result.scenario_applied && (
                      <div style={{ marginBottom: 12, padding: 8, backgroundColor: '#fff3cd', borderRadius: 4, fontSize: 12 }}>
                        <strong>Scenario Applied:</strong> {result.scenario_description}
                      </div>
                    )}

                    <div style={{ marginBottom: 16 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                        <span style={{ fontWeight: 'bold', fontSize: 18 }}>
                          Behavior Index: {typeof behaviorIndex === 'number' ? behaviorIndex.toFixed(3) : String(behaviorIndex || 'N/A')}
                        </span>
                        <span
                          style={{
                            padding: '4px 12px',
                            borderRadius: 12,
                            fontSize: 12,
                            fontWeight: '500',
                            backgroundColor: behaviorIndex < 0.33 ? '#28a74520' : behaviorIndex < 0.67 ? '#ffc10720' : '#dc354520',
                            color: behaviorIndex < 0.33 ? '#28a745' : behaviorIndex < 0.67 ? '#ffc107' : '#dc3545',
                          }}
                        >
                          {behaviorIndex < 0.33 ? 'LOW' : behaviorIndex < 0.67 ? 'MODERATE' : 'HIGH'}
                        </span>
                      </div>
                    </div>

                    {(subIndices && typeof subIndices === 'object' && subIndices !== null) ? (
                      <div style={{ marginBottom: 16 }}>
                        <h4 style={{ fontSize: 14, marginBottom: 8 }}>Sub-Indices:</h4>
                        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                          <tbody>
                            <tr>
                              <td style={{ padding: 4 }}>Economic Stress:</td>
                              <td style={{ padding: 4, textAlign: 'right', fontFamily: 'monospace' }}>
                                {typeof (subIndices as Record<string, unknown>).economic_stress === 'number'
                                  ? (subIndices as Record<string, number>).economic_stress.toFixed(3)
                                  : 'N/A'}
                              </td>
                            </tr>
                            <tr>
                              <td style={{ padding: 4 }}>Environmental Stress:</td>
                              <td style={{ padding: 4, textAlign: 'right', fontFamily: 'monospace' }}>
                                {typeof (subIndices as Record<string, unknown>).environmental_stress === 'number'
                                  ? (subIndices as Record<string, number>).environmental_stress.toFixed(3)
                                  : 'N/A'}
                              </td>
                            </tr>
                            <tr>
                              <td style={{ padding: 4 }}>Mobility Activity:</td>
                              <td style={{ padding: 4, textAlign: 'right', fontFamily: 'monospace' }}>
                                {typeof (subIndices as Record<string, unknown>).mobility_activity === 'number'
                                  ? (subIndices as Record<string, number>).mobility_activity.toFixed(3)
                                  : 'N/A'}
                              </td>
                            </tr>
                            <tr>
                              <td style={{ padding: 4 }}>Digital Attention:</td>
                              <td style={{ padding: 4, textAlign: 'right', fontFamily: 'monospace' }}>
                                {typeof (subIndices as Record<string, unknown>).digital_attention === 'number'
                                  ? (subIndices as Record<string, number>).digital_attention.toFixed(3)
                                  : 'N/A'}
                              </td>
                            </tr>
                            <tr>
                              <td style={{ padding: 4 }}>Public Health Stress:</td>
                              <td style={{ padding: 4, textAlign: 'right', fontFamily: 'monospace' }}>
                                {typeof (subIndices as Record<string, unknown>).public_health_stress === 'number'
                                  ? (subIndices as Record<string, number>).public_health_stress.toFixed(3)
                                  : 'N/A'}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    ) : null}

                    {result.explanations && typeof result.explanations === 'object' && result.explanations !== null && (
                      <div style={{ marginTop: 16, padding: 12, backgroundColor: '#e7f3ff', borderRadius: 4 }}>
                        <h4 style={{ fontSize: 14, marginTop: 0, marginBottom: 8 }}>Explanation:</h4>
                        <p style={{ fontSize: 12, margin: 0, color: '#555' }}>
                          {typeof (result.explanations as Record<string, unknown>).summary === 'string'
                            ? (result.explanations as Record<string, string>).summary
                            : 'No explanation available'}
                        </p>
                      </div>
                    )}

                    {result.forecast.sources && result.forecast.sources.length > 0 && (
                      <div style={{ marginTop: 12, fontSize: 11, color: '#666' }}>
                        <strong>Sources:</strong> {result.forecast.sources.join(', ')}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </main>
    </>
  );
}
