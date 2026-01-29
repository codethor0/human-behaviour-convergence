/**
 * Visualization Utility Functions
 * 
 * Common utilities for data transformation, color mapping, and animation
 */

import { colors, ConfidenceInterval } from '../visualizations/base/types';

/**
 * Map a value to a color based on risk level
 */
export function mapValueToRiskColor(value: number): string {
  if (value < 0.4) return colors.risk.low;
  if (value < 0.7) return colors.risk.medium;
  return colors.risk.high;
}

/**
 * Map a value to a color with intensity based on confidence
 */
export function mapValueToColorWithConfidence(
  value: number,
  confidence: number
): string {
  const baseColor = mapValueToRiskColor(value);
  const opacity = Math.max(colors.confidence.veryLow, Math.min(1, confidence));
  return `${baseColor}${Math.round(opacity * 255).toString(16).padStart(2, '0')}`;
}

/**
 * Calculate confidence interval bounds
 */
export function calculateConfidenceInterval(
  mean: number,
  stdDev: number,
  level: number = 0.95
): ConfidenceInterval {
  const zScore = level === 0.95 ? 1.96 : level === 0.90 ? 1.645 : 2.576;
  return {
    lower: mean - zScore * stdDev,
    upper: mean + zScore * stdDev,
    level,
  };
}

/**
 * Smooth time-series data using moving average
 */
export function smoothTimeSeries(
  data: Array<{ time: Date | string; value: number }>,
  windowSize: number = 3
): Array<{ time: Date | string; value: number }> {
  if (data.length < windowSize) return data;

  return data.map((point, index) => {
    if (index < windowSize - 1) return point;

    const window = data.slice(index - windowSize + 1, index + 1);
    const avg = window.reduce((sum, p) => sum + p.value, 0) / windowSize;

    return {
      time: point.time,
      value: avg,
    };
  });
}

/**
 * Calculate trend velocity (rate of change)
 */
export function calculateTrendVelocity(
  current: number,
  previous: number,
  timeDeltaSeconds: number
): number {
  if (timeDeltaSeconds === 0) return 0;
  return (current - previous) / timeDeltaSeconds;
}

/**
 * Format large numbers with K/M/B suffixes
 */
export function formatLargeNumber(value: number): string {
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(0);
}

/**
 * Format percentage
 */
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format duration in human-readable format
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

/**
 * Interpolate between two values
 */
export function interpolate(start: number, end: number, t: number): number {
  return start + (end - start) * Math.max(0, Math.min(1, t));
}

/**
 * Easing functions for animations
 */
export const easing = {
  linear: (t: number) => t,
  easeIn: (t: number) => t * t,
  easeOut: (t: number) => t * (2 - t),
  easeInOut: (t: number) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t),
};

/**
 * Debounce function calls
 */
export function debounce<T extends (..._args: unknown[]) => void>(
  func: T,
  wait: number
): (..._args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  return (..._args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(..._args), wait);
  };
}

/**
 * Throttle function calls
 */
export function throttle<T extends (..._args: unknown[]) => void>(
  func: T,
  limit: number
): (..._args: Parameters<T>) => void {
  let inThrottle: boolean;
  return (..._args: Parameters<T>) => {
    if (!inThrottle) {
      func(..._args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Check if data is stale
 */
export function isDataStale(
  lastUpdate: Date,
  stalenessThresholdSeconds: number = 300
): boolean {
  const ageSeconds = (Date.now() - lastUpdate.getTime()) / 1000;
  return ageSeconds > stalenessThresholdSeconds;
}
