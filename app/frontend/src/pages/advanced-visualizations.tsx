'use client';

import { useState } from 'react';
import Head from 'next/head';
import { ConvergenceVortex } from '../components/advanced/ConvergenceVortex';
import { PredictiveHorizonClouds } from '../components/advanced/PredictiveHorizonClouds';
import { useRegions } from '../hooks/useRegions';

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
  header: {
    marginBottom: '30px',
  },
  title: {
    fontSize: '32px',
    fontWeight: '700',
    marginBottom: '10px',
  },
  subtitle: {
    fontSize: '16px',
    color: '#a0a0a0',
    marginBottom: '20px',
  },
  controls: {
    display: 'flex',
    gap: '20px',
    alignItems: 'center',
    marginBottom: '30px',
    padding: '15px',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: '8px',
  },
  regionSelect: {
    padding: '8px 12px',
    fontSize: '14px',
    backgroundColor: '#1a1f3a',
    color: '#ffffff',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: '4px',
    minWidth: '200px',
  },
  visualizationGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr',
    gap: '30px',
  },
  visualizationPanel: {
    backgroundColor: '#1a1f3a',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    minHeight: '600px',
  },
  panelTitle: {
    fontSize: '20px',
    fontWeight: '600',
    marginBottom: '20px',
    color: '#ffffff',
    textTransform: 'uppercase' as const,
    letterSpacing: '1px',
  },
};

export default function AdvancedVisualizations() {
  const { regions, loading: regionsLoading } = useRegions();
  const [selectedRegion, setSelectedRegion] = useState<string>('');

  return (
    <>
      <Head>
        <title>Advanced Visualizations - HBC Intelligence</title>
        <meta name="description" content="Advanced data visualizations for behavioral intelligence" />
      </Head>
      <div style={styles.container}>
        <div style={styles.header}>
          <h1 style={styles.title}>Advanced Visualizations</h1>
          <p style={styles.subtitle}>
            Multi-dimensional visualizations revealing hidden patterns and predictive insights
          </p>
        </div>

        <div style={styles.controls}>
          <label style={{ fontSize: '14px' }}>Region:</label>
          <select
            value={selectedRegion}
            onChange={(e) => setSelectedRegion(e.target.value)}
            style={styles.regionSelect}
            disabled={regionsLoading}
          >
            <option value="">All Regions (Global)</option>
            {regions.map((r: any) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.country})
              </option>
            ))}
          </select>
        </div>

        <div style={styles.visualizationGrid}>
          {/* Convergence Vortex */}
          <div style={styles.visualizationPanel}>
            <div style={styles.panelTitle}>Convergence Vortex</div>
            <ConvergenceVortex region={selectedRegion || null} width={800} height={600} />
          </div>

          {/* Predictive Horizon Clouds */}
          <div style={styles.visualizationPanel}>
            <div style={styles.panelTitle}>Predictive Horizon Clouds</div>
            <PredictiveHorizonClouds region={selectedRegion || null} width={800} height={400} />
          </div>
        </div>
      </div>
    </>
  );
}
