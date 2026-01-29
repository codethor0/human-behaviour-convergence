'use client';

import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';

interface Anomaly {
  timestamp: string;
  value: number;
  expected: number;
  zScore: number;
  region: string;
  investigation: string[];
}

interface AnomalyDetectionTheaterProps {
  region?: string | null;
  width?: number;
  height?: number;
}

export function AnomalyDetectionTheater({ region, width: _width = 1000, height: _height = 600 }: AnomalyDetectionTheaterProps) {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [history, setHistory] = useState<Array<{ timestamp: string; value: number }>>([]);
  const [selectedAnomaly, setSelectedAnomaly] = useState<Anomaly | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(
          `http://localhost:8100/api/forecast?region_id=${region || 'city_nyc'}&days_back=90&forecast_horizon=7`
        );
        const data = await response.json();

        const hist = (data.history || []).map((h: any) => ({
          timestamp: h.timestamp,
          value: h.behavior_index || 0.5,
        }));

        setHistory(hist);

        // Detect anomalies using Z-score
        if (hist.length > 30) {
          const values = hist.map((h: { timestamp: string; value: number }) => h.value);
          const mean = values.reduce((a: number, b: number) => a + b, 0) / values.length;
          const _std = Math.sqrt(
            values.reduce((sum: number, v: number) => sum + Math.pow(v - mean, 2), 0) / values.length
          );

          const detected: Anomaly[] = [];
          hist.forEach((h: { timestamp: string; value: number }, idx: number) => {
            if (idx < 30) return; // Need history for rolling average

            const recent = values.slice(Math.max(0, idx - 30), idx);
            const recentMean = recent.reduce((a: number, b: number) => a + b, 0) / recent.length;
            const recentStd = Math.sqrt(
              recent.reduce((sum: number, v: number) => sum + Math.pow(v - recentMean, 2), 0) / recent.length
            );

            const zScore = recentStd > 0 ? Math.abs((h.value - recentMean) / recentStd) : 0;

            if (zScore > 2.0) {
              const investigation: string[] = [];

              // Generate investigation threads
              if (h.value > recentMean + 2 * recentStd) {
                investigation.push('Spike detected: Check recent shock events');
                investigation.push('Verify data source freshness');
                investigation.push('Compare with regional neighbors');
              } else if (h.value < recentMean - 2 * recentStd) {
                investigation.push('Drop detected: Check for data pipeline issues');
                investigation.push('Verify sub-index contributions');
                investigation.push('Review historical patterns');
              }

              detected.push({
                timestamp: h.timestamp,
                value: h.value,
                expected: recentMean,
                zScore,
                region: region || 'unknown',
                investigation,
              });
            }
          });

          setAnomalies(detected);
        }

        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch anomaly data:', error);
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [region]);

  if (loading) {
    return <div style={{ color: '#ffffff', textAlign: 'center', padding: '40px' }}>Loading anomaly detection...</div>;
  }

  const dates = history.map(h => h.timestamp);
  const values = history.map(h => h.value);

  // Calculate rolling average and std for bands
  const rollingAvg: number[] = [];
  const rollingUpper: number[] = [];
  const rollingLower: number[] = [];

  history.forEach((h, idx) => {
    if (idx < 30) {
      rollingAvg.push(h.value);
      rollingUpper.push(h.value);
      rollingLower.push(h.value);
    } else {
      const recent = values.slice(idx - 30, idx);
      const avg = recent.reduce((a, b) => a + b, 0) / recent.length;
      const std = Math.sqrt(
        recent.reduce((sum, v) => sum + Math.pow(v - avg, 2), 0) / recent.length
      );
      rollingAvg.push(avg);
      rollingUpper.push(avg + 2 * std);
      rollingLower.push(avg - 2 * std);
    }
  });

  const option = {
    backgroundColor: 'transparent',
    grid: {
      left: '10%',
      right: '10%',
      top: '15%',
      bottom: '15%',
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#666' } },
      axisLabel: { color: '#aaa', rotate: 45 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      axisLine: { lineStyle: { color: '#666' } },
      axisLabel: { color: '#aaa' },
      splitLine: { lineStyle: { color: '#333' } },
    },
    series: [
      // Confidence bands
      {
        name: 'Normal Range',
        type: 'line',
        data: rollingUpper,
        lineStyle: { opacity: 0 },
        areaStyle: {
          color: 'rgba(0, 255, 136, 0.1)',
        },
        stack: 'confidence',
        silent: true,
      },
      {
        name: 'Lower Bound',
        type: 'line',
        data: rollingLower,
        lineStyle: { opacity: 0 },
        areaStyle: {
          color: 'rgba(0, 0, 0, 0.3)',
        },
        stack: 'confidence',
        silent: true,
      },
      // Main line
      {
        name: 'Behavior Index',
        type: 'line',
        data: values,
        lineStyle: {
          color: '#00ff88',
          width: 2,
        },
        itemStyle: {
          color: '#00ff88',
        },
      },
      // Rolling average
      {
        name: 'Rolling Average',
        type: 'line',
        data: rollingAvg,
        lineStyle: {
          color: '#ffd700',
          width: 1,
          type: 'dashed',
        },
        itemStyle: {
          color: '#ffd700',
        },
      },
      // Anomaly markers with spotlight effect
      ...anomalies.map((anomaly, _idx) => {
        const dateIdx = dates.indexOf(anomaly.timestamp);
        return {
          type: 'scatter',
          data: [[dates[dateIdx], anomaly.value]],
          symbolSize: 30 + anomaly.zScore * 10,
          itemStyle: {
            color: anomaly.zScore > 3 ? '#ff0000' : '#ff8800',
            shadowBlur: 20,
            shadowColor: anomaly.zScore > 3 ? '#ff0000' : '#ff8800',
            borderColor: '#ffffff',
            borderWidth: 2,
          },
          label: {
            show: true,
            formatter: `[WARN] ${anomaly.zScore.toFixed(1)}σ`,
            fontSize: 12,
            color: '#ffffff',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            padding: [4, 8],
            borderRadius: 4,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 40,
            },
          },
        };
      }),
    ],
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: '#00ff88',
      textStyle: { color: '#ffffff' },
      formatter: (params: any) => {
        const point = params[0];
        const anomaly = anomalies.find(a => a.timestamp === point.axisValue);

        if (anomaly) {
          return `
            <div>
              <strong style="color: #ff4444">[WARN] ANOMALY DETECTED</strong><br/>
              <strong>${point.axisValue}</strong><br/>
              Value: ${(anomaly.value * 100).toFixed(1)}%<br/>
              Expected: ${(anomaly.expected * 100).toFixed(1)}%<br/>
              Z-Score: ${anomaly.zScore.toFixed(2)}σ<br/>
              <br/>
              <strong>Investigation Threads:</strong><br/>
              ${anomaly.investigation.map(i => `• ${i}`).join('<br/>')}
            </div>
          `;
        }

        return `
          <div>
            <strong>${point.axisValue}</strong><br/>
            Value: ${(point.value * 100).toFixed(1)}%
          </div>
        `;
      },
    },
    legend: {
      data: ['Behavior Index', 'Rolling Average', 'Normal Range'],
      textStyle: { color: '#aaa' },
      top: '5%',
    },
  };

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '10px', color: '#ffffff', fontSize: '14px' }}>
        <strong>Anomaly Detection Theater</strong>
        <div style={{ fontSize: '11px', color: '#888', marginTop: '5px' }}>
          Spotlight effects highlight statistical outliers | Click anomalies to see investigation threads |
          Z-Score &gt; 2.0 = Moderate, &gt; 3.0 = Critical
        </div>
      </div>
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <ReactECharts
          option={option}
          style={{ flex: 1, minHeight: 0 }}
          opts={{ renderer: 'svg' }}
        />
        {selectedAnomaly && (
          <div style={{
            width: '300px',
            padding: '15px',
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            borderLeft: '2px solid #ff4444',
            color: '#ffffff',
            overflowY: 'auto',
          }}>
            <h3 style={{ color: '#ff4444', marginTop: 0 }}>Investigation Report</h3>
            <div style={{ marginBottom: '10px' }}>
              <strong>Timestamp:</strong> {selectedAnomaly.timestamp}<br/>
              <strong>Value:</strong> {(selectedAnomaly.value * 100).toFixed(1)}%<br/>
              <strong>Expected:</strong> {(selectedAnomaly.expected * 100).toFixed(1)}%<br/>
              <strong>Z-Score:</strong> {selectedAnomaly.zScore.toFixed(2)}σ
            </div>
            <div>
              <strong>Investigation Threads:</strong>
              <ul style={{ paddingLeft: '20px' }}>
                {selectedAnomaly.investigation.map((thread, idx) => (
                  <li key={idx} style={{ marginBottom: '5px' }}>{thread}</li>
                ))}
              </ul>
            </div>
            <button
              onClick={() => setSelectedAnomaly(null)}
              style={{
                marginTop: '10px',
                padding: '6px 12px',
                backgroundColor: '#666',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Close
            </button>
          </div>
        )}
      </div>
      {anomalies.length > 0 && (
        <div style={{
          padding: '10px',
          backgroundColor: 'rgba(255, 68, 68, 0.2)',
          borderTop: '1px solid #ff4444',
          color: '#ffffff',
          fontSize: '12px',
        }}>
          <strong>Active Anomalies:</strong> {anomalies.length} detected |
          Critical: {anomalies.filter(a => a.zScore > 3).length} |
          Moderate: {anomalies.filter(a => a.zScore > 2 && a.zScore <= 3).length}
        </div>
      )}
    </div>
  );
}
