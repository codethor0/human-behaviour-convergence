'use client';

import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import {
  // fetchDataSources as apiFetchDataSources, // No longer used - replaced by Grafana dashboard
  runForecast as apiRunForecast,
} from '../lib/api';
import { useRegions } from '../hooks/useRegions';

// Legacy interfaces - no longer used since Grafana migration
// interface SubIndices {
//   economic_stress?: number;
//   environmental_stress?: number;
//   mobility_activity?: number;
//   digital_attention?: number;
//   public_health_stress?: number;
//   political_stress?: number;
//   crime_stress?: number;
//   misinformation_stress?: number;
//   social_cohesion_stress?: number;
// }
// interface ForecastHistoryItem {
//   timestamp: string;
//   behavior_index: number;
//   sub_indices?: SubIndices;
// }

// interface ForecastItem {
//   timestamp: string;
//   prediction: number;
//   lower_bound: number;
//   upper_bound: number;
//   sub_indices?: SubIndices;
// }

// interface ForecastResponse {
//   history: ForecastHistoryItem[];
//   forecast: ForecastItem[];
//   sources: string[];
//   metadata: Record<string, any>;
//   explanation?: string;
//   risk_tier?: {
//     tier: string;
//     risk_score: number;
//   };
// }

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
    maxWidth: '1600px',
    margin: '0 auto',
    padding: '10px',
    backgroundColor: '#f5f5f5',
    minHeight: '100vh',
  },
  header: {
    backgroundColor: '#fff',
    padding: '8px 14px',
    marginBottom: '6px',
    borderRadius: '6px',
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
    borderRadius: '6px',
    padding: '12px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    marginBottom: '4px',
  },
  infoCard: {
    backgroundColor: '#e7f3ff',
    border: '1px solid #b3d9ff',
    borderRadius: '6px',
    padding: '10px',
    marginBottom: '6px',
    fontSize: '13px',
    color: '#004085',
    lineHeight: '1.4',
  },
  grid: {
    display: 'grid',
    gap: '12px',
  },
  grid2Col: {
    gridTemplateColumns: 'repeat(2, 1fr)',
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
  iframe: {
    width: '100%',
    height: '500px',
    border: 'none',
    borderRadius: '8px',
  },
};

// Custom heights for specific dashboards
const dashboardHeights: Record<string, string> = {
  'forecast-summary': '380px',
  'behavior-index-global': '580px',
  'subindex-deep-dive': '1200px',
  'data-sources-health': '500px',
};

// Grafana Dashboard Embed Component
function GrafanaDashboardEmbed({ dashboardUid, title, regionId }: { dashboardUid: string; title: string; regionId?: string }) {
  const grafanaBase = process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3001';
  const regionParam = regionId ? `&var-region=${encodeURIComponent(regionId)}` : '';
  const src = `${grafanaBase}/d/${dashboardUid}?orgId=1&theme=light&kiosk=tv${regionParam}`;
  
  // Use custom height if defined for this dashboard, otherwise use default from styles.iframe
  const customHeight = dashboardHeights[dashboardUid];
  const iframeStyle = customHeight 
    ? { ...styles.iframe, height: customHeight }
    : styles.iframe;

  return (
    <div style={{
      backgroundColor: '#fff',
      borderRadius: '6px',
      padding: '8px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      marginBottom: '4px',
    }}>
      <h2 style={{ margin: '0 0 4px 0', fontSize: '14px', fontWeight: '600', color: '#333' }}>{title}</h2>
      <iframe
        src={src}
        style={iframeStyle}
        title={title}
        allow="fullscreen"
      />
    </div>
  );
}

export default function ForecastPage() {
  const { regions, loading: regionsLoading, error: regionsError, reload: reloadRegions } = useRegions();
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [daysBack, setDaysBack] = useState(30);
  const [forecastHorizon, setForecastHorizon] = useState(7);
  const [loading, setLoading] = useState(false);
  // forecastData no longer needed - Grafana displays metrics directly from Prometheus
  // const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Legacy data sources state - replaced by Grafana dashboard
  // const [dataSources, setDataSources] = useState<Array<{ name: string; status: string; description?: string; available?: boolean; optional?: boolean; message?: string | null }>>([]);

  // Legacy data sources fetch - replaced by Grafana dashboard
  // const fetchDataSources = async () => {
  //   try {
  //     setError(null);
  //     const data = await apiFetchDataSources();
  //     setDataSources(data);
  //   } catch (e) {
  //     console.error('Failed to fetch data sources:', e);
  //     setError(e instanceof Error ? e.message : 'Failed to load data sources');
  //   }
  // };

  // Set default region when regions load successfully
  useEffect(() => {
    if (!regionsLoading && regions.length > 0 && !selectedRegion) {
      const defaultRegion = regions.find((r: Region) => r.id === 'city_nyc') || regions[0];
      if (defaultRegion) {
        setSelectedRegion(defaultRegion);
      }
    }
  }, [regions, regionsLoading, selectedRegion]);

  const runForecast = async () => {
    setLoading(true);
    setError(null);

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

      // Call forecast API to trigger backend metrics update
      // Result is displayed via Grafana dashboards that query Prometheus
      const data = await apiRunForecast(request);

      // Validate response
      if (!data) {
        throw new Error('Empty response from server');
      }

      // Success - Grafana dashboards will automatically refresh and show updated metrics
    } catch (e: unknown) {
      console.error('Forecast request failed', e);
      setError(e instanceof Error ? e.message : 'Failed to generate forecast');
    } finally {
      setLoading(false);
    }
  };

  // Legacy data sources fetch - replaced by Grafana dashboard
  // useEffect(() => {
  //   fetchDataSources();
  // }, []);

  // Legacy Quick Summary calculations - replaced by Grafana dashboard
  // const latestHistory = forecastData?.history && Array.isArray(forecastData.history) && forecastData.history.length > 0
  //   ? forecastData.history[forecastData.history.length - 1]
  //   : null;
  // const currentBehaviorIndex = typeof latestHistory?.behavior_index === 'number' && !isNaN(latestHistory.behavior_index)
  //   ? Math.max(0, Math.min(1, latestHistory.behavior_index))
  //   : 0;
  // const riskTier = forecastData?.risk_tier?.tier && typeof forecastData.risk_tier.tier === 'string'
  //   ? forecastData.risk_tier.tier
  //   : 'stable';

  return (
    <>
      <Head>
        <title>Behavior Forecast - Behavior Convergence Explorer</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>{`
          @media (max-width: 768px) {
            .grid-2-col { grid-template-columns: 1fr !important; }
          }
        `}</style>
      </Head>
      <div style={styles.container}>
        {/* Header Navigation */}
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

        {/* Info Banner */}
        <div style={styles.infoCard}>
          <strong>Analytics Powered by Grafana</strong>
          <br />
          Deep-dive analytics and time-series visualizations are now powered by Grafana dashboards below.
          Forecast data is fetched from the backend API and metrics are exposed to Prometheus for real-time monitoring.
        </div>

        {/* Forecast Configuration */}
        <div style={{ ...styles.grid, ...styles.grid2Col, marginBottom: '4px' }} className="grid-2-col">
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
                  disabled={regionsLoading || regions.length === 0}
                >
                  {regionsLoading ? (
                    <option value="">Loading regions...</option>
                  ) : regionsError ? (
                    <option value="">Error loading regions</option>
                  ) : regions.length === 0 ? (
                    <option value="">No regions available</option>
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
                {regionsError && (
                  <div style={{ margin: '8px 0', padding: '8px', backgroundColor: '#fff3cd', border: '1px solid #ffc107', borderRadius: '4px', fontSize: '13px' }}>
                    <span style={{ color: '#856404' }}>Unable to load regions. Check your connection and click &quot;Retry&quot;.</span>
                    <button
                      onClick={reloadRegions}
                      style={{
                        marginLeft: '8px',
                        padding: '4px 12px',
                        backgroundColor: '#0070f3',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px',
                      }}
                    >
                      Retry
                    </button>
                  </div>
                )}
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

          {/* Legacy Quick Summary Panel - Replaced by Grafana dashboard */}
          {/* 
          <div style={styles.card} data-testid="forecast-quick-summary">
            <h2 style={{ margin: '0 0 12px 0', fontSize: '18px', fontWeight: '600' }}>Quick Summary</h2>
            {forecastData ? (
              <div style={{ ...styles.grid, gap: '10px' }}>
                <div style={styles.metricCard}>
                  <div style={styles.label}>Behavior Index</div>
                  <div style={styles.value}>{currentBehaviorIndex.toFixed(3)}</div>
                </div>
                <div style={styles.metricCard}>
                  <div style={styles.label}>Risk Tier</div>
                  <div style={{ ...styles.value, fontSize: '16px', textTransform: 'capitalize' }}>{riskTier}</div>
                </div>
                <div style={styles.metricCard}>
                  <div style={styles.label}>History Points</div>
                  <div style={styles.value}>{forecastData.history.length}</div>
                </div>
                <div style={styles.metricCard}>
                  <div style={styles.label}>Forecast Points</div>
                  <div style={styles.value}>{forecastData.forecast.length}</div>
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
              <p style={{ color: '#999', fontSize: '14px', margin: 0 }}>Generate a forecast to see summary and update metrics</p>
            )}
          </div>
          */}
        </div>

        {error && (
          <div style={{ ...styles.card, backgroundColor: '#f8d7da', color: '#721c24', border: '1px solid #f5c6cb' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Grafana Dashboard Embeds */}
        {selectedRegion && (
          <GrafanaDashboardEmbed
            dashboardUid="forecast-summary"
            title="Regional Forecast Overview & Key Metrics"
            regionId={selectedRegion.id}
          />
        )}

        <GrafanaDashboardEmbed
          dashboardUid="behavior-index-global"
          title="Behavior Index Timeline & Historical Trends"
          regionId={selectedRegion?.id}
        />

        <GrafanaDashboardEmbed
          dashboardUid="subindex-deep-dive"
          title="Sub-Index Components & Contributing Factors"
          regionId={selectedRegion?.id}
        />

        {/* Legacy Data Sources Info - Replaced by Grafana dashboard */}
        {/* 
        {dataSources.length > 0 && (
          <div style={styles.card}>
            <h2 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: '600' }}>Data Sources ({dataSources.length})</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px' }}>
              {dataSources.map((source) => {
                const isActive = source.status === 'active' && source.available === true;
                const isOptional = source.optional === true;
                return (
                  <div key={source.name} style={{ ...styles.metricCard, padding: '8px' }}>
                    <div style={{ fontSize: '12px', fontWeight: '600', marginBottom: '4px' }}>
                      {source.name.replace(/_/g, ' ')}
                    </div>
                    <span
                      style={{
                        display: 'inline-block',
                        padding: '4px 8px',
                        borderRadius: '12px',
                        fontSize: '10px',
                        fontWeight: '600',
                        textTransform: 'uppercase',
                        backgroundColor: isActive ? '#d4edda' : (isOptional ? '#fff3cd' : '#f8d7da'),
                        color: isActive ? '#155724' : (isOptional ? '#856404' : '#721c24'),
                      }}
                    >
                      {source.status}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        */}

        {/* Data Sources Health Dashboard (Live Metrics) */}
        <GrafanaDashboardEmbed
          dashboardUid="data-sources-health"
          title="Real-Time Data Source Status & API Health"
        />
      </div>
    </>
  );
}
