import React from 'react';
import Head from 'next/head';
import Link from 'next/link';

interface Dashboard {
  title: string;
  uid: string;
  description: string;
  purpose: string;
  url?: string;
}

const dashboards: Dashboard[] = [
  {
    title: 'Global Behavior Index',
    uid: 'behavior-index-global',
    description: 'Overview of behavioral stress metrics for Minnesota and parent sub-indices',
    purpose: 'Quick health check: Is the system showing elevated stress? What are the primary drivers?'
  },
  {
    title: 'Sub-Index Deep Dive',
    uid: 'subindex-deep-dive',
    description: 'Detailed breakdown of parent and child sub-indices for any region',
    purpose: 'Investigation: Which specific stress factors are elevated? How do they correlate?'
  },
  {
    title: 'Regional Comparison',
    uid: 'regional-comparison',
    description: 'Multi-region analytics with behavior index comparison and heatmap',
    purpose: 'Pattern detection: Are multiple regions affected? Is stress localized or systemic?'
  },
  {
    title: 'Historical Trends & Volatility',
    uid: 'historical-trends',
    description: 'Rolling volatility, trend derivatives, and 7-day/30-day comparisons',
    purpose: 'Trend analysis: Is this a spike or sustained shift? How volatile is the situation?'
  },
  {
    title: 'Behavioral Risk Regimes',
    uid: 'risk-regimes',
    description: 'Risk classification (Stable/Elevated/Unstable/Critical) with 30-day history',
    purpose: 'Prioritization: Which regions need immediate attention? Where are regime transitions?'
  }
];

const additionalLinks = [
  {
    title: 'Alert List',
    url: 'http://localhost:3001/alerting/list',
    description: 'Active and resolved alerts from Grafana'
  },
  {
    title: 'Prometheus Targets',
    url: 'http://localhost:9090/targets',
    description: 'Verify metrics scraping health'
  },
  {
    title: 'Backend API Docs',
    url: 'http://localhost:8100/docs',
    description: 'Interactive FastAPI documentation'
  }
];

export default function OperatorConsole() {
  const grafanaBase = process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3001';

  return (
    <>
      <Head>
        <title>Operator Console - Behavior Forecasting</title>
        <meta name="description" content="Operator dashboard index for behavioral forecasting system" />
      </Head>

      <div style={styles.container}>
        <header style={styles.header}>
          <h1 style={styles.title}>Operator Console</h1>
          <p style={styles.subtitle}>
            Behavioral Forecasting System - Dashboard Index & Quick Links
          </p>
        </header>

        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>Grafana Dashboards</h2>
          <p style={styles.sectionDescription}>
            All analytics are powered by Grafana. Each dashboard answers specific operational questions.
          </p>

          <div style={styles.dashboardGrid}>
            {dashboards.map((dashboard) => (
              <div key={dashboard.uid} style={styles.card}>
                <h3 style={styles.cardTitle}>{dashboard.title}</h3>
                <p style={styles.cardDescription}>{dashboard.description}</p>
                <div style={styles.purposeBox}>
                  <strong>Purpose:</strong> {dashboard.purpose}
                </div>
                <a
                  href={`${grafanaBase}/d/${dashboard.uid}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={styles.button}
                >
                  Open Dashboard →
                </a>
              </div>
            ))}
          </div>
        </section>

        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>System Health & Monitoring</h2>
          <div style={styles.linksGrid}>
            {additionalLinks.map((link) => (
              <div key={link.title} style={styles.linkCard}>
                <h4 style={styles.linkTitle}>{link.title}</h4>
                <p style={styles.linkDescription}>{link.description}</p>
                <a
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={styles.linkButton}
                >
                  Open →
                </a>
              </div>
            ))}
          </div>
        </section>

        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>Documentation</h2>
          <div style={styles.docsGrid}>
            <div style={styles.docCard}>
              <h4>Alert Response Runbook</h4>
              <p>Procedures for responding to high index and spike alerts</p>
              <a href="/docs/runbooks/ALERT_RESPONSE.md" style={styles.docLink}>View Runbook</a>
            </div>
            <div style={styles.docCard}>
              <h4>Operator Console Guide</h4>
              <p>How to use dashboards and interpret metrics</p>
              <a href="/docs/OPERATOR_CONSOLE.md" style={styles.docLink}>View Guide</a>
            </div>
            <div style={styles.docCard}>
              <h4>Application Status</h4>
              <p>Current capabilities, recent updates, and roadmap</p>
              <a href="/APP_STATUS.md" style={styles.docLink}>View Status</a>
            </div>
          </div>
        </section>

        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>Other Pages</h2>
          <div style={styles.navGrid}>
            <Link href="/forecast" style={styles.navCard}>
              <h4>Forecast</h4>
              <p>Generate forecasts for specific regions</p>
            </Link>
            <Link href="/playground" style={styles.navCard}>
              <h4>Playground</h4>
              <p>Interactive multi-region exploration</p>
            </Link>
            <Link href="/live" style={styles.navCard}>
              <h4>Live Monitor</h4>
              <p>Real-time behavior monitoring with auto-refresh</p>
            </Link>
          </div>
        </section>
      </div>
    </>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '40px 20px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  header: {
    marginBottom: '40px',
    borderBottom: '2px solid #e0e0e0',
    paddingBottom: '20px'
  },
  title: {
    fontSize: '36px',
    margin: '0 0 10px 0',
    color: '#1a1a1a'
  },
  subtitle: {
    fontSize: '18px',
    margin: 0,
    color: '#666'
  },
  section: {
    marginBottom: '50px'
  },
  sectionTitle: {
    fontSize: '24px',
    marginBottom: '10px',
    color: '#1a1a1a'
  },
  sectionDescription: {
    fontSize: '16px',
    color: '#666',
    marginBottom: '20px'
  },
  dashboardGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
    gap: '20px'
  },
  card: {
    border: '1px solid #ddd',
    borderRadius: '8px',
    padding: '20px',
    backgroundColor: '#fff',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
  },
  cardTitle: {
    fontSize: '20px',
    margin: '0 0 10px 0',
    color: '#1a1a1a'
  },
  cardDescription: {
    fontSize: '14px',
    color: '#666',
    marginBottom: '15px',
    lineHeight: '1.5'
  },
  purposeBox: {
    backgroundColor: '#f5f5f5',
    padding: '12px',
    borderRadius: '4px',
    fontSize: '14px',
    marginBottom: '15px',
    lineHeight: '1.5'
  },
  button: {
    display: 'inline-block',
    padding: '10px 20px',
    backgroundColor: '#0070f3',
    color: '#fff',
    textDecoration: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    fontWeight: 'bold',
    transition: 'background-color 0.2s'
  },
  linksGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '15px'
  },
  linkCard: {
    border: '1px solid #ddd',
    borderRadius: '6px',
    padding: '15px',
    backgroundColor: '#fff'
  },
  linkTitle: {
    fontSize: '16px',
    margin: '0 0 8px 0',
    color: '#1a1a1a'
  },
  linkDescription: {
    fontSize: '13px',
    color: '#666',
    marginBottom: '10px'
  },
  linkButton: {
    display: 'inline-block',
    padding: '6px 12px',
    backgroundColor: '#f0f0f0',
    color: '#333',
    textDecoration: 'none',
    borderRadius: '4px',
    fontSize: '13px',
    border: '1px solid #ddd'
  },
  docsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
    gap: '15px'
  },
  docCard: {
    border: '1px solid #ddd',
    borderRadius: '6px',
    padding: '15px',
    backgroundColor: '#fffbf0'
  },
  docLink: {
    color: '#0070f3',
    textDecoration: 'none',
    fontSize: '14px',
    fontWeight: 'bold'
  },
  navGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '15px'
  },
  navCard: {
    border: '1px solid #ddd',
    borderRadius: '6px',
    padding: '15px',
    backgroundColor: '#f9f9f9',
    textDecoration: 'none',
    color: 'inherit',
    transition: 'border-color 0.2s'
  }
};
