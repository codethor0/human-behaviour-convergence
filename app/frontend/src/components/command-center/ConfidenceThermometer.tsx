'use client';

import { useEffect, useState } from 'react';

interface QualityData {
  overall: number;
  sources: {
    name: string;
    quality: number;
    freshness: number;
  }[];
}

const styles = {
  container: {
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
  },
  thermometer: {
    width: '60px',
    height: '200px',
    position: 'relative' as const,
    marginBottom: '20px',
  },
  thermometerBody: {
    width: '40px',
    height: '180px',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '20px',
    position: 'absolute' as const,
    left: '10px',
    top: '10px',
    overflow: 'hidden' as const,
  },
  thermometerFill: {
    width: '100%',
    position: 'absolute' as const,
    bottom: 0,
    transition: 'height 0.5s',
  },
  thermometerBulb: {
    width: '60px',
    height: '60px',
    borderRadius: '50%',
    position: 'absolute' as const,
    bottom: 0,
    left: 0,
  },
  label: {
    fontSize: '14px',
    color: '#ffffff',
    marginTop: '10px',
  },
  sourcesList: {
    width: '100%',
    maxHeight: '150px',
    overflowY: 'auto' as const,
    marginTop: '20px',
  },
  sourceItem: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '4px 0',
    fontSize: '11px',
    color: '#a0a0a0',
  },
};

export function ConfidenceThermometer() {
  const [data, setData] = useState<QualityData>({
    overall: 0.85,
    sources: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchQuality = async () => {
      try {
        // Query data source status metrics
        const response = await fetch('http://localhost:8100/api/sources/status');
        const status = await response.json();
        
        // Calculate quality scores
        const sources = Object.entries(status.sources || {}).map(([name, status]: [string, any]) => ({
          name,
          quality: status.active ? 0.9 : 0.1,
          freshness: status.freshness || 0.5,
        }));
        
        const overall = sources.length > 0
          ? sources.reduce((sum, s) => sum + s.quality, 0) / sources.length
          : 0.5;
        
        setData({ overall, sources });
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch quality data:', error);
        setLoading(false);
      }
    };

    fetchQuality();
    const interval = setInterval(fetchQuality, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div style={{ color: '#ffffff' }}>Loading...</div>;
  }

  const fillHeight = data.overall * 180;
  const getColor = (value: number) => {
    if (value > 0.8) return '#00ff88';
    if (value > 0.6) return '#ffd700';
    if (value > 0.4) return '#ff8800';
    return '#ff4444';
  };

  const color = getColor(data.overall);

  return (
    <div style={styles.container}>
      <div style={styles.thermometer}>
        <div style={styles.thermometerBody}>
          <div
            style={{
              ...styles.thermometerFill,
              height: `${fillHeight}px`,
              backgroundColor: color,
            }}
          />
        </div>
        <div
          style={{
            ...styles.thermometerBulb,
            backgroundColor: color,
          }}
        />
      </div>
      <div style={styles.label}>
        {Math.round(data.overall * 100)}% Quality
      </div>
      {data.sources.length > 0 && (
        <div style={styles.sourcesList}>
          {data.sources.slice(0, 5).map((source) => (
            <div key={source.name} style={styles.sourceItem}>
              <span>{source.name}</span>
              <span>{Math.round(source.quality * 100)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
