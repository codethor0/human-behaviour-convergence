'use client';

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface ForecastPoint {
  timestamp: Date;
  mean: number;
  lower95: number;
  upper95: number;
  lower80: number;
  upper80: number;
  confidence: number;
}

interface PredictiveHorizonCloudsProps {
  region?: string | null;
  horizon?: number; // Days ahead
  width?: number;
  height?: number;
}

export function PredictiveHorizonClouds({
  region,
  horizon = 30,
  width = 800,
  height = 400,
}: PredictiveHorizonCloudsProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [forecastData, setForecastData] = useState<ForecastPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [scenarioAdjustment, setScenarioAdjustment] = useState(1.0);

  useEffect(() => {
    const fetchForecast = async () => {
      try {
        // Fetch forecast data - would come from forecast API
        const response = await fetch(
          `http://localhost:8100/api/forecasts${region ? `?region=${region}` : ''}`
        );
        const forecasts = await response.json();

        // Generate mock forecast data with confidence intervals
        const now = new Date();
        const mockData: ForecastPoint[] = [];
        for (let i = 0; i < horizon; i++) {
          const date = new Date(now);
          date.setDate(date.getDate() + i);
          const baseValue = 0.5 + Math.sin(i / 10) * 0.1;
          const uncertainty = 0.05 + (i / horizon) * 0.1; // Uncertainty increases with horizon
          mockData.push({
            timestamp: date,
            mean: baseValue * scenarioAdjustment,
            lower95: (baseValue - uncertainty * 2) * scenarioAdjustment,
            upper95: (baseValue + uncertainty * 2) * scenarioAdjustment,
            lower80: (baseValue - uncertainty * 1.28) * scenarioAdjustment,
            upper80: (baseValue + uncertainty * 1.28) * scenarioAdjustment,
            confidence: 1 - uncertainty,
          });
        }

        setForecastData(mockData);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch forecast:', error);
        setLoading(false);
      }
    };

    fetchForecast();
    const interval = setInterval(fetchForecast, 300000); // Update every 5 minutes
    return () => clearInterval(interval);
  }, [region, horizon, scenarioAdjustment]);

  useEffect(() => {
    if (loading || !svgRef.current || forecastData.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 20, right: 20, bottom: 40, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Scales
    const xScale = d3
      .scaleTime()
      .domain(d3.extent(forecastData, (d) => d.timestamp) as [Date, Date])
      .range([0, innerWidth]);

    const yScale = d3
      .scaleLinear()
      .domain([0, 1])
      .nice()
      .range([innerHeight, 0]);

    // Create gradient definitions for confidence clouds
    const defs = svg.append('defs');

    // 95% confidence gradient
    const gradient95 = defs
      .append('linearGradient')
      .attr('id', 'gradient95')
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '0%')
      .attr('y2', '100%');
    gradient95.append('stop').attr('offset', '0%').attr('stop-color', 'rgba(255, 68, 68, 0.3)');
    gradient95.append('stop').attr('offset', '100%').attr('stop-color', 'rgba(255, 68, 68, 0.05)');

    // 80% confidence gradient
    const gradient80 = defs
      .append('linearGradient')
      .attr('id', 'gradient80')
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '0%')
      .attr('y2', '100%');
    gradient80.append('stop').attr('offset', '0%').attr('stop-color', 'rgba(255, 136, 0, 0.4)');
    gradient80.append('stop').attr('offset', '100%').attr('stop-color', 'rgba(255, 136, 0, 0.1)');

    // Area generator for confidence bands
    const area95 = d3
      .area<ForecastPoint>()
      .x((d) => xScale(d.timestamp))
      .y0((d) => yScale(d.lower95))
      .y1((d) => yScale(d.upper95))
      .curve(d3.curveMonotoneX);

    const area80 = d3
      .area<ForecastPoint>()
      .x((d) => xScale(d.timestamp))
      .y0((d) => yScale(d.lower80))
      .y1((d) => yScale(d.upper80))
      .curve(d3.curveMonotoneX);

    // Line generator for mean forecast
    const line = d3
      .line<ForecastPoint>()
      .x((d) => xScale(d.timestamp))
      .y((d) => yScale(d.mean))
      .curve(d3.curveMonotoneX);

    // Draw 95% confidence cloud
    g.append('path')
      .datum(forecastData)
      .attr('fill', 'url(#gradient95)')
      .attr('d', area95);

    // Draw 80% confidence cloud
    g.append('path')
      .datum(forecastData)
      .attr('fill', 'url(#gradient80)')
      .attr('d', area80);

    // Draw mean forecast line
    g.append('path')
      .datum(forecastData)
      .attr('fill', 'none')
      .attr('stroke', '#00ff88')
      .attr('stroke-width', 3)
      .attr('d', line);

    // Draw warning fronts (areas where forecast exceeds thresholds)
    const warningFronts = forecastData.filter((d) => d.upper95 > 0.7);
    if (warningFronts.length > 0) {
      const warningArea = d3
        .area<ForecastPoint>()
        .x((d) => xScale(d.timestamp))
        .y0((d) => yScale(0.7))
        .y1((d) => yScale(d.upper95))
        .curve(d3.curveMonotoneX);

      g.append('path')
        .datum(warningFronts)
        .attr('fill', 'rgba(255, 68, 68, 0.2)')
        .attr('stroke', '#ff4444')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '5,5')
        .attr('d', warningArea);
    }

    // Add threshold lines
    g.append('line')
      .attr('x1', 0)
      .attr('x2', innerWidth)
      .attr('y1', yScale(0.7))
      .attr('y2', yScale(0.7))
      .attr('stroke', '#ff4444')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '3,3')
      .attr('opacity', 0.5);

    g.append('line')
      .attr('x1', 0)
      .attr('x2', innerWidth)
      .attr('y1', yScale(0.5))
      .attr('y2', yScale(0.5))
      .attr('stroke', '#ffd700')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '3,3')
      .attr('opacity', 0.5);

    // Axes
    const xAxis = d3.axisBottom(xScale).ticks(6);
    const yAxis = d3.axisLeft(yScale).ticks(5);

    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxis)
      .attr('color', '#ffffff');

    g.append('g').call(yAxis).attr('color', '#ffffff');

    // Axis labels
    g.append('text')
      .attr('transform', `translate(${innerWidth / 2}, ${innerHeight + 35})`)
      .style('text-anchor', 'middle')
      .attr('fill', '#ffffff')
      .text('Forecast Horizon (days)');

    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -45)
      .attr('x', -innerHeight / 2)
      .style('text-anchor', 'middle')
      .attr('fill', '#ffffff')
      .text('Behavior Index');

    // Legend
    const legend = g.append('g').attr('transform', `translate(${innerWidth - 150}, 20)`);
    legend
      .append('rect')
      .attr('width', 130)
      .attr('height', 90)
      .attr('fill', 'rgba(0, 0, 0, 0.5)')
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 1);

    const legendItems = [
      { color: '#00ff88', label: 'Mean Forecast' },
      { color: 'rgba(255, 136, 0, 0.4)', label: '80% Confidence' },
      { color: 'rgba(255, 68, 68, 0.3)', label: '95% Confidence' },
      { color: 'rgba(255, 68, 68, 0.2)', label: 'Warning Front' },
    ];

    legendItems.forEach((item, i) => {
      const itemGroup = legend.append('g').attr('transform', `translate(10, ${15 + i * 18})`);
      itemGroup
        .append('rect')
        .attr('width', 15)
        .attr('height', 12)
        .attr('fill', item.color);
      itemGroup
        .append('text')
        .attr('x', 20)
        .attr('y', 10)
        .attr('fill', '#ffffff')
        .attr('font-size', '11px')
        .text(item.label);
    });
  }, [forecastData, loading, width, height]);

  if (loading) {
    return (
      <div style={{ color: '#ffffff', textAlign: 'center', padding: '40px' }}>
        Loading forecast clouds...
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '10px', color: '#ffffff', fontSize: '14px', display: 'flex', gap: '20px', alignItems: 'center' }}>
        <strong>Predictive Horizon Clouds</strong>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label style={{ fontSize: '12px' }}>Scenario Adjustment:</label>
          <input
            type="range"
            min="0.5"
            max="1.5"
            step="0.1"
            value={scenarioAdjustment}
            onChange={(e) => setScenarioAdjustment(parseFloat(e.target.value))}
            style={{ width: '150px' }}
          />
          <span style={{ fontSize: '12px', minWidth: '40px' }}>{(scenarioAdjustment * 100).toFixed(0)}%</span>
        </div>
      </div>
      <svg ref={svgRef} width={width} height={height - 50} style={{ flex: 1 }} />
    </div>
  );
}
