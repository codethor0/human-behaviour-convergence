'use client';

import { useEffect, useState } from 'react';

interface Region {
  id: string;
  name: string;
  behaviorIndex: number;
}

const styles = {
  container: {
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column' as const,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
    gap: '12px',
    flex: 1,
    overflowY: 'auto' as const,
  },
  regionCard: {
    padding: '16px',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s',
    textAlign: 'center' as const,
    border: '2px solid transparent',
  },
  regionCardHover: {
    transform: 'scale(1.05)',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
  },
  regionName: {
    fontSize: '12px',
    fontWeight: '600',
    marginBottom: '8px',
    color: '#ffffff',
  },
  regionValue: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#ffffff',
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#666666',
  },
};

export function RegionalComparisonMatrix({ onRegionSelect }: { onRegionSelect: (_region: string | null) => void }) {
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true);
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null);

  useEffect(() => {
    const fetchRegions = async () => {
      try {
        // Query Prometheus for all regions with behavior_index
        const response = await fetch('http://localhost:8100/api/metrics');
        const _metrics = await response.json();
        
        // Extract regions from metrics
        // This would come from actual Prometheus query: label_values(behavior_index, region)
        const mockRegions: Region[] = [
          { id: 'city_nyc', name: 'NYC', behaviorIndex: 0.52 },
          { id: 'us_ny', name: 'New York', behaviorIndex: 0.48 },
          { id: 'us_ca', name: 'California', behaviorIndex: 0.61 },
          { id: 'us_il', name: 'Illinois', behaviorIndex: 0.45 },
          { id: 'us_tx', name: 'Texas', behaviorIndex: 0.55 },
          { id: 'us_fl', name: 'Florida', behaviorIndex: 0.49 },
        ];
        
        setRegions(mockRegions);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch regions:', error);
        setLoading(false);
      }
    };

    fetchRegions();
    const interval = setInterval(fetchRegions, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div style={styles.loading}>Loading regions...</div>;
  }

  const getColor = (value: number) => {
    if (value < 0.3) return { bg: 'rgba(0, 255, 136, 0.3)', border: '#00ff88' };
    if (value < 0.5) return { bg: 'rgba(255, 215, 0, 0.3)', border: '#ffd700' };
    if (value < 0.7) return { bg: 'rgba(255, 136, 0, 0.3)', border: '#ff8800' };
    return { bg: 'rgba(255, 68, 68, 0.3)', border: '#ff4444' };
  };

  return (
    <div style={styles.container}>
      <div style={styles.grid}>
        {regions.map((region) => {
          const colors = getColor(region.behaviorIndex);
          const isHovered = hoveredRegion === region.id;
          
          return (
            <div
              key={region.id}
              style={{
                ...styles.regionCard,
                backgroundColor: colors.bg,
                borderColor: colors.border,
                ...(isHovered ? styles.regionCardHover : {}),
              }}
              onMouseEnter={() => setHoveredRegion(region.id)}
              onMouseLeave={() => setHoveredRegion(null)}
              onClick={() => {
                onRegionSelect(region.id);
                // Could also navigate to regional dashboard
              }}
            >
              <div style={styles.regionName}>{region.name}</div>
              <div style={styles.regionValue}>
                {Math.round(region.behaviorIndex * 100)}%
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
