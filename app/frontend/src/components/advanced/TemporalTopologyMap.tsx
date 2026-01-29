'use client';

import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

interface TopologyPoint {
  time: number;
  behaviorIndex: number;
  causalDensity: number;
  confidence: number;
}

interface TemporalTopologyMapProps {
  region?: string | null;
  width?: number;
  height?: number;
}

export function TemporalTopologyMap({ region, width = 1000, height = 600 }: TemporalTopologyMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const [data, setData] = useState<TopologyPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRotating, setIsRotating] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`http://localhost:8100/api/forecast?region_id=${region || 'city_nyc'}&days_back=30&forecast_horizon=7`);
        const forecast = await response.json();
        
        const history = forecast.history || [];
        const points: TopologyPoint[] = history.map((h: any, idx: number) => ({
          time: idx,
          behaviorIndex: h.behavior_index || 0.5,
          causalDensity: Object.values(h.sub_indices || {}).reduce((sum: number, v: any) => sum + Math.abs(v - 0.5), 0) / 9,
          confidence: 0.8 - (idx / history.length) * 0.3, // Higher confidence for recent data
        }));
        
        setData(points);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch topology data:', error);
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [region]);

  useEffect(() => {
    if (loading || !containerRef.current || data.length === 0) return;

    const container = containerRef.current;
    
    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.set(15, 10, 15);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 10, 5);
    directionalLight.castShadow = true;
    scene.add(directionalLight);

    // Normalize data for 3D space
    const maxTime = Math.max(...data.map(d => d.time));
    const maxBI = Math.max(...data.map(d => d.behaviorIndex));
    const maxDensity = Math.max(...data.map(d => d.causalDensity));

    // Create surface geometry
    const geometry = new THREE.BufferGeometry();
    const vertices: number[] = [];
    const colors: number[] = [];
    const indices: number[] = [];

    // Generate grid points
    const gridSize = 20;
    for (let i = 0; i < gridSize; i++) {
      for (let j = 0; j < gridSize; j++) {
        const t = (i / gridSize) * maxTime;
        const _bi = (j / gridSize) * maxBI;
        
        // Find nearest data point
        const nearest = data.reduce((prev, curr) => 
          Math.abs(curr.time - t) < Math.abs(prev.time - t) ? curr : prev
        );
        
        const x = (t / maxTime) * 10 - 5;
        const y = (nearest.behaviorIndex / maxBI) * 5;
        const z = (nearest.causalDensity / maxDensity) * 5;
        
        vertices.push(x, y, z);
        
        // Color based on confidence and behavior index
        const hue = (1 - nearest.behaviorIndex) * 0.3; // Green to red
        const saturation = nearest.confidence;
        const lightness = 0.5;
        const color = new THREE.Color().setHSL(hue, saturation, lightness);
        colors.push(color.r, color.g, color.b);
      }
    }

    // Create indices for triangles
    for (let i = 0; i < gridSize - 1; i++) {
      for (let j = 0; j < gridSize - 1; j++) {
        const a = i * gridSize + j;
        const b = i * gridSize + j + 1;
        const c = (i + 1) * gridSize + j;
        const d = (i + 1) * gridSize + j + 1;
        
        indices.push(a, b, c);
        indices.push(b, d, c);
      }
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();

    const material = new THREE.MeshPhongMaterial({
      vertexColors: true,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.8,
      wireframe: false,
    });

    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    // Add data points as spheres
    const pointGeometry = new THREE.SphereGeometry(0.1, 8, 8);
    data.forEach((point) => {
      const x = (point.time / maxTime) * 10 - 5;
      const y = (point.behaviorIndex / maxBI) * 5;
      const z = (point.causalDensity / maxDensity) * 5;
      
      const pointMaterial = new THREE.MeshPhongMaterial({
        color: new THREE.Color().setHSL((1 - point.behaviorIndex) * 0.3, point.confidence, 0.6),
        emissive: new THREE.Color().setHSL((1 - point.behaviorIndex) * 0.3, point.confidence, 0.2),
      });
      
      const sphere = new THREE.Mesh(pointGeometry, pointMaterial);
      sphere.position.set(x, y, z);
      scene.add(sphere);
    });

    // Add axes
    const axesHelper = new THREE.AxesHelper(5);
    scene.add(axesHelper);

    // Animation
    let rotation = 0;
    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate);
      
      if (isRotating) {
        rotation += 0.005;
        camera.position.x = 15 * Math.cos(rotation);
        camera.position.z = 15 * Math.sin(rotation);
        camera.lookAt(0, 0, 0);
      }
      
      renderer.render(scene, camera);
    };
    animate();

    // Mouse controls
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    
    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
      setIsRotating(false);
    };
    
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      
      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;
      
      rotation += deltaX * 0.01;
      camera.position.x = 15 * Math.cos(rotation);
      camera.position.z = 15 * Math.sin(rotation);
      camera.position.y += deltaY * 0.1;
      camera.lookAt(0, 0, 0);
      
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };
    
    const onMouseUp = () => {
      isDragging = false;
    };
    
    renderer.domElement.addEventListener('mousedown', onMouseDown);
    renderer.domElement.addEventListener('mousemove', onMouseMove);
    renderer.domElement.addEventListener('mouseup', onMouseUp);
    renderer.domElement.style.cursor = 'grab';

    // Cleanup
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      renderer.domElement.removeEventListener('mousedown', onMouseDown);
      renderer.domElement.removeEventListener('mousemove', onMouseMove);
      renderer.domElement.removeEventListener('mouseup', onMouseUp);
      container.removeChild(renderer.domElement);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
    };
  }, [data, loading, width, height, isRotating]);

  if (loading) {
    return (
      <div style={{ color: '#ffffff', textAlign: 'center', padding: '40px' }}>
        Loading 3D topology landscape...
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <div
        ref={containerRef}
        style={{ width: '100%', height: '100%' }}
      />
      <div style={{
        position: 'absolute',
        top: '10px',
        left: '10px',
        padding: '10px',
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        borderRadius: '4px',
        color: '#ffffff',
        fontSize: '12px',
      }}>
        <div>X: Time | Y: Behavior Index | Z: Causal Density</div>
        <div>Color: Confidence Level | Drag to rotate</div>
        <button
          onClick={() => setIsRotating(!isRotating)}
          style={{
            marginTop: '5px',
            padding: '4px 8px',
            backgroundColor: isRotating ? '#00ff88' : '#666',
            color: '#000',
            border: 'none',
            borderRadius: '3px',
            cursor: 'pointer',
          }}
        >
          {isRotating ? 'Pause Rotation' : 'Resume Rotation'}
        </button>
      </div>
    </div>
  );
}
