'use client';

import { useEffect, useState } from 'react';

interface BehaviorIndexFuelGaugeProps {
  region?: string | null;
}

interface GaugeData {
  value: number;
  trend: 'up' | 'down' | 'stable';
  velocity: number;
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
  gaugeContainer: {
    position: 'relative' as const,
    width: '300px',
    height: '300px',
  },
  svg: {
    width: '100%',
    height: '100%',
  },
  valueText: {
    fontSize: '48px',
    fontWeight: 'bold',
    fill: '#ffffff',
    textAnchor: 'middle' as const,
  },
  labelText: {
    fontSize: '16px',
    fill: '#a0a0a0',
    textAnchor: 'middle' as const,
  },
  trendArrow: {
    fontSize: '24px',
    fill: '#00ff88',
    textAnchor: 'middle' as const,
  },
};

export function BehaviorIndexFuelGauge({ region }: BehaviorIndexFuelGaugeProps) {
  const [data, setData] = useState<GaugeData>({ value: 0.45, trend: 'stable', velocity: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const regionParam = region ? `?region=${encodeURIComponent(region)}` : '';
        const response = await fetch(`http://localhost:8100/api/metrics${regionParam}`);
        const metrics = await response.json();
        
        const currentValue = metrics.behavior_index?.current || 0.45;
        const previousValue = metrics.behavior_index?.previous || currentValue;
        const velocity = currentValue - previousValue;
        const trend = velocity > 0.01 ? 'up' : velocity < -0.01 ? 'down' : 'stable';
        
        setData({ value: currentValue, trend, velocity });
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch behavior index:', error);
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, [region]);

  if (loading) {
    return <div style={{ color: '#ffffff' }}>Loading...</div>;
  }

  const percentage = Math.round(data.value * 100);
  const angle = (data.value * 180) - 90; // -90 to 90 degrees
  const radius = 120;
  const centerX = 150;
  const centerY = 150;

  // Color based on value
  const getColor = (value: number) => {
    if (value < 0.3) return '#00ff88'; // Green
    if (value < 0.5) return '#ffd700'; // Yellow
    if (value < 0.7) return '#ff8800'; // Orange
    return '#ff4444'; // Red
  };

  const color = getColor(data.value);

  // Calculate gauge arc
  const startAngle = -90;
  const endAngle = angle;
  const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;
  
  const x1 = centerX + radius * Math.cos((startAngle * Math.PI) / 180);
  const y1 = centerY + radius * Math.sin((startAngle * Math.PI) / 180);
  const x2 = centerX + radius * Math.cos((endAngle * Math.PI) / 180);
  const y2 = centerY + radius * Math.sin((endAngle * Math.PI) / 180);

  const pathData = `M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;

  // Trend arrow
  const arrowSymbol = data.trend === 'up' ? '↑' : data.trend === 'down' ? '↓' : '→';
  const arrowColor = data.trend === 'up' ? '#ff4444' : data.trend === 'down' ? '#00ff88' : '#ffd700';

  return (
    <div style={styles.container}>
      <div style={styles.gaugeContainer}>
        <svg style={styles.svg} viewBox="0 0 300 300">
          {/* Background arc */}
          <path
            d={`M ${centerX} ${centerY} L ${centerX} ${centerY - radius} A ${radius} ${radius} 0 0 1 ${centerX + radius} ${centerY}`}
            fill="rgba(255, 255, 255, 0.1)"
            stroke="rgba(255, 255, 255, 0.2)"
            strokeWidth="2"
          />
          
          {/* Value arc */}
          <path
            d={pathData}
            fill={color}
            opacity="0.8"
          />
          
          {/* Needle */}
          <line
            x1={centerX}
            y1={centerY}
            x2={x2}
            y2={y2}
            stroke="#ffffff"
            strokeWidth="3"
            strokeLinecap="round"
          />
          
          {/* Center dot */}
          <circle cx={centerX} cy={centerY} r="8" fill="#ffffff" />
          
          {/* Value text */}
          <text x={centerX} y={centerY + 20} style={styles.valueText}>
            {percentage}%
          </text>
          
          {/* Trend arrow */}
          <text x={centerX} y={centerY + 50} style={{ ...styles.trendArrow, fill: arrowColor }}>
            {arrowSymbol}
          </text>
          
          {/* Velocity text */}
          <text x={centerX} y={centerY + 70} style={styles.labelText}>
            {data.velocity > 0 ? '+' : ''}{(data.velocity * 100).toFixed(1)}% velocity
          </text>
        </svg>
      </div>
    </div>
  );
}
