import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';

interface ForecastRequest {
  region_id?: string;
  latitude?: number;
  longitude?: number;
  region_name: string;
  days_back: number;
  forecast_horizon: number;
}

interface SubIndices {
  economic_stress: number;
  environmental_stress: number;
  mobility_activity: number;
  digital_attention: number;
  public_health_stress: number;
}

interface SubIndexContribution {
  value: number;
  weight: number;
  contribution: number;
}

interface SubIndexContributions {
  economic_stress: SubIndexContribution;
  environmental_stress: SubIndexContribution;
  mobility_activity: SubIndexContribution;
  digital_attention: SubIndexContribution;
  public_health_stress: SubIndexContribution;
}

interface ForecastHistoryItem {
  timestamp: string;
  behavior_index: number;
  sub_indices?: SubIndices;
  subindex_contributions?: SubIndexContributions;
}

interface ForecastItem {
  timestamp: string;
  prediction: number;
  lower_bound: number;
  upper_bound: number;
  sub_indices?: SubIndices;
  subindex_contributions?: SubIndexContributions;
}

interface ComponentExplanation {
  id: string;
  label: string;
  direction: string;
  importance: string;
  explanation: string;
}

interface SubIndexExplanation {
  level: string;
  reason: string;
  components: ComponentExplanation[];
}

interface Explanations {
  summary: string;
  subindices: {
    economic_stress: SubIndexExplanation;
    environmental_stress: SubIndexExplanation;
    mobility_activity: SubIndexExplanation;
    digital_attention: SubIndexExplanation;
    public_health_stress: SubIndexExplanation;
  };
}

interface ForecastResponse {
  history: ForecastHistoryItem[];
  forecast: ForecastItem[];
  sources: string[];
  metadata: Record<string, any>;
  explanation?: string;
  explanations?: Explanations;
}

interface Region {
  id: string;
  name: string;
  country: string;
  region_type: string;
  latitude: number;
  longitude: number;
  region_group?: string;
}

export default function ForecastPage() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [daysBack, setDaysBack] = useState(30);
  const [forecastHorizon, setForecastHorizon] = useState(7);
  const [loading, setLoading] = useState(false);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dataSources, setDataSources] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);

  const fetchDataSources = async () => {
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8100';
      const response = await fetch(`${base}/api/forecasting/data-sources`);
      const data = await response.json();
      setDataSources(data);
    } catch (e) {
      console.error('Failed to fetch data sources:', e);
    }
  };

  const fetchModels = async () => {
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8100';
      const response = await fetch(`${base}/api/forecasting/models`);
      const data = await response.json();
      setModels(data);
    } catch (e) {
      console.error('Failed to fetch models:', e);
    }
  };

  const fetchRegions = async () => {
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8100';
      const response = await fetch(`${base}/api/forecasting/regions`);
      const data = await response.json();
      setRegions(data);
      // Set default to first region (or NYC if available)
      const defaultRegion = data.find((r: Region) => r.id === 'city_nyc') || data[0];
      if (defaultRegion) {
        setSelectedRegion(defaultRegion);
      }
    } catch (e) {
      console.error('Failed to fetch regions:', e);
      // Fallback to hardcoded regions if API fails
      const fallback: Region[] = [
        { id: 'city_nyc', name: 'New York City', country: 'US', region_type: 'city', latitude: 40.7128, longitude: -74.0060 },
        { id: 'city_london', name: 'London', country: 'GB', region_type: 'city', latitude: 51.5074, longitude: -0.1278 },
        { id: 'city_tokyo', name: 'Tokyo', country: 'JP', region_type: 'city', latitude: 35.6762, longitude: 139.6503 },
      ];
      setRegions(fallback);
      setSelectedRegion(fallback[0]);
    }
  };

  const runForecast = async () => {
    setLoading(true);
    setError(null);
    setForecastData(null);

    try {
      if (!selectedRegion) {
        throw new Error('Please select a region');
      }

      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8100';
      const request: ForecastRequest = {
        region_id: selectedRegion.id,
        region_name: selectedRegion.name,
        latitude: selectedRegion.latitude,
        longitude: selectedRegion.longitude,
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
    fetchRegions();
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

        <nav style={{ marginBottom: 32, display: 'flex', gap: 16 }}>
          <Link href="/playground" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Live Playground
          </Link>
          <Link href="/live" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Live Monitoring
          </Link>
          <Link href="/" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Results Dashboard
          </Link>
        </nav>

        <section style={{ marginBottom: 32, padding: 20, border: '1px solid #ddd', borderRadius: 8 }}>
          <h2 style={{ marginTop: 0 }}>Forecast Configuration</h2>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 'bold' }}>
              Region:
            </label>
            <select
              value={selectedRegion?.id || ''}
              onChange={(e) => {
                const region = regions.find((r) => r.id === e.target.value);
                if (region) {
                  setSelectedRegion(region);
                }
              }}
              style={{ padding: 8, fontSize: 14, minWidth: 300 }}
            >
              {['GLOBAL_CITIES', 'EUROPE', 'ASIA_PACIFIC', 'LATAM', 'AFRICA', 'US_STATES'].map((group) => {
                const groupRegions = regions.filter((r) => r.region_group === group);
                if (groupRegions.length === 0) return null;
                const groupLabel = group.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                return (
                  <optgroup key={group} label={groupLabel}>
                    {groupRegions.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} ({r.country})
                      </option>
                    ))}
                  </optgroup>
                );
              })}
            </select>
            {selectedRegion && (
              <p style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                Coordinates: {selectedRegion.latitude.toFixed(4)}, {selectedRegion.longitude.toFixed(4)}
              </p>
            )}
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

            {forecastData.explanations && (
              <div style={{ marginBottom: 24, padding: 20, backgroundColor: '#e7f3ff', borderRadius: 8, borderLeft: '4px solid #0070f3' }}>
                <h3 style={{ marginTop: 0, marginBottom: 12 }}>Why This Forecast?</h3>
                <p style={{ margin: '0 0 20px 0', fontSize: 15, fontWeight: '500' }}>
                  {forecastData.explanations.summary}
                </p>

                <div style={{ marginTop: 20 }}>
                  <h4 style={{ marginTop: 0, marginBottom: 12, fontSize: 16 }}>Sub-Index Breakdown</h4>
                  {Object.entries(forecastData.explanations.subindices).map(([key, subIndex]) => {
                    const levelColors: Record<string, string> = {
                      low: '#28a745',
                      moderate: '#ffc107',
                      high: '#dc3545',
                    };
                    const levelColor = levelColors[subIndex.level] || '#666';

                    return (
                      <div key={key} style={{ marginBottom: 20, padding: 16, backgroundColor: 'white', borderRadius: 6, border: '1px solid #ddd' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <h5 style={{ margin: 0, fontSize: 15, fontWeight: '600' }}>
                            {key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </h5>
                          <span
                            style={{
                              padding: '4px 12px',
                              borderRadius: 12,
                              fontSize: 12,
                              fontWeight: '500',
                              backgroundColor: levelColor + '20',
                              color: levelColor,
                            }}
                          >
                            {subIndex.level.toUpperCase()}
                          </span>
                        </div>
                        <p style={{ margin: '0 0 12px 0', fontSize: 14, color: '#555' }}>
                          {subIndex.reason}
                        </p>

                        {subIndex.components && subIndex.components.length > 0 && (
                          <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #eee' }}>
                            <p style={{ margin: '0 0 8px 0', fontSize: 12, fontWeight: '500', color: '#666' }}>
                              Component Details:
                            </p>
                            {subIndex.components.map((comp, idx) => {
                              const importanceColors: Record<string, string> = {
                                high: '#dc3545',
                                medium: '#ffc107',
                                low: '#6c757d',
                              };
                              const directionSymbols: Record<string, string> = {
                                up: '↑',
                                down: '↓',
                                neutral: '→',
                              };

                              return (
                                <div key={idx} style={{ marginBottom: 8, padding: 8, backgroundColor: '#f8f9fa', borderRadius: 4, fontSize: 13 }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                                    <span style={{ fontWeight: '500' }}>{comp.label}</span>
                                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                      <span style={{ color: importanceColors[comp.importance] || '#666', fontSize: 11 }}>
                                        {comp.importance}
                                      </span>
                                      <span style={{ color: '#666' }}>
                                        {directionSymbols[comp.direction] || comp.direction}
                                      </span>
                                    </div>
                                  </div>
                                  <p style={{ margin: 0, fontSize: 12, color: '#666' }}>
                                    {comp.explanation}
                                  </p>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {forecastData.explanation && !forecastData.explanations && (
              <div style={{ marginBottom: 24, padding: 16, backgroundColor: '#e7f3ff', borderRadius: 4, borderLeft: '4px solid #0070f3' }}>
                <h3 style={{ marginTop: 0, marginBottom: 8 }}>Interpretation</h3>
                <p style={{ margin: 0, fontSize: 15 }}>{forecastData.explanation}</p>
              </div>
            )}

            {forecastData.sources && forecastData.sources.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <strong>Data Sources:</strong>{' '}
                {forecastData.sources.join(', ')}
              </div>
            )}

            {forecastData.history && forecastData.history.length > 0 && forecastData.history[forecastData.history.length - 1]?.sub_indices && (
              <div style={{ marginBottom: 24, padding: 16, backgroundColor: '#f8f9fa', borderRadius: 4 }}>
                <h3 style={{ marginTop: 0 }}>Sub-Index Breakdown (Latest)</h3>
                <SubIndexDisplay subIndices={forecastData.history[forecastData.history.length - 1].sub_indices!} />
              </div>
            )}

            {forecastData.history && forecastData.history.length > 0 && forecastData.history[forecastData.history.length - 1]?.subindex_contributions && (
              <div style={{ marginBottom: 24, padding: 16, backgroundColor: '#e7f3ff', borderRadius: 4 }}>
                <h3 style={{ marginTop: 0 }}>Contribution Breakdown</h3>
                <p style={{ fontSize: 12, color: '#666', marginBottom: 12 }}>
                  Contribution = sub-index value × weight in Behavior Index
                </p>
                <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 14 }}>
                  <thead>
                    <tr style={{ backgroundColor: '#f8f9fa' }}>
                      <th style={{ padding: 8, textAlign: 'left', borderBottom: '2px solid #ddd' }}>Dimension</th>
                      <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Value</th>
                      <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Weight</th>
                      <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Contribution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(forecastData.history[forecastData.history.length - 1].subindex_contributions!).map(([key, contrib]) => (
                      <tr key={key}>
                        <td style={{ padding: 8, borderBottom: '1px solid #eee' }}>{key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</td>
                        <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee' }}>{contrib.value.toFixed(3)}</td>
                        <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee' }}>{(contrib.weight * 100).toFixed(0)}%</td>
                        <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee', fontWeight: 'bold' }}>{contrib.contribution.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {forecastData.history && forecastData.history.length > 0 && (
              <div style={{ marginBottom: 24, padding: 16, backgroundColor: '#fff3cd', borderRadius: 4 }}>
                <h3 style={{ marginTop: 0 }}>Current Behavior Index</h3>
                <BehaviorIndexGauge value={forecastData.history[forecastData.history.length - 1].behavior_index} />
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
                        {forecastData.history[0]?.sub_indices && (
                          <>
                            <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Economic</th>
                            <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Environmental</th>
                            <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Mobility</th>
                            <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Digital</th>
                            <th style={{ padding: 8, textAlign: 'right', borderBottom: '2px solid #ddd' }}>Health</th>
                          </>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {forecastData.history.slice(-10).map((item, i) => (
                        <tr key={i}>
                          <td style={{ padding: 8, borderBottom: '1px solid #eee' }}>{item.timestamp}</td>
                          <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee', fontWeight: 'bold' }}>
                            {item.behavior_index.toFixed(3)}
                          </td>
                          {item.sub_indices && (
                            <>
                              <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee', color: '#666' }}>
                                {item.sub_indices.economic_stress.toFixed(2)}
                              </td>
                              <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee', color: '#666' }}>
                                {item.sub_indices.environmental_stress.toFixed(2)}
                              </td>
                              <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee', color: '#666' }}>
                                {item.sub_indices.mobility_activity.toFixed(2)}
                              </td>
                              <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee', color: '#666' }}>
                                {item.sub_indices.digital_attention.toFixed(2)}
                              </td>
                              <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #eee', color: '#666' }}>
                                {item.sub_indices.public_health_stress.toFixed(2)}
                              </td>
                            </>
                          )}
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

function BehaviorIndexGauge({ value }: { value: number }) {
  const getLevel = (v: number) => {
    if (v < 0.3) return { label: 'Low Disruption', color: '#28a745' };
    if (v < 0.6) return { label: 'Moderate Disruption', color: '#ffc107' };
    return { label: 'High Disruption', color: '#dc3545' };
  };

  const level = getLevel(value);
  const percentage = Math.round(value * 100);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 8 }}>
        <div style={{ flex: 1, height: 24, backgroundColor: '#e9ecef', borderRadius: 12, overflow: 'hidden', position: 'relative' }}>
          <div
            style={{
              width: `${percentage}%`,
              height: '100%',
              backgroundColor: level.color,
              transition: 'width 0.3s',
            }}
          />
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              fontWeight: 'bold',
              fontSize: 12,
              color: value > 0.5 ? 'white' : '#333',
            }}
          >
            {value.toFixed(3)}
          </div>
        </div>
        <span style={{ fontWeight: 'bold', color: level.color, minWidth: 150 }}>
          {level.label}
        </span>
      </div>
      <p style={{ margin: 0, fontSize: 13, color: '#666' }}>
        Behavior Index: {value.toFixed(3)} (0.0 = stable, 1.0 = maximum disruption)
      </p>
    </div>
  );
}

function SubIndexDisplay({ subIndices }: { subIndices: SubIndices }) {
  const indices = [
    { name: 'Economic Stress', value: subIndices.economic_stress, color: '#dc3545' },
    { name: 'Environmental Stress', value: subIndices.environmental_stress, color: '#fd7e14' },
    { name: 'Mobility Activity', value: subIndices.mobility_activity, color: '#20c997' },
    { name: 'Digital Attention', value: subIndices.digital_attention, color: '#6f42c1' },
    { name: 'Public Health Stress', value: subIndices.public_health_stress, color: '#e83e8c' },
  ];

  return (
    <div>
      {indices.map((idx) => (
        <div key={idx.name} style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: 14, fontWeight: '500' }}>{idx.name}</span>
            <span style={{ fontSize: 14, fontFamily: 'monospace' }}>{idx.value.toFixed(3)}</span>
          </div>
          <div style={{ height: 8, backgroundColor: '#e9ecef', borderRadius: 4, overflow: 'hidden' }}>
            <div
              style={{
                width: `${idx.value * 100}%`,
                height: '100%',
                backgroundColor: idx.color,
                transition: 'width 0.3s',
              }}
            />
          </div>
        </div>
      ))}
      <p style={{ marginTop: 16, marginBottom: 0, fontSize: 12, color: '#666' }}>
        Higher values indicate more stress/disruption (except Mobility Activity, where higher = more activity).
      </p>
    </div>
  );
}
