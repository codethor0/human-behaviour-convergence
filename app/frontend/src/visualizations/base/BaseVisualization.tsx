/**
 * Base Visualization Component
 * 
 * Provides common functionality for all visualization types:
 * - Loading states
 * - Error handling
 * - Data freshness indicators
 * - Focus mode support
 * - Click handling
 */

import React, { useState, useEffect } from 'react';
import { BaseVisualizationProps, DataFreshness } from './types';
import { colors, spacing, borderRadius, shadows } from '../../styles/design-system';

export function BaseVisualization({
  id,
  title,
  width = '100%',
  height = '100%',
  data,
  loading = false,
  error,
  onClick,
  onUpdate,
  className = '',
  focusMode = false,
  children,
}: BaseVisualizationProps & { children?: React.ReactNode }) {
  const [dataFreshness, _setDataFreshness] = useState<DataFreshness | null>(null);

  useEffect(() => {
    if (data && onUpdate) {
      onUpdate(data);
    }
  }, [data, onUpdate]);

  const containerStyle: React.CSSProperties = {
    width,
    height,
    backgroundColor: colors.neutral.white,
    borderRadius: borderRadius.lg,
    padding: spacing.md,
    boxShadow: shadows.md,
    position: 'relative',
    opacity: focusMode ? 1 : (focusMode === false ? 0.3 : 1),
    transition: 'opacity 0.3s ease-in-out',
    ...(focusMode && {
      zIndex: 1050,
      boxShadow: shadows.xl,
    }),
  };

  const handleClick = (event: React.MouseEvent) => {
    if (onClick) {
      onClick({
        type: 'background',
        coordinates: {
          x: event.clientX,
          y: event.clientY,
        },
      });
    }
  };

  return (
    <div
      id={id}
      className={`base-visualization ${className}`}
      style={containerStyle}
      onClick={handleClick}
      data-testid={`visualization-${id}`}
    >
      {title && (
        <h3
          style={{
            fontSize: '1.125rem',
            fontWeight: 600,
            marginBottom: spacing.md,
            color: colors.neutral.gray800,
          }}
        >
          {title}
        </h3>
      )}

      {loading && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            color: colors.neutral.gray500,
          }}
        >
          <div
            style={{
              width: '40px',
              height: '40px',
              border: `3px solid ${colors.neutral.gray200}`,
              borderTopColor: colors.primary.base,
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
            }}
          />
          <p style={{ marginTop: spacing.sm }}>Loading...</p>
        </div>
      )}

      {error && (
        <div
          style={{
            padding: spacing.md,
            backgroundColor: colors.accent.lightest,
            color: colors.accent.darkest,
            borderRadius: borderRadius.md,
            border: `1px solid ${colors.accent.light}`,
          }}
        >
          <strong>Error:</strong> {error instanceof Error ? error.message : error}
        </div>
      )}

      {!loading && !error && children}

      {dataFreshness && dataFreshness.isStale && (
        <div
          style={{
            position: 'absolute',
            top: spacing.sm,
            right: spacing.sm,
            padding: `${spacing.xs} ${spacing.sm}`,
            backgroundColor: colors.semantic.warning,
            color: colors.neutral.white,
            borderRadius: borderRadius.md,
            fontSize: '0.75rem',
            fontWeight: 500,
          }}
        >
          Data may be stale ({Math.round(dataFreshness.ageSeconds / 60)}m old)
        </div>
      )}

      <style jsx>{`
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}
