'use client';

import { useState } from 'react';

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
  const regionParam = regionId ? `&var-region=${encodeURIComponent(regionId)}` : '';
  const panelParam = panelId ? `&panelId=${panelId}` : '';
  const refresh = refreshInterval || (dashboardUid.includes('live') || dashboardUid.includes('realtime') ? '30s' : '5m');
  
  const src = `${grafanaBase}/d/${dashboardUid}?orgId=1&theme=light&kiosk=tv&refresh=${refresh}${regionParam}${panelParam}`;
  
  const customHeight = height || DEFAULT_HEIGHTS[dashboardUid] || '500px';
  const iframeHeight = typeof customHeight === 'number' ? `${customHeight}px` : customHeight;

  const [embedError, setEmbedError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  return (
    <div
      style={{
        backgroundColor: '#fff',
        borderRadius: '6px',
        padding: '8px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        marginBottom: '4px',
        minHeight: iframeHeight,
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
          display: isLoading ? 'none' : 'block',
        }}
        title={title}
        allow="fullscreen"
        sandbox="allow-scripts allow-same-origin"
        onLoad={(e) => {
          setIsLoading(false);
          try {
            const iframe = e.target as HTMLIFrameElement;
            if (iframe.contentWindow?.location.href.includes('/login')) {
              setEmbedError('Grafana requires authentication. Check GF_AUTH_ANONYMOUS_ENABLED setting.');
            } else {
              setEmbedError(null);
            }
          } catch (err) {
            setEmbedError(null);
          }
        }}
        onError={() => {
          setIsLoading(false);
          setEmbedError('Failed to load Grafana dashboard. Check GF_SECURITY_ALLOW_EMBEDDING and network connectivity.');
        }}
      />
    </div>
  );
}
