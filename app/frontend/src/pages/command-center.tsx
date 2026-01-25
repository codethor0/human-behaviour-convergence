'use client';

import { useEffect, useState } from 'react';
import Head from 'next/head';
import { BehaviorIndexFuelGauge } from '../components/command-center/BehaviorIndexFuelGauge';
import { CriticalAlertsTicker } from '../components/command-center/CriticalAlertsTicker';
import { RegionalComparisonMatrix } from '../components/command-center/RegionalComparisonMatrix';
import { WarningRadar } from '../components/command-center/WarningRadar';
import { ConfidenceThermometer } from '../components/command-center/ConfidenceThermometer';
import { InsightOfTheDay } from '../components/command-center/InsightOfTheDay';

const styles = {
  container: {
    fontFamily: 'system-ui, -apple-system, sans-serif',
    width: '100%',
    minHeight: '100vh',
    backgroundColor: '#0a0e27',
    color: '#ffffff',
    padding: '20px',
    boxSizing: 'border-box' as const,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gridTemplateRows: 'repeat(2, 1fr)',
    gap: '20px',
    height: 'calc(100vh - 40px)',
    maxWidth: '1920px',
    margin: '0 auto',
  },
  panel: {
    backgroundColor: '#1a1f3a',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  panelTitle: {
    fontSize: '18px',
    fontWeight: '600',
    marginBottom: '16px',
    color: '#ffffff',
    textTransform: 'uppercase' as const,
    letterSpacing: '1px',
  },
  panelContent: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
};

export default function CommandCenter() {
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);

  return (
    <>
      <Head>
        <title>Command Center - HBC Intelligence</title>
        <meta name="description" content="Executive Command Center for Behavioral Intelligence" />
      </Head>
      <div style={styles.container}>
        <div style={styles.grid}>
          {/* Panel 1: Behavior Index Fuel Gauge */}
          <div style={styles.panel}>
            <div style={styles.panelTitle}>Behavior Index</div>
            <div style={styles.panelContent}>
              <BehaviorIndexFuelGauge region={selectedRegion} />
            </div>
          </div>

          {/* Panel 2: Critical Alerts Ticker */}
          <div style={styles.panel}>
            <div style={styles.panelTitle}>Critical Alerts</div>
            <div style={styles.panelContent}>
              <CriticalAlertsTicker />
            </div>
          </div>

          {/* Panel 3: Regional Comparison Matrix */}
          <div style={styles.panel}>
            <div style={styles.panelTitle}>Regional Overview</div>
            <div style={styles.panelContent}>
              <RegionalComparisonMatrix onRegionSelect={setSelectedRegion} />
            </div>
          </div>

          {/* Panel 4: 72-Hour Warning Radar */}
          <div style={styles.panel}>
            <div style={styles.panelTitle}>72-Hour Risk Radar</div>
            <div style={styles.panelContent}>
              <WarningRadar region={selectedRegion} />
            </div>
          </div>

          {/* Panel 5: Confidence Thermometer */}
          <div style={styles.panel}>
            <div style={styles.panelTitle}>Data Quality</div>
            <div style={styles.panelContent}>
              <ConfidenceThermometer />
            </div>
          </div>

          {/* Panel 6: Insight of the Day */}
          <div style={styles.panel}>
            <div style={styles.panelTitle}>Daily Insight</div>
            <div style={styles.panelContent}>
              <InsightOfTheDay />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
