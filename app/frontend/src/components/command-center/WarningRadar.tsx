'use client';

import { useEffect, useState } from 'react';

interface Risk {
  horizon: '24h' | '48h' | '72h';
  level: 'low' | 'moderate' | 'high' | 'critical';
  description: string;
}

const styles = {
  container: {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative' as const,
  },
  radar: {
    position: 'relative' as const,
    width: '300px',
    height: '300px',
  },
  svg: {
    width: '100%',
    height: '100%',
  },
  circle: {
    fill: 'none',
    stroke: 'rgba(255, 255, 255, 0.2)',
    strokeWidth: '2',
  },
  riskDot: {
    r: '8',
    transition: 'all 0.3s',
  },
  riskPulse: {
    animation: 'pulse 2s infinite',
  },
  label: {
    fontSize: '12px',
    fill: '#ffffff',
    textAnchor: 'middle' as const,
  },
};

export function WarningRadar({ region }: { region?: string | null }) {
  const [risks, setRisks] = useState<Risk[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRisks = async () => {
      try {
        // Query forecast metrics for risk assessment
        // This would integrate with actual forecast service
        const mockRisks: Risk[] = [
          { horizon: '24h', level: 'moderate', description: 'Economic stress trending up' },
          { horizon: '48h', level: 'high', description: 'Environmental factors converging' },
          { horizon: '72h', level: 'low', description: 'Stable conditions expected' },
        ];
        
        setRisks(mockRisks);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch risks:', error);
        setLoading(false);
      }
    };

    fetchRisks();
    const interval = setInterval(fetchRisks, 60000); // Update every minute
    return () => clearInterval(interval);
  }, [region]);

  if (loading) {
    return <div style={{ color: '#ffffff' }}>Loading radar...</div>;
  }

  const centerX = 150;
  const centerY = 150;
  const radius24h = 60;
  const radius48h = 100;
  const radius72h = 140;

  const getRiskColor = (level: Risk['level']) => {
    switch (level) {
      case 'critical': return '#ff4444';
      case 'high': return '#ff8800';
      case 'moderate': return '#ffd700';
      default: return '#00ff88';
    }
  };

  const getRiskPosition = (horizon: Risk['horizon']) => {
    const angle = Math.random() * Math.PI * 2; // Random angle for demo
    let radius = radius24h;
    if (horizon === '48h') radius = radius48h;
    if (horizon === '72h') radius = radius72h;
    
    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  };

  return (
    <div style={styles.container}>
      <div style={styles.radar}>
        <svg style={styles.svg} viewBox="0 0 300 300">
          {/* Concentric circles */}
          <circle cx={centerX} cy={centerY} r={radius24h} style={styles.circle} />
          <circle cx={centerX} cy={centerY} r={radius48h} style={styles.circle} />
          <circle cx={centerX} cy={centerY} r={radius72h} style={styles.circle} />
          
          {/* Labels */}
          <text x={centerX} y={centerY - radius24h - 10} style={styles.label}>24h</text>
          <text x={centerX} y={centerY - radius48h - 10} style={styles.label}>48h</text>
          <text x={centerX} y={centerY - radius72h - 10} style={styles.label}>72h</text>
          
          {/* Risk dots */}
          {risks.map((risk, index) => {
            const pos = getRiskPosition(risk.horizon);
            const color = getRiskColor(risk.level);
            const isCritical = risk.level === 'critical' || risk.level === 'high';
            
            return (
              <g key={index}>
                {/* Pulse effect for critical risks */}
                {isCritical && (
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r="12"
                    fill={color}
                    opacity="0.3"
                    style={styles.riskPulse}
                  />
                )}
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r="8"
                  fill={color}
                  style={styles.riskDot}
                />
              </g>
            );
          })}
          
          {/* Center point */}
          <circle cx={centerX} cy={centerY} r="4" fill="#ffffff" />
        </svg>
      </div>
    </div>
  );
}
