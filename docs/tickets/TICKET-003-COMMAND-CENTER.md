# TICKET-003: Command Center - 6-Panel Cinematic Layout

## Priority: P0 (User-Facing)
## Estimate: 5 days
## Dependencies: TICKET-001, TICKET-002
## Sprint: 1

## Objective

Create the Tier 1 Command Center dashboard with a 6-panel cinematic layout optimized for executive decision-making. This is the primary entry point for high-level behavioral intelligence.

## Panel Specifications

### Panel 1: Live Behavior Index "Fuel Gauge"
- **Visual Style**: Circular gauge (like car fuel gauge)
- **Components**:
  - Current behavior index value (0-1 scale)
  - Trend velocity arrows (up/down/stable)
  - Color zones: Green (0-0.4), Yellow (0.4-0.7), Red (0.7-1.0)
  - Historical comparison (where we were 7d, 30d ago)
- **Update Frequency**: Real-time (WebSocket)
- **Interactivity**: Click to drill down to detailed view

### Panel 2: Critical Alerts Ticker
- **Visual Style**: Scrolling ticker tape (like news ticker)
- **Components**:
  - Top 5 active shocks/alerts
  - Color-coded severity (red/yellow/green)
  - Timestamp for each alert
  - Click to expand details
- **Update Frequency**: Real-time
- **Interactivity**: Click alert to see full context

### Panel 3: Regional Comparison Matrix
- **Visual Style**: Grid layout showing all monitored regions
- **Components**:
  - Each cell shows region name + current index value
  - Color-coded by risk level
  - Small trend indicator (arrow)
  - Hover shows quick stats
- **Update Frequency**: 30 seconds
- **Interactivity**: Click region to filter all panels

### Panel 4: 72-Hour Warning Radar
- **Visual Style**: Concentric circles (radar screen style)
- **Components**:
  - Center = current time
  - Concentric circles = 24h, 48h, 72h horizons
  - Risk indicators positioned by time-to-impact
  - Color intensity = severity
- **Update Frequency**: 1 minute
- **Interactivity**: Click risk indicator for details

### Panel 5: Confidence Thermometer
- **Visual Style**: Vertical thermometer gauge
- **Components**:
  - Data quality score (0-100%)
  - Data freshness indicator
  - Source health status
  - Color zones: Red (<70%), Yellow (70-90%), Green (>90%)
- **Update Frequency**: 30 seconds
- **Interactivity**: Click to see source breakdown

### Panel 6: Auto-Generated Insight of the Day
- **Visual Style**: Card with text + supporting visualization
- **Components**:
  - Natural language insight (2-3 sentences)
  - Supporting chart/graph
  - "Learn more" link
  - Refresh button (get new insight)
- **Update Frequency**: Daily (or on-demand refresh)
- **Interactivity**: Refresh button, "Learn more" link

## Layout Specifications

- **Grid Layout**: 3 columns × 2 rows
- **Panel Sizes**:
  - Row 1: Panel 1 (1 col), Panel 2 (2 cols)
  - Row 2: Panel 3 (1 col), Panel 4 (1 col), Panel 5 (1 col)
  - Row 3: Panel 6 (full width)
- **Responsive Breakpoints**:
  - Desktop (≥1280px): Full grid
  - Tablet (768-1279px): 2 columns
  - Mobile (<768px): Single column

## Technical Implementation

### Components to Create
- `CommandCenter.tsx` (main container)
- `FuelGauge.tsx` (Panel 1)
- `AlertTicker.tsx` (Panel 2)
- `RegionalMatrix.tsx` (Panel 3)
- `WarningRadar.tsx` (Panel 4)
- `ConfidenceThermometer.tsx` (Panel 5)
- `InsightCard.tsx` (Panel 6)

### Data Requirements
- Real-time behavior index updates (WebSocket)
- Alert/event stream (WebSocket)
- Regional data aggregation (API)
- Forecast data (API)
- Data quality metrics (API)
- Insight generation (API or client-side)

### Styling
- Use design system colors (max 3 base colors)
- Implement "Focus Mode" (dim non-critical panels during crisis)
- Smooth animations for updates
- Loading states for all panels

## Acceptance Criteria

- [ ] All 6 panels render correctly
- [ ] Real-time updates work via WebSocket
- [ ] Responsive layout works on all breakpoints
- [ ] Panel interactions work (click, hover)
- [ ] "Focus Mode" implemented
- [ ] Loading states implemented
- [ ] Error handling implemented
- [ ] Performance: < 100ms render time per panel update

## Files to Create

- `app/frontend/src/pages/command-center.tsx`
- `app/frontend/src/components/command-center/CommandCenter.tsx`
- `app/frontend/src/components/command-center/FuelGauge.tsx`
- `app/frontend/src/components/command-center/AlertTicker.tsx`
- `app/frontend/src/components/command-center/RegionalMatrix.tsx`
- `app/frontend/src/components/command-center/WarningRadar.tsx`
- `app/frontend/src/components/command-center/ConfidenceThermometer.tsx`
- `app/frontend/src/components/command-center/InsightCard.tsx`
- `app/frontend/src/hooks/useCommandCenterData.ts`
- `app/frontend/src/utils/insight-generator.ts`

## Testing

- [ ] Unit tests for each panel component
- [ ] Integration test for WebSocket updates
- [ ] Visual regression tests
- [ ] Responsive design tests
- [ ] Performance tests

## Definition of Done

- All 6 panels implemented and working
- Real-time updates functional
- Responsive design complete
- Interactions working
- Tests passing
- Documentation complete
