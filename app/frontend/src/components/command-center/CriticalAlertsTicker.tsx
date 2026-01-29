'use client';

import { useEffect, useState } from 'react';

interface Alert {
  id: string;
  severity: 'critical' | 'high' | 'moderate';
  message: string;
  region: string;
  timestamp: string;
}

const styles = {
  container: {
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  ticker: {
    flex: 1,
    overflow: 'hidden',
    position: 'relative' as const,
  },
  tickerContent: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
    animation: 'scroll 30s linear infinite',
  },
  alertItem: {
    padding: '12px 16px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  severityCritical: {
    backgroundColor: 'rgba(255, 68, 68, 0.2)',
    borderLeft: '4px solid #ff4444',
  },
  severityHigh: {
    backgroundColor: 'rgba(255, 136, 0, 0.2)',
    borderLeft: '4px solid #ff8800',
  },
  severityModerate: {
    backgroundColor: 'rgba(255, 215, 0, 0.2)',
    borderLeft: '4px solid #ffd700',
  },
  alertText: {
    flex: 1,
    fontSize: '14px',
    color: '#ffffff',
  },
  alertRegion: {
    fontSize: '12px',
    color: '#a0a0a0',
    fontWeight: '600',
  },
  alertTime: {
    fontSize: '11px',
    color: '#666666',
  },
  emptyState: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#666666',
    fontSize: '14px',
  },
};

export function CriticalAlertsTicker() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        // Query Prometheus for anomalies (z-score > 2.0)
        // For now, use mock data structure
        const response = await fetch('http://localhost:8100/api/metrics');
        const _metrics = await response.json();
        
        // Generate alerts from anomaly detection metrics
        // This would integrate with actual anomaly detection service
        const mockAlerts: Alert[] = [
          {
            id: '1',
            severity: 'critical',
            message: 'Behavior Index spike detected in NYC',
            region: 'city_nyc',
            timestamp: new Date().toISOString(),
          },
          {
            id: '2',
            severity: 'high',
            message: 'Environmental stress elevated in California',
            region: 'us_ca',
            timestamp: new Date(Date.now() - 3600000).toISOString(),
          },
          {
            id: '3',
            severity: 'moderate',
            message: 'Mobility activity anomaly in Illinois',
            region: 'us_il',
            timestamp: new Date(Date.now() - 7200000).toISOString(),
          },
        ];
        
        setAlerts(mockAlerts.slice(0, 5)); // Top 5
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch alerts:', error);
        setLoading(false);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div style={styles.emptyState}>Loading alerts...</div>;
  }

  if (alerts.length === 0) {
    return <div style={styles.emptyState}>No active alerts</div>;
  }

  const getSeverityStyle = (severity: Alert['severity']) => {
    switch (severity) {
      case 'critical':
        return styles.severityCritical;
      case 'high':
        return styles.severityHigh;
      default:
        return styles.severityModerate;
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  return (
    <div style={styles.container}>
      <div style={styles.ticker}>
        <div style={styles.tickerContent}>
          {alerts.map((alert) => (
            <div
              key={alert.id}
              style={{
                ...styles.alertItem,
                ...getSeverityStyle(alert.severity),
              }}
              onClick={() => {
                // Navigate to alert details or regional dashboard
                window.location.href = `/regional-deep-dive?region=${alert.region}`;
              }}
            >
              <div style={styles.alertText}>{alert.message}</div>
              <div style={styles.alertRegion}>{alert.region}</div>
              <div style={styles.alertTime}>{formatTime(alert.timestamp)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
