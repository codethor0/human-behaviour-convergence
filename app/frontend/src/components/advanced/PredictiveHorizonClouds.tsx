'use client';

import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';

interface ForecastPoint {
  date: string;
  value: number;
  lower: number;
  upper: number;
  confidence: number;
}

interface PredictiveHorizonCloudsProps {
  region?: string | null;
  width?: number;
  height?: number;
}

export function PredictiveHorizonClouds({ region, width: _width = 1000, height: _height = 500 }: PredictiveHorizonCloudsProps) {
  const [history, setHistory] = useState<ForecastPoint[]>([]);
  const [forecast, setForecast] = useState<ForecastPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [assumptionMultiplier, setAssumptionMultiplier] = useState(1.0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(
          `http://localhost:8100/api/forecast?region_id=${region || 'city_nyc'}&days_back=30&forecast_horizon=7`
        );
        const data = await response.json();
        
        const hist = (data.history || []).map((h: any) => ({
          date: h.timestamp,
          value: h.behavior_index,
          lower: h.behavior_index * 0.95,
          upper: h.behavior_index * 1.05,
          confidence: 0.9,
        }));
        
        const fcst = (data.forecast || []).map((f: any, idx: number) => {
          const baseValue = f.behavior_index * assumptionMultiplier;
          const confidence = 0.9 - (idx / (data.forecast.length || 1)) * 0.3;
          const range = baseValue * (1 - confidence);
          return {
            date: f.timestamp,
            value: baseValue,
            lower: baseValue - range,
            upper: baseValue + range,
            confidence,
          };
        });
        
        setHistory(hist);
        setForecast(fcst);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch forecast data:', error);
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [region, assumptionMultiplier]);

  if (loading) {
    return <div style={{ color: '#ffffff', textAlign: 'center', padding: '40px' }}>Loading probability clouds...</div>;
  }

  const allData = [...history, ...forecast];
  const dates = allData.map(d => d.date);
  const values = allData.map(d => d.value);
  const lowers = allData.map(d => d.lower);
  const uppers = allData.map(d => d.upper);
  const _confidences = allData.map(d => d.confidence);

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
      // Confidence bands (gradient opacity)
      {
        name: 'Confidence Band',
        type: 'line',
        data: uppers,
        lineStyle: { opacity: 0 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: allData.map((d, idx) => ({
              offset: idx / (allData.length - 1),
              color: `rgba(0, 255, 136, ${d.confidence * 0.3})`,
            })),
          },
        },
        stack: 'confidence',
        silent: true,
      },
      {
        name: 'Lower Bound',
        type: 'line',
        data: lowers,
        lineStyle: { opacity: 0 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: allData.map((d, idx) => ({
              offset: idx / (allData.length - 1),
              color: `rgba(0, 255, 136, ${d.confidence * 0.3})`,
            })),
          },
        },
        stack: 'confidence',
        silent: true,
      },
      // Main forecast line
      {
        name: 'Behavior Index',
        type: 'line',
        data: values,
        lineStyle: {
          color: '#00ff88',
          width: 3,
        },
        itemStyle: {
          color: '#00ff88',
        },
        markLine: {
          data: [
            {
              xAxis: dates[history.length - 1],
              lineStyle: { color: '#ff8800', type: 'dashed', width: 2 },
              label: { formatter: 'Forecast Start', color: '#ff8800' },
            },
          ],
        },
        markArea: {
          itemStyle: {
            color: 'rgba(255, 136, 0, 0.1)',
          },
          data: [
            [
              { xAxis: dates[history.length - 1] },
              { xAxis: dates[dates.length - 1] },
            ],
          ],
        },
      },
      // Warning fronts (high values)
      ...values.map((val, idx) => {
        if (val > 0.7 && idx >= history.length) {
          return {
            type: 'scatter',
            data: [[dates[idx], val]],
            symbolSize: 20,
            itemStyle: {
              color: '#ff4444',
              shadowBlur: 10,
              shadowColor: '#ff4444',
            },
            label: {
              show: true,
              formatter: '[WARN]',
              fontSize: 16,
              color: '#ff4444',
            },
          };
        }
        return null;
      }).filter(Boolean),
    ],
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: '#00ff88',
      textStyle: { color: '#ffffff' },
      formatter: (params: any) => {
        const point = params[0];
        const idx = dates.indexOf(point.axisValue);
        const dataPoint = allData[idx];
        return `
          <div>
            <strong>${point.axisValue}</strong><br/>
            Value: ${(dataPoint.value * 100).toFixed(1)}%<br/>
            Range: ${(dataPoint.lower * 100).toFixed(1)}% - ${(dataPoint.upper * 100).toFixed(1)}%<br/>
            Confidence: ${(dataPoint.confidence * 100).toFixed(0)}%
          </div>
        `;
      },
    },
    legend: {
      data: ['Behavior Index', 'Confidence Band'],
      textStyle: { color: '#aaa' },
      top: '5%',
    },
  };

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '10px', color: '#ffffff', fontSize: '14px' }}>
        <strong>Predictive Horizon Clouds</strong>
        <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label style={{ fontSize: '12px' }}>Assumption Multiplier:</label>
          <input
            type="range"
            min="0.5"
            max="1.5"
            step="0.1"
            value={assumptionMultiplier}
            onChange={(e) => setAssumptionMultiplier(parseFloat(e.target.value))}
            style={{ flex: 1, maxWidth: '200px' }}
          />
          <span style={{ fontSize: '12px', minWidth: '50px' }}>{assumptionMultiplier.toFixed(1)}x</span>
        </div>
        <div style={{ fontSize: '11px', color: '#888', marginTop: '5px' }}>
          Gradient opacity = Confidence | Red warnings = High risk periods | Adjust slider to see scenario shifts
        </div>
      </div>
      <ReactECharts
        option={option}
        style={{ flex: 1, minHeight: 0 }}
        opts={{ renderer: 'svg' }}
      />
    </div>
  );
}
