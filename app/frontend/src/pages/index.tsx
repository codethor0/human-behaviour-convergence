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
  forecastConfig: {
    backgroundColor: '#fff',
    padding: '20px',
    borderRadius: '8px',
    marginBottom: '20px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  configRow: {
    display: 'flex',
    gap: '20px',
    alignItems: 'center',
    marginBottom: '12px',
    flexWrap: 'wrap' as const,
  },
  configLabel: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#333',
    minWidth: '120px',
  },
  configInput: {
    padding: '8px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    width: '100px',
  },
  generateButton: {
    padding: '10px 24px',
    fontSize: '16px',
    fontWeight: '600',
    backgroundColor: '#0070f3',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  infoBox: {
    backgroundColor: '#f8f9fa',
    padding: '16px',
    borderRadius: '8px',
    marginBottom: '20px',
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#333',
  },
  infoTitle: {
    fontWeight: '600',
    marginBottom: '8px',
  },
};

export default function HomePage() {
  const { regions, loading: regionsLoading, error: regionsError } = useRegions();
  const [selectedRegion, setSelectedRegion] = useState<string>('');
  const [historicalDays, setHistoricalDays] = useState<number>(30);
  const [forecastHorizon, setForecastHorizon] = useState<number>(7);

  useEffect(() => {
    if (!regionsLoading && regions.length > 0 && !selectedRegion) {
      const defaultRegion = regions.find((r: Region) => r.id === 'city_nyc') || regions[0];
      if (defaultRegion) {
        setSelectedRegion(defaultRegion.id);
      }
    }
  }, [regions, regionsLoading, selectedRegion]);

  const handleGenerateForecast = async () => {
    // Navigate to forecast page or trigger forecast generation
    window.location.href = `/forecast?region=${selectedRegion}&historicalDays=${historicalDays}&horizon=${forecastHorizon}`;
  };

  const selectedRegionData = regions.find((r: Region) => r.id === selectedRegion);

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
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
          }
          [data-testid^="dashboard-embed-"] {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            min-height: 200px !important;
          }
          [data-testid^="dashboard-embed-"] iframe {
            display: block !important;
            visibility: visible !important;
            min-height: 200px !important;
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
            <Link href="/advanced-visualizations" style={styles.navLink}>
              Advanced Visualizations
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

        {/* Executive Storyboard Section */}
        <section id="executive-storyboard" className="dashboard-section" style={styles.dashboardSection}>
          <h2 style={styles.sectionTitle}>Executive Storyboard</h2>
          <div style={{ marginBottom: '20px', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px', fontSize: '14px', lineHeight: '1.6', color: '#333' }}>
            <p style={{ margin: '0 0 12px 0', fontWeight: '600' }}>
              High-level overview: Global KPIs, regional stress distribution, and key insights at a glance.
            </p>
            <p style={{ margin: '0', fontSize: '13px', color: '#666' }}>
              <strong>New:</strong> Storytelling visualization with narrative panels and executive-grade insights.
            </p>
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="executive-storyboard"
              title="Executive Storyboard"
              regionId={selectedRegion}
              height={600}
            />
          </div>
        </section>

        {/* Storytelling Dashboards Section */}
        <section id="storytelling-dashboards" className="dashboard-section" style={styles.dashboardSection}>
          <h2 style={styles.sectionTitle}>Storytelling Visualizations</h2>
          <div style={{ marginBottom: '20px', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px', fontSize: '14px', lineHeight: '1.6', color: '#333' }}>
            <p style={{ margin: '0 0 12px 0', fontWeight: '600' }}>
              Narrative-driven dashboards: Compare regions, analyze shocks, and evaluate forecast performance.
            </p>
          </div>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }}>
            <GrafanaDashboardEmbed
              dashboardUid="shock-recovery-timeline"
              title="Shock & Recovery Timeline"
              regionId={selectedRegion}
              height={500}
            />
            <GrafanaDashboardEmbed
              dashboardUid="regional-comparison-storyboard"
              title="Regional Comparison"
              regionId={selectedRegion}
              height={500}
            />
            <GrafanaDashboardEmbed
              dashboardUid="forecast-performance-storybook"
              title="Forecast Performance"
              regionId={selectedRegion}
              height={500}
            />
          </div>
        </section>

        {/* Behavior Forecast Section */}
        <section id="behavior-forecast" className="dashboard-section" style={styles.dashboardSection}>
          <h2 style={styles.sectionTitle}>Behavior Forecast</h2>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="forecast-summary"
              title="Behavior Forecast"
              regionId={selectedRegion}
              height={500}
            />
          </div>
        </section>

        {/* Live Playground Section */}
        <section id="live-playground" className="dashboard-section" style={styles.dashboardSection}>
          <h2 style={styles.sectionTitle}>Live Playground</h2>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="forecast-overview"
              title="Live Playground"
              regionId={selectedRegion}
              height={500}
              refreshInterval="30s"
            />
          </div>
        </section>

        {/* Live Monitoring Section */}
        <section id="live-monitoring" className="dashboard-section" style={styles.dashboardSection}>
          <h2 style={styles.sectionTitle}>Live Monitoring</h2>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="forecast-overview"
              title="Live Monitoring"
              regionId={selectedRegion}
              height={500}
              refreshInterval="30s"
            />
          </div>
        </section>

        {/* Results Dashboard Section */}
        <section id="results-dashboard" className="dashboard-section" style={styles.dashboardSection}>
          <h2 style={styles.sectionTitle}>Results Dashboard</h2>
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="public-overview"
              title="Results Dashboard"
              regionId={selectedRegion}
              height={500}
            />
          </div>
        </section>

        {/* Analytics Powered by Grafana Section */}
        <section id="grafana-analytics" className="dashboard-section" style={styles.dashboardSection}>
          <h2 style={styles.sectionTitle}>Analytics Powered by Grafana</h2>
          <div style={{ marginBottom: '20px', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px', fontSize: '14px', lineHeight: '1.6', color: '#333' }}>
            <p style={{ margin: '0 0 12px 0', fontWeight: '600' }}>
              Deep-dive analytics and time-series visualizations are now powered by Grafana dashboards below.
            </p>
            <p style={{ margin: '0 0 12px 0' }}>
              Forecast data is fetched from the backend API and metrics are exposed to Prometheus for real-time monitoring.
            </p>
            <p style={{ margin: '0', fontSize: '13px', color: '#666' }}>
              <strong>Note:</strong> Some indices (economic_stress, mobility_activity) are global/national and appear identical across regions by design. Region-specific indices (environmental_stress, political_stress) will differ. Grafana region dropdown populates as metrics become available (warm-up: ~5-10 minutes after stack start).
            </p>
          </div>

          {/* Regional Forecast Overview & Key Metrics */}
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="forecast-summary"
              title="Regional Forecast Overview & Key Metrics"
              regionId={selectedRegion}
              height={500}
            />
          </div>

          {/* Behavior Index Timeline & Historical Trends */}
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="behavior-index-global"
              title="Behavior Index Timeline & Historical Trends"
              regionId={selectedRegion}
              height={500}
            />
          </div>

          {/* Sub-Index Components & Contributing Factors */}
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="subindex-deep-dive"
              title="Sub-Index Components & Contributing Factors"
              regionId={selectedRegion}
              height={500}
            />
          </div>

          {/* Regional Variance Explorer - Multi-Region Comparison */}
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="regional-variance-explorer"
              title="Regional Variance Explorer - Multi-Region Comparison"
              regionId={selectedRegion}
              height={500}
            />
          </div>

          {/* Forecast Quality and Drift Analysis */}
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="forecast-quality-drift"
              title="Forecast Quality and Drift Analysis"
              regionId={selectedRegion}
              height={500}
            />
          </div>

          {/* Algorithm / Model Performance Comparison */}
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="algorithm-model-comparison"
              title="Algorithm / Model Performance Comparison"
              regionId={selectedRegion}
              height={500}
            />
          </div>

          {/* Real-Time Data Source Status & API Health */}
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="data-sources-health"
              title="Real-Time Data Source Status & API Health"
              height={500}
              refreshInterval="30s"
            />
          </div>

          {/* Source Health and Freshness - Detailed Monitoring */}
          <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
            <GrafanaDashboardEmbed
              dashboardUid="source-health-freshness"
              title="Source Health and Freshness - Detailed Monitoring"
              height={500}
              refreshInterval="30s"
            />
          </div>

          {/* Additional Dashboards - All Others */}
          <div style={{ marginTop: '40px', paddingTop: '40px', borderTop: '2px solid #e0e0e0' }}>
            <h3 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '20px', color: '#000' }}>Additional Analytics Dashboards</h3>

            <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
              <GrafanaDashboardEmbed
                dashboardUid="hbc-anomaly-atlas"
                title="Anomaly Atlas and Regime Shifts"
                regionId={selectedRegion}
                height={600}
              />
            </div>

            <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
              <GrafanaDashboardEmbed
                dashboardUid="cross-domain-correlation"
                title="Cross-Domain Correlation Analysis"
                regionId={selectedRegion}
                height={400}
              />
              <GrafanaDashboardEmbed
                dashboardUid="regional-deep-dive"
                title="Regional Deep Dive Analysis"
                regionId={selectedRegion}
                height={400}
              />
            </div>

            <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
              <GrafanaDashboardEmbed
                dashboardUid="regional-comparison"
                title="Regional Comparison Matrix"
                regionId={selectedRegion}
                height={400}
              />
              <GrafanaDashboardEmbed
                dashboardUid="regional-signals"
                title="Regional Signals Analysis"
                regionId={selectedRegion}
                height={400}
              />
            </div>

            <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
              <GrafanaDashboardEmbed
                dashboardUid="geo-map"
                title="Geographic Map Visualization"
                regionId={selectedRegion}
                height={400}
              />
              <GrafanaDashboardEmbed
                dashboardUid="anomaly-detection-center"
                title="Anomaly Detection Center"
                regionId={selectedRegion}
                height={400}
              />
            </div>

            <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
              <GrafanaDashboardEmbed
                dashboardUid="risk-regimes"
                title="Risk Regimes Analysis"
                regionId={selectedRegion}
                height={400}
              />
              <GrafanaDashboardEmbed
                dashboardUid="model-performance"
                title="Model Performance Hub"
                regionId={selectedRegion}
                height={400}
              />
            </div>

            <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
              <GrafanaDashboardEmbed
                dashboardUid="historical-trends"
                title="Historical Trends Analysis"
                regionId={selectedRegion}
                height={400}
              />
              <GrafanaDashboardEmbed
                dashboardUid="contribution-breakdown"
                title="Contribution Breakdown Analysis"
                regionId={selectedRegion}
                height={400}
              />
            </div>

            <div style={{ ...styles.dashboardGrid, ...styles.gridCols2 }} className="dashboard-grid-cols-2">
              <GrafanaDashboardEmbed
                dashboardUid="baselines"
                title="Baseline Models Comparison"
                regionId={selectedRegion}
                height={400}
              />
              <GrafanaDashboardEmbed
                dashboardUid="classical-models"
                title="Classical Forecasting Models"
                regionId={selectedRegion}
                height={400}
              />
            </div>

            <div style={{ ...styles.dashboardGrid, ...styles.gridCols1 }}>
              <GrafanaDashboardEmbed
                dashboardUid="data-sources-health-enhanced"
                title="Data Sources Health Enhanced"
                height={400}
                refreshInterval="30s"
              />
            </div>
          </div>
        </section>

        {/* Forecast Configuration */}
        <section style={styles.forecastConfig}>
          <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '20px', color: '#000' }}>
            Forecast Configuration
          </h2>
          <div style={styles.configRow}>
            <span style={styles.configLabel}>Region</span>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              style={{ ...styles.regionSelect, minWidth: '250px' }}
              disabled={regionsLoading || regions.length === 0}
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
            {selectedRegionData && (
              <span style={{ fontSize: '13px', color: '#666' }}>
                {selectedRegionData.latitude}, {selectedRegionData.longitude}
              </span>
            )}
          </div>
          <div style={styles.configRow}>
            <span style={styles.configLabel}>Historical Days:</span>
            <input
              type="number"
              value={historicalDays}
              onChange={(e) => setHistoricalDays(parseInt(e.target.value) || 30)}
              min="7"
              max="365"
              style={styles.configInput}
            />
          </div>
          <div style={styles.configRow}>
            <span style={styles.configLabel}>Forecast Horizon:</span>
            <input
              type="number"
              value={forecastHorizon}
              onChange={(e) => setForecastHorizon(parseInt(e.target.value) || 7)}
              min="1"
              max="30"
              style={styles.configInput}
            />
            <span style={{ fontSize: '13px', color: '#666' }}>days</span>
          </div>
          <div style={styles.configRow}>
            <button
              onClick={handleGenerateForecast}
              style={styles.generateButton}
              disabled={!selectedRegion || regionsLoading}
              onMouseEnter={(e) => {
                if (!e.currentTarget.disabled) {
                  e.currentTarget.style.backgroundColor = '#0051cc';
                }
              }}
              onMouseLeave={(e) => {
                if (!e.currentTarget.disabled) {
                  e.currentTarget.style.backgroundColor = '#0070f3';
                }
              }}
            >
              Generate Forecast
            </button>
          </div>
        </section>
      </div>
    </>
  );
}
