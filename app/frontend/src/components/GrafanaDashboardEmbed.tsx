'use client';

import { useState, useEffect } from 'react';

interface GrafanaDashboardEmbedProps {
  dashboardUid: string;
  title: string;
  regionId?: string;
  height?: string | number;
  refreshInterval?: string;
  panelId?: number;
}

const DEFAULT_HEIGHTS: Record<string, string> = {
  'forecast-summary': '380px',
  'behavior-index-global': '580px',
  'subindex-deep-dive': '1200px',
  'data-sources-health': '500px',
  'regional-variance-explorer': '1000px',
  'forecast-quality-drift': '800px',
  'algorithm-model-comparison': '900px',
  'source-health-freshness': '600px',
  'anomaly-detection-center': '500px',
  'cross-domain-correlation': '600px',
  'forecast-overview': '400px',
  'risk-regimes': '600px',
  'regional-comparison': '500px',
  'regional-deep-dive': '600px',
  'historical-trends': '500px',
  'geo-map': '500px',
  'public-overview': '400px',
  'regional-signals': '500px',
  'baselines': '500px',
  'classical-models': '500px',
  'model-performance': '400px',
  'data-sources-health-enhanced': '400px',
  'hbc-anomaly-atlas': '600px',
};

export function GrafanaDashboardEmbed({
  dashboardUid,
  title,
  regionId,
  height,
  refreshInterval,
  panelId,
}: GrafanaDashboardEmbedProps) {
  const grafanaBase = process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3001';
  // Grafana uses var-<variable_name> format for dashboard variables.
  // Most dashboards use 'region'; regional-comparison and regional-variance-explorer use 'regions' (multi).
  // Pass both so both variable names are populated when the user selects a region.
  const regionParam = regionId
    ? `&var-region=${encodeURIComponent(regionId)}&var-regions=${encodeURIComponent(regionId)}`
    : '';
  const panelParam = panelId ? `&panelId=${panelId}` : '';
  const refresh = refreshInterval || (dashboardUid.includes('live') || dashboardUid.includes('realtime') ? '30s' : '5m');

  const src = `${grafanaBase}/d/${dashboardUid}?orgId=1&theme=light&kiosk=tv&refresh=${refresh}${regionParam}${panelParam}`;

  // Debug logging (only in development)
  if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
    console.log(`[GrafanaDashboardEmbed] Loading dashboard: ${dashboardUid}`, {
      regionId,
      src: src.replace(/http:\/\/[^/]+/, grafanaBase),
    });
  }

  const customHeight = height || DEFAULT_HEIGHTS[dashboardUid] || '500px';
  const iframeHeight = typeof customHeight === 'number' ? `${customHeight}px` : customHeight;

  const [embedError, setEmbedError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fallback timeout: show iframe after 3 seconds even if onLoad hasn't fired
  // This ensures dashboards are visible even if load detection fails
  useEffect(() => {
    const timeout = setTimeout(() => {
      setIsLoading(false);
    }, 3000);
    return () => clearTimeout(timeout);
  }, []);

  return (
    <div
      style={{
        backgroundColor: '#fff',
        borderRadius: '6px',
        padding: '8px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        marginBottom: '4px',
        minHeight: iframeHeight,
        position: 'relative',
      }}
      data-testid={`dashboard-embed-${dashboardUid}`}
    >
      <h2 style={{ margin: '0 0 4px 0', fontSize: '14px', fontWeight: '600', color: '#333' }}>
        {title}
      </h2>
      {embedError && (
        <div
          style={{
            padding: '12px',
            backgroundColor: '#f8d7da',
            color: '#721c24',
            borderRadius: '4px',
            marginBottom: '8px',
            fontSize: '12px',
          }}
        >
          <strong>Grafana embed error:</strong> {embedError}
          <br />
          <small>URL: {src.replace(/http:\/\/[^/]+/, 'http://localhost:3001')}</small>
        </div>
      )}
      {isLoading && (
        <div
          style={{
            padding: '20px',
            textAlign: 'center',
            color: '#666',
            fontSize: '14px',
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            borderRadius: '4px',
            zIndex: 10,
            pointerEvents: 'none',
          }}
        >
          Loading dashboard...
        </div>
      )}
      <iframe
        key={`${dashboardUid}-${regionId || 'no-region'}-${panelId || 'no-panel'}`}
        src={src}
        style={{
          width: '100%',
          height: iframeHeight,
          border: 'none',
          borderRadius: '8px',
          display: 'block',
          opacity: isLoading ? 0.3 : 1,
          transition: 'opacity 0.3s ease-in-out',
          minHeight: '200px',
        }}
        title={title}
        allow="fullscreen"
        sandbox="allow-scripts allow-same-origin"
        onLoad={(e) => {
          setIsLoading(false);
          try {
            const iframe = e.target as HTMLIFrameElement;
            // Check if Grafana redirected to login page
            if (iframe.contentWindow?.location.href.includes('/login')) {
              setEmbedError('Grafana requires authentication. Check GF_AUTH_ANONYMOUS_ENABLED setting.');
            } else {
              setEmbedError(null);
              // Debug log successful load
              if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
                console.log(`[GrafanaDashboardEmbed] Successfully loaded: ${dashboardUid}`);
              }
            }
          } catch (err) {
            // Cross-origin restrictions may prevent checking href, but iframe loaded
            setEmbedError(null);
            if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
              console.log(`[GrafanaDashboardEmbed] Loaded (cross-origin check blocked): ${dashboardUid}`);
            }
          }
        }}
        onError={() => {
          setIsLoading(false);
          const errorMsg = `Failed to load Grafana dashboard: ${dashboardUid}. Check: 1) Grafana is running at ${grafanaBase}, 2) GF_SECURITY_ALLOW_EMBEDDING=true, 3) Network connectivity.`;
          setEmbedError(errorMsg);
          if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
            console.error(`[GrafanaDashboardEmbed] Error loading ${dashboardUid}:`, errorMsg);
          }
        }}
      />
    </div>
  );
}
