/**
 * Design System for Next-Generation Visualizations
 * 
 * Implements the "3-color palette" constraint with intensity variations
 * and comprehensive spacing/typography scales.
 */

export const colors = {
  // Primary Color Palette (3 base colors + variations)
  primary: {
    base: '#0070f3', // Blue - primary actions, data
    light: '#3291ff',
    dark: '#0051cc',
    lightest: '#e6f2ff',
    darkest: '#003d99',
  },
  secondary: {
    base: '#00ff88', // Green - positive, stable states
    light: '#33ffa3',
    dark: '#00cc6d',
    lightest: '#e6fff4',
    darkest: '#009955',
  },
  accent: {
    base: '#ff6b6b', // Red - alerts, critical states
    light: '#ff8e8e',
    dark: '#cc5555',
    lightest: '#ffe6e6',
    darkest: '#993333',
  },
  
  // Neutral grays for backgrounds and text
  neutral: {
    white: '#ffffff',
    gray50: '#fafafa',
    gray100: '#f5f5f5',
    gray200: '#e5e5e5',
    gray300: '#d4d4d4',
    gray400: '#a3a3a3',
    gray500: '#737373',
    gray600: '#525252',
    gray700: '#404040',
    gray800: '#262626',
    gray900: '#171717',
    black: '#000000',
  },
  
  // Semantic colors (derived from base palette)
  semantic: {
    success: '#00ff88',
    warning: '#ffaa00',
    error: '#ff6b6b',
    info: '#0070f3',
  },
  
  // Risk level colors (for behavior index)
  risk: {
    low: '#00ff88',      // Green (0-0.4)
    medium: '#ffaa00',   // Yellow (0.4-0.7)
    high: '#ff6b6b',     // Red (0.7-1.0)
  },
  
  // Confidence levels (for opacity/intensity)
  confidence: {
    high: 1.0,      // Full opacity
    medium: 0.7,    // 70% opacity
    low: 0.4,       // 40% opacity
    veryLow: 0.2,   // 20% opacity
  },
} as const;

export const typography = {
  fontFamily: {
    sans: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    mono: 'Menlo, Monaco, "Courier New", monospace',
  },
  fontSize: {
    xs: '0.75rem',    // 12px
    sm: '0.875rem',   // 14px
    base: '1rem',     // 16px
    lg: '1.125rem',   // 18px
    xl: '1.25rem',    // 20px
    '2xl': '1.5rem',  // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem', // 36px
    '5xl': '3rem',    // 48px
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeight: {
    tight: 1.25,
    normal: 1.5,
    relaxed: 1.75,
  },
} as const;

export const spacing = {
  xs: '0.25rem',   // 4px
  sm: '0.5rem',    // 8px
  md: '1rem',      // 16px
  lg: '1.5rem',    // 24px
  xl: '2rem',      // 32px
  '2xl': '3rem',   // 48px
  '3xl': '4rem',   // 64px
  '4xl': '6rem',   // 96px
} as const;

export const borderRadius = {
  none: '0',
  sm: '0.125rem',  // 2px
  md: '0.375rem',  // 6px
  lg: '0.5rem',    // 8px
  xl: '0.75rem',   // 12px
  '2xl': '1rem',  // 16px
  full: '9999px',
} as const;

export const shadows = {
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
} as const;

export const transitions = {
  fast: '150ms ease-in-out',
  normal: '300ms ease-in-out',
  slow: '500ms ease-in-out',
} as const;

export const zIndex = {
  base: 0,
  dropdown: 1000,
  sticky: 1020,
  fixed: 1030,
  modalBackdrop: 1040,
  modal: 1050,
  popover: 1060,
  tooltip: 1070,
} as const;

// Breakpoints for responsive design
export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// Focus mode styles (dim non-critical elements during crisis)
export const focusMode = {
  dimmed: {
    opacity: 0.3,
    pointerEvents: 'none' as const,
  },
  highlighted: {
    opacity: 1,
    zIndex: zIndex.modal,
  },
} as const;
