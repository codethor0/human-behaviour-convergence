'use client';

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface SubIndex {
  id: string;
  name: string;
  parent: string;
  value: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface Correlation {
  source: string;
  target: string;
  strength: number;
}

interface ConvergenceVortexProps {
  region?: string | null;
  width?: number;
  height?: number;
}

export function ConvergenceVortex({ region, width = 800, height = 600 }: ConvergenceVortexProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [subIndices, setSubIndices] = useState<SubIndex[]>([]);
  const [correlations, setCorrelations] = useState<Correlation[]>([]);
  const [loading, setLoading] = useState(true);
  const simulationRef = useRef<d3.Simulation<SubIndex, Correlation> | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch parent sub-indices
        const metricsResponse = await fetch(`http://localhost:8100/api/metrics${region ? `?region=${region}` : ''}`);
        const metrics = await metricsResponse.json();
        
        // Mock sub-indices structure - would come from Prometheus
        const mockSubIndices: SubIndex[] = [
          { id: 'economic_stress', name: 'Economic', parent: 'economic_stress', value: 0.52 },
          { id: 'environmental_stress', name: 'Environmental', parent: 'environmental_stress', value: 0.48 },
          { id: 'mobility_activity', name: 'Mobility', parent: 'mobility_activity', value: 0.45 },
          { id: 'digital_attention', name: 'Digital', parent: 'digital_attention', value: 0.61 },
          { id: 'public_health_stress', name: 'Health', parent: 'public_health_stress', value: 0.55 },
          { id: 'political_stress', name: 'Political', parent: 'political_stress', value: 0.43 },
          { id: 'crime_stress', name: 'Crime', parent: 'crime_stress', value: 0.38 },
          { id: 'misinformation_stress', name: 'Misinfo', parent: 'misinformation_stress', value: 0.49 },
          { id: 'social_cohesion_stress', name: 'Social', parent: 'social_cohesion_stress', value: 0.47 },
        ];

        // Calculate correlations (mock - would come from actual correlation analysis)
        const mockCorrelations: Correlation[] = [
          { source: 'economic_stress', target: 'mobility_activity', strength: 0.72 },
          { source: 'economic_stress', target: 'digital_attention', strength: 0.65 },
          { source: 'environmental_stress', target: 'public_health_stress', strength: 0.68 },
          { source: 'environmental_stress', target: 'mobility_activity', strength: 0.55 },
          { source: 'political_stress', target: 'social_cohesion_stress', strength: 0.71 },
          { source: 'political_stress', target: 'misinformation_stress', strength: 0.78 },
          { source: 'crime_stress', target: 'social_cohesion_stress', strength: 0.63 },
          { source: 'digital_attention', target: 'misinformation_stress', strength: 0.69 },
          { source: 'public_health_stress', target: 'mobility_activity', strength: 0.58 },
        ];

        setSubIndices(mockSubIndices);
        setCorrelations(mockCorrelations);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch convergence data:', error);
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000); // Update every minute
    return () => clearInterval(interval);
  }, [region]);

  useEffect(() => {
    if (loading || !svgRef.current || subIndices.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Create force simulation
    const simulation = d3
      .forceSimulation<SubIndex>(subIndices)
      .force(
        'link',
        d3
          .forceLink<SubIndex, Correlation>(correlations)
          .id((d) => d.id)
          .distance((d) => 200 - d.strength * 100)
          .strength((d) => d.strength)
      )
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(40));

    simulationRef.current = simulation;

    // Create links (edges)
    const link = svg
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(correlations)
      .enter()
      .append('line')
      .attr('stroke', (d) => {
        const opacity = d.strength;
        return `rgba(0, 255, 136, ${opacity})`;
      })
      .attr('stroke-width', (d) => d.strength * 8)
      .attr('stroke-opacity', 0.6);

    // Create link labels (correlation strength)
    const linkLabels = svg
      .append('g')
      .attr('class', 'link-labels')
      .selectAll('text')
      .data(correlations.filter((d) => d.strength > 0.6))
      .enter()
      .append('text')
      .attr('font-size', '10px')
      .attr('fill', '#ffffff')
      .text((d) => (d.strength * 100).toFixed(0) + '%');

    // Create nodes
    const node = svg
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(subIndices)
      .enter()
      .append('g')
      .call(
        d3
          .drag<SVGGElement, SubIndex>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = undefined;
            d.fy = undefined;
          })
      );

    // Add pulsing circles for nodes
    const circles = node
      .append('circle')
      .attr('r', (d) => 20 + d.value * 15)
      .attr('fill', (d) => {
        if (d.value < 0.3) return '#00ff88';
        if (d.value < 0.5) return '#ffd700';
        if (d.value < 0.7) return '#ff8800';
        return '#ff4444';
      })
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 2)
      .attr('opacity', 0.9)
      .style('cursor', 'pointer');

    // Add pulse animation for high-value nodes
    circles
      .filter((d) => d.value > 0.6)
      .append('animate')
      .attr('attributeName', 'r')
      .attr('values', (d) => `${20 + d.value * 15};${25 + d.value * 15};${20 + d.value * 15}`)
      .attr('dur', '2s')
      .attr('repeatCount', 'indefinite');

    // Add labels
    const labels = node
      .append('text')
      .text((d) => d.name)
      .attr('font-size', '12px')
      .attr('fill', '#ffffff')
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => 35 + d.value * 15)
      .style('pointer-events', 'none');

    // Highlight critical paths (strong correlations)
    const criticalPaths = correlations.filter((d) => d.strength > 0.7);
    link
      .filter((d) => criticalPaths.includes(d))
      .attr('stroke', '#ff4444')
      .attr('stroke-width', (d) => d.strength * 10)
      .attr('stroke-opacity', 0.8);

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d) => (d.source as SubIndex).x!)
        .attr('y1', (d) => (d.source as SubIndex).y!)
        .attr('x2', (d) => (d.target as SubIndex).x!)
        .attr('y2', (d) => (d.target as SubIndex).y!);

      linkLabels
        .attr('x', (d) => {
          const source = subIndices.find((s) => s.id === d.source);
          const target = subIndices.find((s) => s.id === d.target);
          return source && target ? (source.x! + target.x!) / 2 : 0;
        })
        .attr('y', (d) => {
          const source = subIndices.find((s) => s.id === d.source);
          const target = subIndices.find((s) => s.id === d.target);
          return source && target ? (source.y! + target.y!) / 2 : 0;
        });

      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
    };
  }, [subIndices, correlations, loading, width, height]);

  if (loading) {
    return (
      <div style={{ color: '#ffffff', textAlign: 'center', padding: '40px' }}>
        Loading convergence network...
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '10px', color: '#ffffff', fontSize: '14px' }}>
        <strong>Convergence Vortex</strong> - Node size = Index value, Edge thickness = Correlation strength
        <br />
        <span style={{ fontSize: '12px', color: '#a0a0a0' }}>
          Red edges indicate critical paths (correlation &gt; 70%). Drag nodes to explore.
        </span>
      </div>
      <svg ref={svgRef} width={width} height={height - 60} style={{ flex: 1 }} />
    </div>
  );
}
