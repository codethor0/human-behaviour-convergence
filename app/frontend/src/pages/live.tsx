'use client';

import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { fetchRegions as apiFetchRegions } from '../lib/api';

interface Region {
  id: string;
  name: string;
  country: string;
  region_type: string;
  latitude: number;
  longitude: number;
  region_group?: string;
}

interface LiveSnapshot {
  region_id: string;
  timestamp: string;
  behavior_index: number;
  sub_indices: {
    economic_stress?: number;
    environmental_stress?: number;
    mobility_activity?: number;
    digital_attention?: number;
    public_health_stress?: number;
  };
  sources: string[];
  explanation_summary?: string;
  event_flags: Record<string, boolean>;
}

interface IntelligenceData {
  risk_tier: string;
  top_contributing_indices: Array<{ name: string; contribution_score: number }>;
  shock_status: string;
}

interface LiveRegionData {
  latest: LiveSnapshot;
  history: LiveSnapshot[];
  snapshot_count: number;
  intelligence?: IntelligenceData;
}

interface LiveSummaryResponse {
  timestamp: string;
  regions: Record<string, LiveRegionData | { status: string; message: string }>;
}

export default function LivePage() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);
  const [liveData, setLiveData] = useState<LiveSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(60); // seconds
  const [timeWindow, setTimeWindow] = useState(60); // minutes

  const fetchRegions = async () => {
    try {
      setError(null);
      const data = await apiFetchRegions();
      if (!Array.isArray(data) || data.length === 0) {
        throw new Error('Regions response is empty or invalid');
      }
      setRegions(data);
      // Set default selections
      const defaultIds = ['us_dc', 'us_mn', 'city_nyc'].filter(id =>
        data.some((r: Region) => r.id === id)
      );
      if (defaultIds.length > 0) {
        setSelectedRegions(defaultIds);
      }
    } catch (e) {
      console.error('Live: failed to load regions', e);
      setError(e instanceof Error ? e.message : 'Failed to load regions');
      setRegions([]); // Ensure regions is empty on error
    }
  };

  const fetchLiveData = async () => {
    if (selectedRegions.length === 0) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8100';
      const params = new URLSearchParams({
        time_window_minutes: timeWindow.toString(),
      });
      selectedRegions.forEach(id => params.append('regions', id));

      const response = await fetch(`${base}/api/live/summary?${params.toString()}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch live data');
      }

      const data: LiveSummaryResponse = await response.json();
      setLiveData(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to fetch live data');
    } finally {
      setLoading(false);
    }
  };

  const triggerRefresh = async () => {
    if (selectedRegions.length === 0) {
      return;
    }

    try {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8100';
      const params = new URLSearchParams();
      selectedRegions.forEach(id => params.append('regions', id));

      const response = await fetch(`${base}/api/live/refresh?${params.toString()}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to trigger refresh');
      }

      // Wait a moment for refresh to complete, then fetch data
      setTimeout(() => {
        fetchLiveData();
      }, 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to trigger refresh');
    }
  };

  useEffect(() => {
    fetchRegions();
  }, []);

  useEffect(() => {
    if (selectedRegions.length > 0) {
      fetchLiveData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRegions, timeWindow]);

  useEffect(() => {
    if (!autoRefresh || selectedRegions.length === 0) {
      return;
    }

    const interval = setInterval(() => {
      fetchLiveData();
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, refreshInterval, selectedRegions, timeWindow]);

  const getEventBadges = (eventFlags: Record<string, boolean>) => {
    const activeEvents = Object.entries(eventFlags).filter(([_, active]) => active);
    if (activeEvents.length === 0) {
      return null;
    }

    return (
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
        {activeEvents.map(([event, _]) => (
          <span
            key={event}
            style={{
              padding: '4px 12px',
              borderRadius: 12,
              fontSize: 11,
              fontWeight: '500',
              backgroundColor: '#dc3545',
              color: 'white',
              textTransform: 'uppercase',
            }}
          >
            {event.replace(/_/g, ' ')}
          </span>
        ))}
      </div>
    );
  };

  return (
    <>
      <Head>
        <title>Live Monitoring - Behavior Convergence Explorer</title>
      </Head>
      <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 1400, margin: '0 auto' }}>
        <h1>Live Behavior Monitoring</h1>
        <p style={{ color: '#555', marginBottom: 24 }}>
          Near real-time monitoring of behavior index values across regions with automatic event detection.
        </p>

        <nav style={{ marginBottom: 32, display: 'flex', gap: 16 }}>
          <Link href="/forecast" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Single Forecast
          </Link>
          <Link href="/playground" style={{ textDecoration: 'underline', color: '#0070f3' }}>
            Playground
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
            <div style={{ marginBottom: 8 }}>
              <span data-testid="live-selected-count">Selected: {selectedRegions.length} regions</span>
            </div>
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
            <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
              <button
                type="button"
                onClick={() => setSelectedRegions([])}
                data-testid="live-clear-selection"
                style={{ padding: '4px 8px', fontSize: 12, backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}
              >
                Clear Selection
              </button>
              <button
                type="button"
                onClick={() => {
                  const sortedRegions = [...regions].sort((a, b) => a.id.localeCompare(b.id));
                  const firstRegion = sortedRegions[0];
                  if (firstRegion) {
                    setSelectedRegions([firstRegion.id]);
                  }
                }}
                disabled={regions.length === 0}
                data-testid="live-select-1"
                style={{ padding: '4px 8px', fontSize: 12, backgroundColor: regions.length === 0 ? '#ccc' : '#0070f3', color: 'white', border: 'none', borderRadius: 4, cursor: regions.length === 0 ? 'not-allowed' : 'pointer' }}
              >
                Select 1
              </button>
              <button
                type="button"
                onClick={() => {
                  const sortedRegions = [...regions].sort((a, b) => a.id.localeCompare(b.id));
                  if (sortedRegions.length >= 3) {
                    setSelectedRegions(sortedRegions.slice(0, 3).map(r => r.id));
                  }
                }}
                disabled={regions.length < 3}
                data-testid="live-select-3"
                style={{ padding: '4px 8px', fontSize: 12, backgroundColor: regions.length < 3 ? '#ccc' : '#0070f3', color: 'white', border: 'none', borderRadius: 4, cursor: regions.length < 3 ? 'not-allowed' : 'pointer' }}
              >
                Select 3
              </button>
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 'bold' }}>
              Time Window (minutes): {timeWindow}
            </label>
            <input
              type="range"
              min="15"
              max="1440"
              step="15"
              value={timeWindow}
              onChange={(e) => setTimeWindow(parseInt(e.target.value))}
              style={{ width: '100%', maxWidth: 400 }}
            />
          </div>

          <div style={{ marginBottom: 16, display: 'flex', gap: 24, alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              <span>Auto-refresh</span>
            </label>

            {autoRefresh && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <label style={{ fontSize: 14 }}>Interval (seconds):</label>
                <input
                  type="number"
                  min="30"
                  max="300"
                  step="30"
                  value={refreshInterval}
                  onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
                  style={{ width: 80, padding: 4 }}
                />
              </div>
            )}

            <button
              type="button"
              onClick={triggerRefresh}
              disabled={loading || selectedRegions.length === 0}
              style={{
                padding: '8px 16px',
                fontSize: 14,
                backgroundColor: loading || selectedRegions.length === 0 ? '#ccc' : '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: 4,
                cursor: loading || selectedRegions.length === 0 ? 'not-allowed' : 'pointer',
              }}
              data-testid="live-refresh"
            >
              {loading ? 'Refreshing...' : 'Refresh Now'}
            </button>
          </div>

          {liveData && (
            <div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>
              Last updated: {new Date(liveData.timestamp).toLocaleString()}
            </div>
          )}
        </section>

        {error && (
          <section style={{ padding: 16, backgroundColor: '#f8d7da', color: '#721c24', borderRadius: 4, marginBottom: 24 }}>
            <strong>Error:</strong> {error}
          </section>
        )}

        {liveData && (
          <section>
            <h2>Live Data</h2>

            {/* Intelligence Summary Card */}
            {Object.entries(liveData.regions).some(
              ([_, data]) => 'intelligence' in data && (data as LiveRegionData).intelligence
            ) && (
              <div
                data-testid="live-intel-summary"
                style={{
                  marginBottom: 24,
                  padding: 20,
                  border: '1px solid #ddd',
                  borderRadius: 8,
                  backgroundColor: '#f8f9fa',
                }}
              >
                <h3 style={{ marginTop: 0, marginBottom: 16 }}>Intelligence Summary</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 16 }}>
                  {Object.entries(liveData.regions).map(([regionId, regionData]) => {
                    if ('status' in regionData || !regionData.intelligence) {
                      return null;
                    }
                    const intel = regionData.intelligence;
                    return (
                      <div
                        key={regionId}
                        style={{
                          padding: 16,
                          border: '1px solid #ddd',
                          borderRadius: 4,
                          backgroundColor: 'white',
                        }}
                      >
                        <h4 style={{ marginTop: 0, marginBottom: 12, fontSize: 14 }}>{regionId}</h4>
                        <div style={{ marginBottom: 8 }}>
                          <strong>Risk Tier:</strong>{' '}
                          <span data-testid="live-intel-risk-tier" style={{ fontWeight: 'bold' }}>
                            {intel.risk_tier}
                          </span>
                        </div>
                        <div style={{ marginBottom: 8 }}>
                          <strong>Shock Status:</strong>{' '}
                          <span data-testid="live-intel-shock-status">
                            {intel.shock_status}
                          </span>
                        </div>
                        {intel.top_contributing_indices && intel.top_contributing_indices.length > 0 && (
                          <div>
                            <strong>Top Contributing Indices:</strong>
                            <ul data-testid="live-intel-top-indices" style={{ margin: '8px 0 0 0', paddingLeft: 20, fontSize: 12 }}>
                              {intel.top_contributing_indices.map((idx, i) => (
                                <li key={i}>
                                  {idx.name}: {idx.contribution_score.toFixed(3)}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 24 }}>
              {Object.entries(liveData.regions).map(([regionId, regionData]) => {
                if ('status' in regionData && regionData.status === 'no_data') {
                  return (
                    <div key={regionId} data-testid={`live-region-card-${regionId}`} style={{ padding: 20, border: '1px solid #ddd', borderRadius: 8, backgroundColor: 'white' }}>
                      <h3 style={{ marginTop: 0 }}>{regionId}</h3>
                      <p style={{ color: '#666', fontSize: 14 }}>{regionData.message}</p>
                    </div>
                  );
                }

                const data = regionData as LiveRegionData;
                const latest = data.latest;
                const behaviorIndex = latest.behavior_index;

                return (
                  <div key={regionId} data-testid={`live-region-card-${regionId}`} style={{ padding: 20, border: '1px solid #ddd', borderRadius: 8, backgroundColor: 'white' }}>
                    <h3 style={{ marginTop: 0, marginBottom: 8 }}>
                      {regionId}
                    </h3>

                    <div style={{ marginBottom: 16 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                        <span style={{ fontWeight: 'bold', fontSize: 18 }}>
                          Behavior Index: {behaviorIndex.toFixed(3)}
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
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 8 }}>
                        Updated: {new Date(latest.timestamp).toLocaleString()}
                      </div>
                      {getEventBadges(latest.event_flags)}
                    </div>

                    {latest.sub_indices && (
                      <div style={{ marginBottom: 16 }}>
                        <h4 style={{ fontSize: 14, marginBottom: 8 }}>Sub-Indices:</h4>
                        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                          <tbody>
                            {latest.sub_indices.economic_stress !== undefined && (
                              <tr>
                                <td style={{ padding: 4 }}>Economic Stress:</td>
                                <td style={{ padding: 4, textAlign: 'right', fontFamily: 'monospace' }}>
                                  {latest.sub_indices.economic_stress.toFixed(3)}
                                </td>
                              </tr>
                            )}
                            {latest.sub_indices.environmental_stress !== undefined && (
                              <tr>
                                <td style={{ padding: 4 }}>Environmental Stress:</td>
                                <td style={{ padding: 4, textAlign: 'right', fontFamily: 'monospace' }}>
                                  {latest.sub_indices.environmental_stress.toFixed(3)}
                                </td>
                              </tr>
                            )}
                            {latest.sub_indices.mobility_activity !== undefined && (
                              <tr>
                                <td style={{ padding: 4 }}>Mobility Activity:</td>
                                <td style={{ padding: 4, textAlign: 'right', fontFamily: 'monospace' }}>
                                  {latest.sub_indices.mobility_activity.toFixed(3)}
                                </td>
                              </tr>
                            )}
                            {latest.sub_indices.digital_attention !== undefined && (
                              <tr>
                                <td style={{ padding: 4 }}>Digital Attention:</td>
                                <td style={{ padding: 4, textAlign: 'right', fontFamily: 'monospace' }}>
                                  {latest.sub_indices.digital_attention.toFixed(3)}
                                </td>
                              </tr>
                            )}
                            {latest.sub_indices.public_health_stress !== undefined && (
                              <tr>
                                <td style={{ padding: 4 }}>Public Health Stress:</td>
                                <td style={{ padding: 4, textAlign: 'right', fontFamily: 'monospace' }}>
                                  {latest.sub_indices.public_health_stress.toFixed(3)}
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {latest.explanation_summary && (
                      <div style={{ marginTop: 16, padding: 12, backgroundColor: '#e7f3ff', borderRadius: 4 }}>
                        <h4 style={{ fontSize: 14, marginTop: 0, marginBottom: 8 }}>Summary:</h4>
                        <p style={{ fontSize: 12, margin: 0, color: '#555' }}>
                          {latest.explanation_summary}
                        </p>
                      </div>
                    )}

                    {data.history && data.history.length > 0 && (
                      <div style={{ marginTop: 16, fontSize: 11, color: '#666' }}>
                        <strong>History:</strong> {data.snapshot_count} snapshots in the last {timeWindow} minutes
                      </div>
                    )}

                    {latest.sources && latest.sources.length > 0 && (
                      <div style={{ marginTop: 12, fontSize: 11, color: '#666' }}>
                        <strong>Sources:</strong> {latest.sources.join(', ')}
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
