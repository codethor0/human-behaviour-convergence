'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Head from 'next/head';
import { GrafanaDashboardEmbed } from '../components/GrafanaDashboardEmbed';
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
    maxWidth: '1920px',
    margin: '0 auto',
    padding: '10px',
    backgroundColor: '#f5f5f5',
    minHeight: '100vh',
  },
  header: {
    backgroundColor: '#fff',
    padding: '12px 16px',
    marginBottom: '8px',
    borderRadius: '6px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    position: 'sticky' as const,
    top: 0,
    zIndex: 100,
  },
  nav: {
    display: 'flex',
    gap: '24px',
    alignItems: 'center',
    flexWrap: 'wrap' as const,
    marginBottom: '12px',
  },
  navLink: {
    textDecoration: 'none',
    color: '#0070f3',
    fontSize: '14px',
    fontWeight: '500',
    padding: '6px 0',
  },
  navLinkHighlight: {
    textDecoration: 'none',
    color: '#00ff88',
    fontSize: '14px',
    fontWeight: '600',
    padding: '6px 0',
    backgroundColor: 'rgba(0, 255, 136, 0.1)',
    borderRadius: '4px',
    paddingLeft: '8px',
    paddingRight: '8px',
    borderBottom: '2px solid transparent',
  },
  navLinkActive: {
    borderBottomColor: '#0070f3',
  },
  regionSelector: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 12px',
    backgroundColor: '#f8f9fa',
    borderRadius: '6px',
    marginTop: '8px',
  },
  regionLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#666',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  regionSelect: {
    padding: '6px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    minWidth: '200px',
  },
  dashboardSection: {
    marginBottom: '40px',
  },
  sectionTitle: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#000',
    marginBottom: '16px',
    paddingBottom: '8px',
    borderBottom: '2px solid #0070f3',
  },
  dashboardGrid: {
    display: 'grid',
    gap: '12px',
  },
  gridCols1: {
    gridTemplateColumns: '1fr',
  },
  gridCols2: {
    gridTemplateColumns: 'repeat(2, 1fr)',
  },
  gridCols4: {
    gridTemplateColumns: 'repeat(4, 1fr)',
  },
};

export default function HomePage() {
  const { regions, loading: regionsLoading, error: regionsError } = useRegions();
  const [selectedRegion, setSelectedRegion] = useState<string>('');

  useEffect(() => {
    if (!regionsLoading && regions.length > 0 && !selectedRegion) {
      const defaultRegion = regions.find((r: Region) => r.id === 'city_nyc') || regions[0];
      if (defaultRegion) {
        setSelectedRegion(defaultRegion.id);
      }
    }
  }, [regions, regionsLoading, selectedRegion]);

  return (
    <>
      <Head>
        <title>Behavior Convergence Explorer - Command Center</title>
        <meta name="description" content="Comprehensive behavioral forecasting and analytics dashboard" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>{`
          @media (max-width: 1279px) {
            .dashboard-grid-cols-2 { grid-template-columns: 1fr !important; }
            .dashboard-grid-cols-4 { grid-template-columns: repeat(2, 1fr) !important; }
          }
          @media (max-width: 767px) {
            .dashboard-grid-cols-2 { grid-template-columns: 1fr !important; }
            .dashboard-grid-cols-4 { grid-template-columns: 1fr !important; }
          }
          .dashboard-section {
            min-height: 300px;
          }
        `}</style>
      </Head>
      <div style={styles.container}>
        <header style={styles.header}>
          <nav style={styles.nav}>
            <Link href="/" style={{ ...styles.navLink, ...styles.navLinkActive }}>
              Dashboard Hub
            </Link>
            <Link href="/command-center" style={styles.navLinkHighlight}>
              Command Center
            </Link>
            <Link href="/forecast" style={styles.navLink}>
              Generate Forecast
            </Link>
            <Link href="/playground" style={styles.navLink}>
              Live Playground
            </Link>
            <Link href="/live" style={styles.navLink}>
              Live Monitoring
            </Link>
            <Link href="/history" style={styles.navLink}>
              Forecast History
            </Link>
          </nav>
          <div style={styles.regionSelector}>
            <span style={styles.regionLabel}>Global Region:</span>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              style={styles.regionSelect}
              disabled={regionsLoading || regions.length === 0}
              data-testid="global-region-selector"
            >
              {regionsLoading ? (
                <option value="">Loading regions...</option>
              ) : regionsError ? (
                <option value="">Error loading regions</option>
              ) : regions.length === 0 ? (
                <option value="">No regions available</option>
              ) : (
                regions.map((r: Region) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.country})
                  </option>
                ))
              )}
            </select>
          </div>
        </header>

        {/* Section 1: Executive Command Center */}
        <section id="executive" className="dashboard-section" style={styles.dashboardSection} data-testid="section-executive">
          <h2 style={styles.sectionTitle}>Executive Command Center</h2>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="behavior-index-global"
              title="Behavior Index Timeline & Historical Trends"
              regionId={selectedRegion}
              height={400}
            />
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols4 }} className="dashboard-grid-cols-4">
            <GrafanaDashboardEmbed
              dashboardUid="forecast-summary"
              title="Current Behavior Index"
              regionId={selectedRegion}
              panelId={1}
              height={200}
            />
            <GrafanaDashboardEmbed
              dashboardUid="forecast-summary"
              title="Risk Tier"
              regionId={selectedRegion}
              panelId={2}
              height={200}
            />
            <GrafanaDashboardEmbed
              dashboardUid="forecast-summary"
              title="Trend Direction"
              regionId={selectedRegion}
              panelId={3}
              height={200}
            />
            <GrafanaDashboardEmbed
              dashboardUid="source-health-freshness"
              title="Data Freshness"
              height={200}
            />
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
            <GrafanaDashboardEmbed
              dashboardUid="public-overview"
              title="Public Overview - Executive Summary"
              regionId={selectedRegion}
              height={400}
            />
            <GrafanaDashboardEmbed
              dashboardUid="historical-trends"
              title="Historical Trends & Volatility Analysis"
              regionId={selectedRegion}
              height={400}
            />
          </div>
        </section>

        {/* Section 2: Forecast & Prediction Center */}
        <section id="forecasting" className="dashboard-section" style={styles.dashboardSection} data-testid="section-forecasting">
          <h2 style={styles.sectionTitle}>Forecast & Prediction Center</h2>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="forecast-summary"
              title="Behavior Forecast - Regional Overview"
              regionId={selectedRegion}
              height={500}
            />
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
            <GrafanaDashboardEmbed
              dashboardUid="forecast-quality-drift"
              title="Forecast Quality & Drift Analysis"
              regionId={selectedRegion}
              height={500}
            />
            <GrafanaDashboardEmbed
              dashboardUid="algorithm-model-comparison"
              title="Algorithm Performance Comparison"
              regionId={selectedRegion}
              height={500}
            />
          </div>
        </section>

        {/* Section 3: Real-Time Operations */}
        <section id="operations" className="dashboard-section" style={styles.dashboardSection} data-testid="section-operations">
          <h2 style={styles.sectionTitle}>Real-Time Operations</h2>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="forecast-overview"
              title="Live Monitoring - Real-Time Operations Center"
              regionId={selectedRegion}
              height={400}
              refreshInterval="30s"
            />
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
            <GrafanaDashboardEmbed
              dashboardUid="data-sources-health"
              title="Real-Time Data Source Status & API Health"
              height={400}
              refreshInterval="30s"
            />
            <GrafanaDashboardEmbed
              dashboardUid="data-sources-health-enhanced"
              title="Source Health & Freshness - Detailed Monitoring"
              height={400}
              refreshInterval="30s"
            />
          </div>
        </section>

        {/* Section 4: Multi-Dimensional Analysis */}
        <section id="analysis" className="dashboard-section" style={styles.dashboardSection} data-testid="section-analysis">
          <h2 style={styles.sectionTitle}>Multi-Dimensional Analysis</h2>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="subindex-deep-dive"
              title="Sub-Index Components & Contributing Factors"
              regionId={selectedRegion}
              height={450}
            />
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
            <GrafanaDashboardEmbed
              dashboardUid="cross-domain-correlation"
              title="Economic Behavior Convergence"
              regionId={selectedRegion}
              height={400}
            />
            <GrafanaDashboardEmbed
              dashboardUid="regional-deep-dive"
              title="Environmental Impact Analysis"
              regionId={selectedRegion}
              height={400}
            />
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
            <GrafanaDashboardEmbed
              dashboardUid="regional-comparison"
              title="Social Sentiment Intelligence"
              regionId={selectedRegion}
              height={400}
            />
            <GrafanaDashboardEmbed
              dashboardUid="regional-variance-explorer"
              title="Mobility & Movement Patterns"
              regionId={selectedRegion}
              height={400}
            />
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
            <GrafanaDashboardEmbed
              dashboardUid="regional-signals"
              title="Contribution Breakdown - How Sub-Indices Build Behavior Index"
              regionId={selectedRegion}
              height={400}
            />
            <GrafanaDashboardEmbed
              dashboardUid="geo-map"
              title="Geo Map - Regional Stress Visualization"
              regionId={selectedRegion}
              height={400}
            />
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="forecast-overview"
              title="Forecast Overview - Comprehensive Regional Analysis"
              regionId={selectedRegion}
              height={500}
            />
          </div>
        </section>

        {/* Section 5: Anomaly & Risk Detection */}
        <section id="anomalies" className="dashboard-section" style={styles.dashboardSection} data-testid="section-anomalies">
          <h2 style={styles.sectionTitle}>Anomaly & Risk Detection</h2>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="anomaly-detection-center"
              title="Anomaly Detection Center - Statistical Outlier Analysis"
              regionId={selectedRegion}
              height={500}
            />
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
            <GrafanaDashboardEmbed
              dashboardUid="risk-regimes"
              title="Geopolitical Risk Monitor"
              regionId={selectedRegion}
              height={400}
            />
            <GrafanaDashboardEmbed
              dashboardUid="cross-domain-correlation"
              title="Cross-Domain Correlation Analysis"
              regionId={selectedRegion}
              height={400}
            />
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
            <GrafanaDashboardEmbed
              dashboardUid="baselines"
              title="Shock Intelligence Dashboard - Event Detection & Analysis"
              regionId={selectedRegion}
              height={500}
            />
            <GrafanaDashboardEmbed
              dashboardUid="classical-models"
              title="Classical Forecasting Models - Baseline Comparisons"
              regionId={selectedRegion}
              height={500}
            />
          </div>
        </section>

        {/* Section 6: Data Integrity & System Health */}
        <section id="integrity" className="dashboard-section" style={styles.dashboardSection} data-testid="section-integrity">
          <h2 style={styles.sectionTitle}>Data Integrity & System Health</h2>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="source-health-freshness"
              title="Data Quality & Lineage - Trust & Transparency"
              height={400}
            />
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
            <GrafanaDashboardEmbed
              dashboardUid="data-sources-health"
              title="Prometheus System Health - Internal Metrics"
              height={400}
            />
            <GrafanaDashboardEmbed
              dashboardUid="model-performance"
              title="Model Performance Metrics - Forecast Accuracy Tracking"
              regionId={selectedRegion}
              height={400}
            />
          </div>
        </section>
      </div>
    </>
  );
}
