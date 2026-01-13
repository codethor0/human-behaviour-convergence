'use client';

import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import {
  fetchRegions as apiFetchRegions,
  fetchDataSources as apiFetchDataSources,
  runForecast as apiRunForecast,
} from '../lib/api';

interface ForecastRequest {
  region_id?: string;
  latitude?: number;
  longitude?: number;
  region_name: string;
  days_back: number;
  forecast_horizon: number;
}

interface SubIndices {
  economic_stress?: number;
  environmental_stress?: number;
  mobility_activity?: number;
  digital_attention?: number;
  public_health_stress?: number;
  political_stress?: number;
  crime_stress?: number;
  misinformation_stress?: number;
  social_cohesion_stress?: number;
}

interface SubIndexContribution {
  value: number;
  weight: number;
  contribution: number;
}

interface SubIndexContributions {
  economic_stress?: SubIndexContribution;
  environmental_stress?: SubIndexContribution;
  mobility_activity?: SubIndexContribution;
  digital_attention?: SubIndexContribution;
  public_health_stress?: SubIndexContribution;
  political_stress?: SubIndexContribution;
  crime_stress?: SubIndexContribution;
  misinformation_stress?: SubIndexContribution;
  social_cohesion_stress?: SubIndexContribution;
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
    economic_stress?: SubIndexExplanation;
    environmental_stress?: SubIndexExplanation;
    mobility_activity?: SubIndexExplanation;
    digital_attention?: SubIndexExplanation;
    public_health_stress?: SubIndexExplanation;
    political_stress?: SubIndexExplanation;
    crime_stress?: SubIndexExplanation;
    misinformation_stress?: SubIndexExplanation;
    social_cohesion_stress?: SubIndexExplanation;
  };
}

interface ShockEvent {
  index: string;
  severity: string;
  delta: number;
  timestamp: string;
}

interface ConvergenceAnalysis {
  score: number;
  reinforcing_signals: Array<string | number | [string, string, number]>;
  conflicting_signals: Array<string | number | [string, string, number]>;
}

interface RiskClassification {
  tier: string;
  risk_score: number;
}

interface ForecastResponse {
  history: ForecastHistoryItem[];
  forecast: ForecastItem[];
  sources: string[];
  metadata: Record<string, any>;
  explanation?: string;
  explanations?: Explanations;
  shock_events?: ShockEvent[];
  convergence?: ConvergenceAnalysis;
  risk_tier?: RiskClassification;
  forecast_confidence?: Record<string, number>;
  model_drift?: Record<string, number>;
  correlations?: {
    correlations?: Record<string, number>;
    relationships?: Array<{ index1: string; index2: string; correlation: number }>;
    indices_analyzed?: string[];
  };
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

const styles = {
  container: {
    fontFamily: 'system-ui, -apple-system, sans-serif',
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '12px',
    backgroundColor: '#f5f5f5',
    minHeight: '100vh',
  },
  header: {
    backgroundColor: '#fff',
    padding: '10px 16px',
    marginBottom: '12px',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  nav: {
    display: 'flex',
    gap: '24px',
    alignItems: 'center',
    flexWrap: 'wrap' as const,
  },
  navLink: {
    textDecoration: 'none',
    color: '#0070f3',
    fontSize: '14px',
    fontWeight: '500',
    padding: '6px 0',
    borderBottom: '2px solid transparent',
  },
  navLinkActive: {
    borderBottomColor: '#0070f3',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: '8px',
    padding: '14px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    marginBottom: '12px',
  },
  grid: {
    display: 'grid',
    gap: '12px',
  },
  grid2Col: {
    gridTemplateColumns: 'repeat(2, 1fr)',
  },
  grid3Col: {
    gridTemplateColumns: 'repeat(3, 1fr)',
  },
  grid4Col: {
    gridTemplateColumns: 'repeat(4, 1fr)',
  },
  label: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#666',
    marginBottom: '4px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  value: {
    fontSize: '20px',
    fontWeight: '700',
    color: '#000',
  },
  metricCard: {
    backgroundColor: '#f8f9fa',
    padding: '10px',
    borderRadius: '6px',
    border: '1px solid #e9ecef',
  },
  button: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: '600',
    backgroundColor: '#0070f3',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
    cursor: 'not-allowed',
  },
  input: {
    padding: '8px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    width: '100%',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: '13px',
  },
  tableHeader: {
    backgroundColor: '#f8f9fa',
    fontWeight: '600',
    padding: '8px',
    textAlign: 'left' as const,
    borderBottom: '2px solid #dee2e6',
    fontSize: '12px',
    color: '#666',
  },
  tableCell: {
    padding: '8px',
    borderBottom: '1px solid #e9ecef',
    fontSize: '13px',
  },
  badge: {
    display: 'inline-block',
    padding: '4px 8px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  badgeLow: {
    backgroundColor: '#d4edda',
    color: '#155724',
  },
  badgeModerate: {
    backgroundColor: '#fff3cd',
    color: '#856404',
  },
  badgeHigh: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
  },
};

export default function ForecastPage() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [daysBack, setDaysBack] = useState(30);
  const [forecastHorizon, setForecastHorizon] = useState(7);
  const [loading, setLoading] = useState(false);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dataSources, setDataSources] = useState<Array<{ name: string; status: string; description?: string; available?: boolean; parameters?: Record<string, string> }>>([]);
  const [expandedSubIndex, setExpandedSubIndex] = useState<string | null>(null);
  const [showHistoryTable, setShowHistoryTable] = useState(false);

  const fetchDataSources = async () => {
    try {
      setError(null);
      const data = await apiFetchDataSources();
      setDataSources(data);
    } catch (e) {
      console.error('Failed to fetch data sources:', e);
      setError(e instanceof Error ? e.message : 'Failed to load data sources');
    }
  };

  const fetchRegions = async () => {
    try {
      setError(null);
      const data = await apiFetchRegions();

      // Validate that data is an array
      if (!Array.isArray(data)) {
        throw new Error(`Invalid response format: expected array, got ${typeof data}`);
      }

      // Only set regions if we have valid data
      if (data.length > 0) {
        setRegions(data);
        const defaultRegion = data.find((r: Region) => r.id === 'city_nyc') || data[0];
        if (defaultRegion) {
          setSelectedRegion(defaultRegion);
        }
      } else {
        // Empty array - use fallback
        throw new Error('Regions endpoint returned empty array');
      }
    } catch (e) {
      console.error('Failed to fetch regions:', e);
      setError(e instanceof Error ? e.message : 'Failed to load regions');
      // Use fallback regions to ensure UI is usable
      const fallback: Region[] = [
        { id: 'city_nyc', name: 'New York City', country: 'US', region_type: 'city', latitude: 40.7128, longitude: -74.0060 },
        { id: 'city_london', name: 'London', country: 'GB', region_type: 'city', latitude: 51.5074, longitude: -0.1278 },
        { id: 'city_tokyo', name: 'Tokyo', country: 'JP', region_type: 'city', latitude: 35.6762, longitude: 139.6503 },
      ];
      setRegions(fallback);
      if (fallback.length > 0 && fallback[0]) {
        setSelectedRegion(fallback[0]);
      }
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

      const request = {
        region_id: selectedRegion.id,
        region_name: selectedRegion.name,
        latitude: selectedRegion.latitude,
        longitude: selectedRegion.longitude,
        days_back: daysBack,
        forecast_horizon: forecastHorizon,
      };

      const data = await apiRunForecast(request);

      // Validate and sanitize response data
      if (!data) {
        throw new Error('Empty response from server');
      }

      // Ensure arrays exist
      if (!Array.isArray(data.history)) {
        data.history = [];
      }
      if (!Array.isArray(data.forecast)) {
        data.forecast = [];
      }
      if (!Array.isArray(data.sources)) {
        data.sources = [];
      }

      setForecastData(data);
    } catch (e: unknown) {
      console.error('Forecast request failed', e);
      setError(e instanceof Error ? e.message : 'Failed to generate forecast');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDataSources();
    fetchRegions();
  }, []);

  const latestHistory = forecastData?.history && Array.isArray(forecastData.history) && forecastData.history.length > 0
    ? forecastData.history[forecastData.history.length - 1]
    : null;
  const currentBehaviorIndex = typeof latestHistory?.behavior_index === 'number' && !isNaN(latestHistory.behavior_index)
    ? Math.max(0, Math.min(1, latestHistory.behavior_index))
    : 0;
  const riskTier = forecastData?.risk_tier?.tier && typeof forecastData.risk_tier.tier === 'string'
    ? forecastData.risk_tier.tier
    : 'stable';
  const convergenceScore = typeof forecastData?.convergence?.score === 'number' && !isNaN(forecastData.convergence.score)
    ? Math.max(0, Math.min(100, forecastData.convergence.score))
    : 0;
  const shockCount = Array.isArray(forecastData?.shock_events) ? forecastData.shock_events.length : 0;

  return (
    <>
      <Head>
        <title>Behavior Forecast - Behavior Convergence Explorer</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>{`
          @media (max-width: 768px) {
            .grid-2-col { grid-template-columns: 1fr !important; }
            .grid-3-col { grid-template-columns: repeat(2, 1fr) !important; }
            .grid-4-col { grid-template-columns: repeat(2, 1fr) !important; }
          }
          @media (max-width: 480px) {
            .grid-2-col { grid-template-columns: 1fr !important; }
            .grid-3-col { grid-template-columns: 1fr !important; }
            .grid-4-col { grid-template-columns: 1fr !important; }
          }
        `}</style>
      </Head>
      <div style={styles.container}>
        {/* Compact Header Navigation */}
        <header style={styles.header}>
          <nav style={styles.nav}>
            <Link href="/forecast" style={{ ...styles.navLink, ...styles.navLinkActive }}>
              Behavior Forecast
            </Link>
            <Link href="/playground" style={styles.navLink}>
              Live Playground
            </Link>
            <Link href="/live" style={styles.navLink}>
              Live Monitoring
            </Link>
            <Link href="/" style={styles.navLink}>
              Results Dashboard
            </Link>
          </nav>
        </header>

        {/* Forecast Configuration - Two Column Layout */}
        <div style={{ ...styles.grid, ...styles.grid2Col, marginBottom: '12px' }} className="grid-2-col">
          <div style={styles.card}>
            <h2 style={{ margin: '0 0 12px 0', fontSize: '18px', fontWeight: '600' }}>Forecast Configuration</h2>
            <div style={{ ...styles.grid, gap: '10px' }}>
              <div>
                <label style={styles.label}>Region</label>
                <select
                  value={selectedRegion?.id || ''}
                  onChange={(e) => {
                    const region = regions.find((r) => r.id === e.target.value);
                    if (region) setSelectedRegion(region);
                  }}
                  style={styles.input}
                  aria-label="Select region for forecast"
                >
                  {regions.length === 0 ? (
                    <option value="">Loading regions...</option>
                  ) : (
                    <>
                      {(() => {
                        const regionGroups = ['GLOBAL_CITIES', 'EUROPE', 'ASIA_PACIFIC', 'LATAM', 'AFRICA', 'US_STATES'];
                        const groupedRegions: Record<string, Region[]> = {};
                        const otherRegions: Region[] = [];

                        regions.forEach((r) => {
                          const group = r.region_group;
                          if (group && regionGroups.includes(group)) {
                            if (!groupedRegions[group]) {
                              groupedRegions[group] = [];
                            }
                            const groupArray = groupedRegions[group];
                            if (groupArray) {
                              groupArray.push(r);
                            }
                          } else {
                            otherRegions.push(r);
                          }
                        });

                        return (
                          <>
                            {regionGroups.map((group) => {
                              const groupRegions = groupedRegions[group];
                              if (!groupRegions || groupRegions.length === 0) return null;
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
                            {otherRegions.length > 0 && (
                              <optgroup label="Other">
                                {otherRegions.map((r) => (
                                  <option key={r.id} value={r.id}>
                                    {r.name} ({r.country})
                                  </option>
                                ))}
                              </optgroup>
                            )}
                          </>
                        );
                      })()}
                    </>
                  )}
                </select>
                {selectedRegion && (
                  <p style={{ margin: '4px 0 0 0', fontSize: '11px', color: '#999' }}>
                    {selectedRegion.latitude.toFixed(4)}, {selectedRegion.longitude.toFixed(4)}
                  </p>
                )}
              </div>
              <div>
                <label style={styles.label}>Historical Days: {daysBack}</label>
                <input
                  type="range"
                  min="7"
                  max="365"
                  value={daysBack}
                  onChange={(e) => setDaysBack(parseInt(e.target.value))}
                  style={{ width: '100%' }}
                  aria-label={`Historical days: ${daysBack}`}
                />
              </div>
              <div>
                <label style={styles.label}>Forecast Horizon: {forecastHorizon} days</label>
                <input
                  type="range"
                  min="1"
                  max="30"
                  value={forecastHorizon}
                  onChange={(e) => setForecastHorizon(parseInt(e.target.value))}
                  style={{ width: '100%' }}
                  aria-label={`Forecast horizon: ${forecastHorizon} days`}
                />
              </div>
              <button
                onClick={runForecast}
                disabled={loading}
                style={loading ? { ...styles.button, ...styles.buttonDisabled } : styles.button}
                aria-label={loading ? 'Generating forecast' : 'Generate forecast'}
                data-testid="forecast-generate-button"
              >
                {loading ? 'Generating...' : 'Generate Forecast'}
              </button>
            </div>
          </div>

          {/* Quick Summary Panel */}
          <div style={styles.card} data-testid="forecast-quick-summary">
            <h2 style={{ margin: '0 0 12px 0', fontSize: '18px', fontWeight: '600' }}>Quick Summary</h2>
            {forecastData ? (
              <div style={{ ...styles.grid, ...styles.grid2Col, gap: '10px' }}>
                <div style={styles.metricCard}>
                  <div style={styles.label}>Behavior Index</div>
                  <div style={styles.value}>{currentBehaviorIndex.toFixed(3)}</div>
                </div>
                <div style={styles.metricCard}>
                  <div style={styles.label}>Risk Tier</div>
                  <div style={{ ...styles.value, fontSize: '16px', textTransform: 'capitalize' }}>{riskTier}</div>
                </div>
                <div style={styles.metricCard}>
                  <div style={styles.label}>Convergence Score</div>
                  <div style={styles.value}>{convergenceScore.toFixed(1)}</div>
                </div>
                <div style={styles.metricCard}>
                  <div style={styles.label}>Shock Events</div>
                  <div style={styles.value}>{shockCount}</div>
                </div>
                {forecastData.metadata?.forecast_date && (
                  <div style={{ ...styles.metricCard, gridColumn: '1 / -1', padding: '8px 12px' }}>
                    <div style={styles.label}>Last Updated</div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {new Date(forecastData.metadata.forecast_date).toLocaleString()}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p style={{ color: '#999', fontSize: '14px', margin: 0 }}>Generate a forecast to see summary</p>
            )}
          </div>
        </div>

        {/* Data Sources - Compact Grid */}
        {dataSources.length > 0 && (
          <div style={styles.card}>
            <h2 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: '600' }}>Data Sources</h2>
            <div style={{ ...styles.grid, ...styles.grid4Col }} className="grid-4-col">
              {dataSources.map((source) => {
                // Determine status badge: active if status=active AND available=true, otherwise degraded
                const isActive = source.status === 'active' && source.available === true;
                const needsKey = source.status === 'needs_key' || (source.available === false && source.status !== 'error');
                const statusText = isActive ? 'active' : (needsKey ? 'needs key' : source.status || 'degraded');
                const requiredVars = source.parameters?.required_env_vars || source.parameters?.requires || '';
                return (
                  <div key={source.name} style={{ ...styles.metricCard, padding: '8px' }}>
                    <div style={{ fontSize: '12px', fontWeight: '600', marginBottom: '4px' }}>
                      {source.name.replace(/_/g, ' ')}
                    </div>
                    <span
                      style={{
                        ...styles.badge,
                        ...(isActive ? styles.badgeLow : (needsKey ? styles.badgeModerate : styles.badgeHigh)),
                      }}
                      title={needsKey && requiredVars ? `Set: ${requiredVars}` : undefined}
                    >
                      {statusText}
                    </span>
                    {needsKey && requiredVars && (
                      <div style={{ fontSize: '10px', color: '#666', marginTop: '4px' }}>
                        Set: {requiredVars}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {error && (
          <div style={{ ...styles.card, backgroundColor: '#f8d7da', color: '#721c24', border: '1px solid #f5c6cb' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {forecastData && (
          <>
            {/* Forecast Summary - Two Column Layout */}
            <div style={{ ...styles.grid, ...styles.grid2Col, marginBottom: '12px' }} className="grid-2-col">
              <div style={styles.card}>
                <h2 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: '600' }}>Forecast Summary</h2>
                {forecastData.explanations?.summary && (
                  <p style={{ fontSize: '14px', color: '#555', margin: '0 0 10px 0', lineHeight: '1.5' }}>
                    {forecastData.explanations.summary}
                  </p>
                )}
                {forecastData.metadata && (
                  <div style={{ ...styles.grid, gap: '6px', fontSize: '12px', color: '#666' }}>
                    <div><strong>Region:</strong> {forecastData.metadata.region_name}</div>
                    <div><strong>Model:</strong> {forecastData.metadata.model_type || 'Unknown'}</div>
                    <div><strong>Data Points:</strong> {forecastData.metadata.historical_data_points || 0}</div>
                  </div>
                )}
              </div>

              <div style={styles.card}>
                <h2 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: '600' }}>Behavior Index</h2>
                <BehaviorIndexGauge value={currentBehaviorIndex} />
                {forecastData.risk_tier && typeof forecastData.risk_tier === 'object' && (
                  <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #e9ecef' }}>
                    <div style={styles.label}>Risk Classification</div>
                    <div style={{ fontSize: '14px', textTransform: 'capitalize', marginTop: '4px' }}>
                      {forecastData.risk_tier.tier || 'stable'} (Score: {typeof forecastData.risk_tier.risk_score === 'number' && !isNaN(forecastData.risk_tier.risk_score) ? Math.max(0, Math.min(1, forecastData.risk_tier.risk_score)).toFixed(3) : '0.000'})
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Sub-Index Breakdown - 3x3 Grid */}
            {forecastData.explanations?.subindices && (
              <div style={styles.card} data-testid="forecast-subindex-breakdown">
                <h2 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: '600' }}>Sub-Index Breakdown</h2>
                <div style={{ ...styles.grid, ...styles.grid3Col, gap: '10px' }} className="grid-3-col">
                  {Object.entries(forecastData.explanations.subindices).map(([key, subIndex]) => {
                    if (!subIndex) return null;
                    const levelColors: Record<string, { bg: string; text: string }> = {
                      low: { bg: '#d4edda', text: '#155724' },
                      moderate: { bg: '#fff3cd', text: '#856404' },
                      high: { bg: '#f8d7da', text: '#721c24' },
                    };
                    const levelColor = levelColors[subIndex.level] || { bg: '#e9ecef', text: '#495057' };
                    const isExpanded = expandedSubIndex === key;
                    const indexValue = latestHistory?.sub_indices?.[key as keyof SubIndices] || 0;

                    return (
                      <div
                        key={key}
                        style={{
                          ...styles.metricCard,
                          padding: '10px',
                          cursor: 'pointer',
                          border: isExpanded ? '2px solid #0070f3' : '1px solid #e9ecef',
                        }}
                        onClick={() => setExpandedSubIndex(isExpanded ? null : key)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setExpandedSubIndex(isExpanded ? null : key);
                          }
                        }}
                        aria-expanded={isExpanded}
                        aria-label={`${key.replace(/_/g, ' ')} sub-index details`}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <div style={{ fontSize: '13px', fontWeight: '600' }}>
                            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </div>
                          <span
                            style={{
                              ...styles.badge,
                              backgroundColor: levelColor.bg,
                              color: levelColor.text,
                            }}
                          >
                            {subIndex.level}
                          </span>
                        </div>
                        <div style={{ fontSize: '20px', fontWeight: '700', marginBottom: '4px' }}>
                          {typeof indexValue === 'number' && !isNaN(indexValue) ? indexValue.toFixed(3) : 'N/A'}
                        </div>
                        <p style={{ fontSize: '12px', color: '#666', margin: '4px 0 0 0', lineHeight: '1.4' }}>
                          {subIndex.reason}
                        </p>
                        {isExpanded && subIndex.components && subIndex.components.length > 0 && (
                          <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #e9ecef' }}>
                            {subIndex.components.map((comp, idx) => (
                              <div key={`${key}-comp-${idx}`} style={{ marginBottom: '6px', fontSize: '11px' }}>
                                <div style={{ fontWeight: '600', marginBottom: '2px' }}>{comp.label}</div>
                                <div style={{ color: '#666', fontSize: '10px' }}>{comp.explanation}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Contribution Breakdown - Horizontal Table */}
            {latestHistory?.subindex_contributions && (
              <div style={styles.card}>
                <h2 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: '600' }}>Contribution Breakdown</h2>
                <div style={{ overflowX: 'auto' }}>
                  <table style={styles.table} role="table" aria-label="Contribution breakdown table">
                    <thead>
                      <tr>
                        <th style={styles.tableHeader}>Dimension</th>
                        <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Value</th>
                        <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Weight</th>
                        <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Contribution</th>
                        <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Visual</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(latestHistory.subindex_contributions).map(([key, contrib]) => {
                        if (!contrib || typeof contrib !== 'object') return null;
                        const value = typeof contrib.value === 'number' && !isNaN(contrib.value) ? contrib.value : 0;
                        const weight = typeof contrib.weight === 'number' && !isNaN(contrib.weight) ? contrib.weight : 0;
                        const contribution = typeof contrib.contribution === 'number' && !isNaN(contrib.contribution) ? contrib.contribution : 0;
                        return (
                          <tr key={key}>
                            <td style={styles.tableCell}>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</td>
                            <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace' }}>
                              {value.toFixed(3)}
                            </td>
                            <td style={{ ...styles.tableCell, textAlign: 'right' }}>{(weight * 100).toFixed(0)}%</td>
                            <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontWeight: '600' }}>
                              {contribution.toFixed(3)}
                            </td>
                            <td style={styles.tableCell}>
                              <div style={{ height: '8px', backgroundColor: '#e9ecef', borderRadius: '4px', overflow: 'hidden' }}>
                                <div
                                  style={{
                                    width: `${Math.min(100, Math.max(0, Math.abs(contribution) * 100))}%`,
                                    height: '100%',
                                    backgroundColor: contribution > 0 ? '#dc3545' : '#28a745',
                                  }}
                                />
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Intelligence Layer Summary */}
            {(forecastData.shock_events || forecastData.convergence || forecastData.forecast_confidence) && (
              <div style={styles.card}>
                <h2 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: '600' }}>Intelligence Layer</h2>
                <div style={{ ...styles.grid, ...styles.grid3Col, gap: '10px' }} className="grid-3-col">
                  {Array.isArray(forecastData.shock_events) && forecastData.shock_events.length > 0 && (
                    <div style={styles.metricCard}>
                      <div style={styles.label}>Shock Events</div>
                      <div style={styles.value}>{forecastData.shock_events.length}</div>
                      {forecastData.shock_events[0] && (
                        <div style={{ fontSize: '11px', color: '#666', marginTop: '4px' }}>
                          Latest: {forecastData.shock_events[0].index || 'Unknown'} ({forecastData.shock_events[0].severity || 'Unknown'})
                        </div>
                      )}
                    </div>
                  )}
                  {forecastData.convergence && typeof forecastData.convergence === 'object' && (
                    <div style={styles.metricCard}>
                      <div style={styles.label}>Convergence</div>
                      <div style={styles.value}>
                        {typeof forecastData.convergence.score === 'number' && !isNaN(forecastData.convergence.score)
                          ? Math.max(0, Math.min(100, forecastData.convergence.score)).toFixed(1)
                          : '0.0'}
                      </div>
                      <div style={{ fontSize: '11px', color: '#666', marginTop: '4px' }}>
                        Reinforcing: {Array.isArray(forecastData.convergence.reinforcing_signals) ? forecastData.convergence.reinforcing_signals.length : 0}
                      </div>
                    </div>
                  )}
                  {forecastData.forecast_confidence && typeof forecastData.forecast_confidence === 'object' && Object.keys(forecastData.forecast_confidence).length > 0 && (
                    <div style={styles.metricCard}>
                      <div style={styles.label}>Avg Confidence</div>
                      <div style={styles.value}>
                        {(() => {
                          const values = Object.values(forecastData.forecast_confidence).filter((v): v is number => typeof v === 'number' && !isNaN(v));
                          if (values.length === 0) return '0.00';
                          const sum = values.reduce((a, b) => a + b, 0);
                          const avg = sum / values.length;
                          return Math.max(0, Math.min(1, avg)).toFixed(2);
                        })()}
                      </div>
                      <div style={{ fontSize: '11px', color: '#666', marginTop: '4px' }}>
                        {Object.keys(forecastData.forecast_confidence).length} indices
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Historical Data - Collapsible */}
            {forecastData.history && forecastData.history.length > 0 && (
              <div style={styles.card}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <h2 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>
                    Historical Data ({forecastData.history.length} points)
                  </h2>
                  <button
                    onClick={() => setShowHistoryTable(!showHistoryTable)}
                    style={{ ...styles.button, padding: '6px 12px', fontSize: '12px' }}
                    aria-label={showHistoryTable ? 'Hide historical data' : 'Show historical data'}
                    aria-expanded={showHistoryTable}
                  >
                    {showHistoryTable ? 'Hide' : 'Show'}
                  </button>
                </div>
                {showHistoryTable && (
                  <div style={{ overflowX: 'auto', maxHeight: '350px', overflowY: 'auto' }}>
                    <table style={styles.table} role="table" aria-label="Historical data table">
                      <thead>
                        <tr style={{ backgroundColor: '#f8f9fa', position: 'sticky' as const, top: 0 }}>
                          <th style={styles.tableHeader}>Date</th>
                          <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Behavior Index</th>
                          {forecastData.history[0]?.sub_indices && (
                            <>
                              <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Economic</th>
                              <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Environmental</th>
                              <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Mobility</th>
                              <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Digital</th>
                              <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Health</th>
                              <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Political</th>
                              <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Crime</th>
                              <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Misinfo</th>
                              <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Social</th>
                            </>
                          )}
                        </tr>
                      </thead>
                      <tbody>
                        {forecastData.history.slice(-20).map((item, i) => {
                          if (!item) return null;
                          const safeTimestamp = item.timestamp ? (() => {
                            try {
                              return new Date(item.timestamp).toLocaleDateString();
                            } catch {
                              return String(item.timestamp || 'N/A');
                            }
                          })() : 'N/A';
                          const safeBehaviorIndex = typeof item.behavior_index === 'number' && !isNaN(item.behavior_index)
                            ? Math.max(0, Math.min(1, item.behavior_index)).toFixed(3)
                            : 'N/A';
                          const formatSubIndex = (val: unknown): string => {
                            if (typeof val === 'number' && !isNaN(val)) {
                              return Math.max(0, Math.min(1, val)).toFixed(2);
                            }
                            return '-';
                          };
                          return (
                            <tr key={`history-${i}-${item.timestamp || i}`}>
                              <td style={styles.tableCell}>{safeTimestamp}</td>
                              <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontWeight: '600' }}>
                                {safeBehaviorIndex}
                              </td>
                              {item.sub_indices && typeof item.sub_indices === 'object' ? (
                                <>
                                  <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                                    {formatSubIndex(item.sub_indices.economic_stress)}
                                  </td>
                                  <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                                    {formatSubIndex(item.sub_indices.environmental_stress)}
                                  </td>
                                  <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                                    {formatSubIndex(item.sub_indices.mobility_activity)}
                                  </td>
                                  <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                                    {formatSubIndex(item.sub_indices.digital_attention)}
                                  </td>
                                  <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                                    {formatSubIndex(item.sub_indices.public_health_stress)}
                                  </td>
                                  <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                                    {formatSubIndex(item.sub_indices.political_stress)}
                                  </td>
                                  <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                                    {formatSubIndex(item.sub_indices.crime_stress)}
                                  </td>
                                  <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                                    {formatSubIndex(item.sub_indices.misinformation_stress)}
                                  </td>
                                  <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                                    {formatSubIndex(item.sub_indices.social_cohesion_stress)}
                                  </td>
                                </>
                              ) : (
                                <>
                                  <td style={styles.tableCell}>-</td>
                                  <td style={styles.tableCell}>-</td>
                                  <td style={styles.tableCell}>-</td>
                                  <td style={styles.tableCell}>-</td>
                                  <td style={styles.tableCell}>-</td>
                                  <td style={styles.tableCell}>-</td>
                                  <td style={styles.tableCell}>-</td>
                                  <td style={styles.tableCell}>-</td>
                                  <td style={styles.tableCell}>-</td>
                                </>
                              )}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Forecast Table - Compact & Scrollable */}
            {forecastData.forecast && forecastData.forecast.length > 0 && (
              <div style={styles.card}>
                <h2 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: '600' }}>
                  Forecast ({forecastData.forecast.length} days ahead)
                </h2>
                <div style={{ overflowX: 'auto' }}>
                  <table style={styles.table} role="table" aria-label="Forecast predictions table">
                    <thead>
                      <tr>
                        <th style={styles.tableHeader}>Date</th>
                        <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Prediction</th>
                        <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Lower</th>
                        <th style={{ ...styles.tableHeader, textAlign: 'right' }}>Upper</th>
                      </tr>
                    </thead>
                    <tbody>
                      {forecastData.forecast.map((item, i) => {
                        if (!item) return null;
                        const safeTimestamp = item.timestamp ? (() => {
                          try {
                            return new Date(item.timestamp).toLocaleDateString();
                          } catch {
                            return String(item.timestamp || 'N/A');
                          }
                        })() : 'N/A';
                        const formatForecastValue = (val: unknown): string => {
                          if (typeof val === 'number' && !isNaN(val)) {
                            return Math.max(0, Math.min(1, val)).toFixed(3);
                          }
                          return 'N/A';
                        };
                        return (
                          <tr key={`forecast-${i}-${item.timestamp || i}`}>
                            <td style={styles.tableCell}>{safeTimestamp}</td>
                            <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontWeight: '600' }}>
                              {formatForecastValue(item.prediction)}
                            </td>
                            <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontSize: '12px', color: '#666' }}>
                              {formatForecastValue(item.lower_bound)}
                            </td>
                            <td style={{ ...styles.tableCell, textAlign: 'right', fontFamily: 'monospace', fontSize: '12px', color: '#666' }}>
                              {formatForecastValue(item.upper_bound)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
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
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
        <div style={{ flex: 1, height: '20px', backgroundColor: '#e9ecef', borderRadius: '10px', overflow: 'hidden', position: 'relative' }}>
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
              fontSize: '11px',
              color: value > 0.5 ? 'white' : '#333',
            }}
          >
            {value.toFixed(3)}
          </div>
        </div>
        <span style={{ fontWeight: '600', color: level.color, fontSize: '13px', minWidth: '120px' }}>
          {level.label}
        </span>
      </div>
    </div>
  );
}
