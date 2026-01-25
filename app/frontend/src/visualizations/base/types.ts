/**
 * Base types for all visualization components
 */

export interface BaseVisualizationProps {
  /** Unique identifier for this visualization */
  id: string;
  /** Title to display */
  title?: string;
  /** Width in pixels or CSS units */
  width?: number | string;
  /** Height in pixels or CSS units */
  height?: number | string;
  /** Data to visualize */
  data?: unknown;
  /** Region ID for filtering */
  regionId?: string;
  /** Time range for data */
  timeRange?: {
    from: Date | string;
    to: Date | string;
  };
  /** Whether to show loading state */
  loading?: boolean;
  /** Error message if visualization fails */
  error?: string | Error;
  /** Callback when visualization is clicked */
  onClick?: (event: VisualizationClickEvent) => void;
  /** Callback when data is updated */
  onUpdate?: (data: unknown) => void;
  /** Additional CSS classes */
  className?: string;
  /** Whether visualization is in focus mode (highlighted) */
  focusMode?: boolean;
}

export interface VisualizationClickEvent {
  /** Type of element clicked */
  type: 'point' | 'region' | 'axis' | 'legend' | 'background';
  /** Data point or region clicked */
  data?: unknown;
  /** Coordinates of click */
  coordinates?: {
    x: number;
    y: number;
  };
}

export interface VisualizationUpdate {
  /** Timestamp of update */
  timestamp: Date;
  /** New data */
  data: unknown;
  /** Source of update */
  source: 'websocket' | 'poll' | 'user-action';
}

export interface ConfidenceInterval {
  /** Lower bound */
  lower: number;
  /** Upper bound */
  upper: number;
  /** Confidence level (0-1) */
  level: number;
}

export interface DataFreshness {
  /** Timestamp of last update */
  lastUpdate: Date;
  /** Age of data in seconds */
  ageSeconds: number;
  /** Whether data is stale */
  isStale: boolean;
  /** Staleness threshold in seconds */
  stalenessThreshold: number;
}

export type VisualizationType =
  | 'temporal-topology'
  | 'convergence-vortex'
  | 'predictive-clouds'
  | 'heat-cartography'
  | 'anomaly-theater'
  | 'narrative-streams'
  | 'timeseries'
  | 'network'
  | 'map'
  | 'gauge'
  | 'matrix';
