'use client';

import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

interface HeatPoint {
  lat: number;
  lon: number;
  value: number;
  timestamp: string;
}

interface BehavioralHeatCartographyProps {
  regions?: Array<{ id: string; name: string; latitude: number; longitude: number }>;
  width?: number;
  height?: number;
}

export function BehavioralHeatCartography({ regions, width: _width = 1000, height: _height = 600 }: BehavioralHeatCartographyProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const [heatData, setHeatData] = useState<HeatPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeIndex, setTimeIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch data for all regions
        const regionIds = regions?.map(r => r.id) || ['city_nyc', 'us_il', 'us_az', 'us_fl'];
        const allData: HeatPoint[] = [];
        
        for (const regionId of regionIds) {
          const response = await fetch(
            `http://localhost:8100/api/forecast?region_id=${regionId}&days_back=7&forecast_horizon=7`
          );
          const data = await response.json();
          
          const region = regions?.find(r => r.id === regionId) || { latitude: 40.7128, longitude: -74.0060 };
          
          (data.history || []).forEach((h: any) => {
            allData.push({
              lat: region.latitude,
              lon: region.longitude,
              value: h.behavior_index || 0.5,
              timestamp: h.timestamp,
            });
          });
        }
        
        setHeatData(allData);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch heat map data:', error);
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [regions]);

  useEffect(() => {
    if (loading || !mapContainerRef.current || heatData.length === 0) return;

    // Initialize map
    mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || '';
    
    if (!mapRef.current) {
      const map = new mapboxgl.Map({
        container: mapContainerRef.current!,
        style: 'mapbox://styles/mapbox/dark-v10',
        center: [-98.5795, 39.8283], // Center of US
        zoom: 4,
      });

      mapRef.current = map;

      map.on('load', () => {
        // Add heat source
        const uniqueTimestamps = Array.from(new Set(heatData.map(d => d.timestamp))).sort();
        
        map.addSource('heat-source', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: heatData
              .filter(d => d.timestamp === uniqueTimestamps[timeIndex])
              .map(d => ({
                type: 'Feature',
                geometry: {
                  type: 'Point',
                  coordinates: [d.lon, d.lat],
                },
                properties: {
                  value: d.value,
                },
              })),
          },
        });

        // Add heat layer
        map.addLayer({
          id: 'heat-layer',
          type: 'heatmap',
          source: 'heat-source',
          paint: {
            'heatmap-weight': {
              property: 'value',
              type: 'exponential',
              stops: [[0, 0], [1, 1]],
            },
            'heatmap-intensity': {
              stops: [[0, 0.5], [20, 1.5]],
            },
            'heatmap-color': [
              'interpolate',
              ['linear'],
              ['heatmap-density'],
              0, 'rgba(0, 255, 136, 0)',
              0.2, 'rgba(0, 255, 136, 0.3)',
              0.4, 'rgba(255, 215, 0, 0.5)',
              0.6, 'rgba(255, 136, 0, 0.7)',
              1, 'rgba(255, 68, 68, 0.9)',
            ],
            'heatmap-radius': {
              stops: [[0, 20], [20, 80]],
            },
            'heatmap-opacity': 0.8,
          },
        });

        // Add point layer for precise values
        map.addSource('point-source', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: heatData
              .filter(d => d.timestamp === uniqueTimestamps[timeIndex])
              .map(d => ({
                type: 'Feature',
                geometry: {
                  type: 'Point',
                  coordinates: [d.lon, d.lat],
                },
                properties: {
                  value: d.value,
                },
              })),
          },
        });

        map.addLayer({
          id: 'point-layer',
          type: 'circle',
          source: 'point-source',
          paint: {
            'circle-radius': {
              property: 'value',
              type: 'exponential',
              stops: [[0, 5], [1, 30]],
            },
            'circle-color': {
              property: 'value',
              type: 'exponential',
              stops: [
                [0, '#00ff88'],
                [0.3, '#ffd700'],
                [0.5, '#ff8800'],
                [0.7, '#ff4444'],
              ],
            },
            'circle-opacity': 0.8,
            'circle-stroke-width': 2,
            'circle-stroke-color': '#ffffff',
          },
        });
      });
    } else {
      // Update existing map
      const uniqueTimestamps = Array.from(new Set(heatData.map(d => d.timestamp))).sort();
      const currentTimestamp = uniqueTimestamps[timeIndex];
      
      if (currentTimestamp) {
        const source = mapRef.current.getSource('heat-source') as mapboxgl.GeoJSONSource;
        const pointSource = mapRef.current.getSource('point-source') as mapboxgl.GeoJSONSource;
        
        if (source && pointSource) {
          const filtered = heatData.filter(d => d.timestamp === currentTimestamp);
          
          source.setData({
            type: 'FeatureCollection',
            features: filtered.map(d => ({
              type: 'Feature',
              geometry: {
                type: 'Point',
                coordinates: [d.lon, d.lat],
              },
              properties: {
                value: d.value,
              },
            })),
          });
          
          pointSource.setData({
            type: 'FeatureCollection',
            features: filtered.map(d => ({
              type: 'Feature',
              geometry: {
                type: 'Point',
                coordinates: [d.lon, d.lat],
              },
              properties: {
                value: d.value,
              },
            })),
          });
        }
      }
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [heatData, loading, timeIndex]);

  // Time-lapse animation
  useEffect(() => {
    if (!isPlaying || loading) return;
    
    const uniqueTimestamps = Array.from(new Set(heatData.map(d => d.timestamp))).sort();
    const interval = setInterval(() => {
      setTimeIndex((prev) => (prev + 1) % uniqueTimestamps.length);
    }, 1000);
    
    return () => clearInterval(interval);
  }, [isPlaying, heatData, loading]);

  if (loading) {
    return <div style={{ color: '#ffffff', textAlign: 'center', padding: '40px' }}>Loading heat cartography...</div>;
  }

  const uniqueTimestamps = Array.from(new Set(heatData.map(d => d.timestamp))).sort();

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <div
        ref={mapContainerRef}
        style={{ width: '100%', height: '100%' }}
      />
      <div style={{
        position: 'absolute',
        bottom: '20px',
        left: '20px',
        right: '20px',
        padding: '15px',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderRadius: '8px',
        color: '#ffffff',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '10px' }}>
          <input
            type="range"
            min="0"
            max={uniqueTimestamps.length - 1}
            value={timeIndex}
            onChange={(e) => setTimeIndex(parseInt(e.target.value))}
            style={{ flex: 1 }}
          />
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            style={{
              padding: '8px 16px',
              backgroundColor: isPlaying ? '#ff4444' : '#00ff88',
              color: '#000',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            {isPlaying ? '⏸ Pause' : '▶ Play'}
          </button>
        </div>
        <div style={{ fontSize: '12px', display: 'flex', justifyContent: 'space-between' }}>
          <span>Time: {uniqueTimestamps[timeIndex] || 'N/A'}</span>
          <span>Frame: {timeIndex + 1} / {uniqueTimestamps.length}</span>
        </div>
      </div>
    </div>
  );
}
