'use client';

import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRegions } from '../hooks/useRegions';

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
    marginBottom: '6px',
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
  label: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#666',
    marginBottom: '4px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  input: {
    padding: '8px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    width: '100%',
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
  iframe: {
    width: '100%',
    height: '500px',
    border: 'none',
    borderRadius: '6px',
  },
};

// Grafana Dashboard Embed Component
function GrafanaDashboardEmbed({ dashboardUid, title, regionId }: { dashboardUid: string; title: string; regionId?: string }) {
  const grafanaBase = process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3001';
  const regionParam = regionId ? `&var-region=${encodeURIComponent(regionId)}` : '';
  const src = `${grafanaBase}/d/${dashboardUid}?orgId=1&theme=light&kiosk=tv${regionParam}`;

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
        style={styles.iframe}
        title={title}
        allow="fullscreen"
      />
    </div>
  );
}

export default function PlaygroundPage() {
  const { regions, loading: regionsLoading, error: regionsError, reload: reloadRegions } = useRegions();
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);

  // Set default region when regions load successfully
  useEffect(() => {
    if (!regionsLoading && regions.length > 0 && !selectedRegion) {
      const defaultRegion = regions.find((r: Region) => r.id === 'us_dc') ||
                           regions.find((r: Region) => r.id === 'us_mn') ||
                           regions[0];
      if (defaultRegion) {
        setSelectedRegion(defaultRegion);
      }
    }
  }, [regions, regionsLoading, selectedRegion]);

  return (
    <>
      <Head>
        <title>Live Playground - Behavior Convergence Explorer</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <div style={styles.container}>
        {/* Header Navigation */}
        <header style={styles.header}>
          <nav style={styles.nav}>
            <Link href="/forecast" style={styles.navLink}>
              Behavior Forecast
            </Link>
            <Link href="/playground" style={{ ...styles.navLink, ...styles.navLinkActive }}>
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
          <strong>Interactive Analytics Playground</strong>
          <br />
          Explore behavior indices and sub-indices across regions using live Grafana dashboards.
          Select a region below to update the visualizations in real-time.
        </div>

        {/* Region Selection */}
        <div style={styles.card}>
          <h2 style={{ margin: '0 0 12px 0', fontSize: '18px', fontWeight: '600' }}>Region Selection</h2>
          <div>
            <label style={styles.label}>Select Region</label>
            <select
              value={selectedRegion?.id || ''}
              onChange={(e) => {
                const region = regions.find((r) => r.id === e.target.value);
                if (region) setSelectedRegion(region);
              }}
              style={styles.input}
              aria-label="Select region for playground"
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
              <p style={{ margin: '8px 0 0 0', fontSize: '13px', color: '#666' }}>
                <strong>Selected:</strong> {selectedRegion.name} ({selectedRegion.country})
                {' '}- {selectedRegion.latitude.toFixed(4)}, {selectedRegion.longitude.toFixed(4)}
              </p>
            )}
          </div>
        </div>

        {/* Grafana Dashboard Embeds */}
        <GrafanaDashboardEmbed
          dashboardUid="behavior-index-global"
          title="Behavior Index - Regional View"
          regionId={selectedRegion?.id}
        />

        <GrafanaDashboardEmbed
          dashboardUid="subindex-deep-dive"
          title="Sub-Index Analysis - Deep Dive"
          regionId={selectedRegion?.id}
        />
      </div>
    </>
  );
}
