# Interactive Demo Features

**Live Demo:** https://codethor0.github.io/human-behaviour-convergence/docs/index.html

## Overview

The interactive demo is a fully client-side forecasting simulation that runs entirely in the browser. No backend required—perfect for GitHub Pages deployment!

---

## Interactive Features

### 1. Real-Time Parameter Controls

**Region Input**
- Text input for region identifier (e.g., `us-midwest`, `europe-central`)
- Auto-updates forecast when changed (with debouncing)
- Visual feedback on input

**Horizon Slider**
- Range slider: 1-30 days
- Live value display above slider
- Real-time forecast updates
- Smooth transitions

**Modality Selection**
- Interactive checkboxes for 4 modalities:
  - **Satellite** - Imagery data
  - **Mobility** - Telemetry data
  - **Social** - Activity signals
  - **Environmental** - Sensor data
- Visual cards with hover effects
- Instant forecast updates when toggled

**Simulation Speed Control**
- 5-speed slider: Very Slow → Very Fast
- Controls auto-update frequency:
  - Very Slow: 2000ms (2 seconds)
  - Slow: 1500ms (1.5 seconds)
  - Normal: 1000ms (1 second)
  - Fast: 500ms (0.5 seconds)
  - Very Fast: 250ms (0.25 seconds)

**Auto-Update Toggle**
- Enable/disable real-time simulation
- When enabled: Forecasts regenerate automatically based on simulation speed
- When disabled: Manual updates only (via "Generate Now" button)

---

### 2. Live Forecast Display

**Current Forecast Card**
- Large, animated forecast index and confidence displays
- Visual progress bars with gradient animations
- Modal contribution breakdown with individual progress bars
- Parameter summary (region, horizon, modalities)
- Ethics disclaimer (synthetic data only)

**Visual Progress Bars**
- Forecast Index: Cyan gradient bar (0-100% scale)
- Confidence Level: Emerald gradient bar (0-100% scale)
- Modal Contributions: Individual bars per modality
- Smooth CSS transitions on all updates

---

### 3. Interactive Chart Visualization

**Chart.js Line Chart**
- Tracks forecast history (last 20 forecasts)
- Dual-line visualization:
  - **Forecast Index** (cyan line)
  - **Confidence** (emerald line)
- Smooth curve interpolation
- Real-time updates as new forecasts are generated
- Responsive design (adjusts to container size)

**Chart Controls**
- "Clear" button to reset history
- Automatic scrolling to latest forecast
- Shows up to 20 most recent forecasts

---

### 4. Scenario Comparison

**Comparison Grid**
- Save up to 6 scenarios for side-by-side comparison
- Each scenario card shows:
  - Scenario name (region + horizon)
  - Forecast index and confidence
  - Modalities used
  - Remove button (×)
- Visual cards with hover effects
- Grid layout (2-3 columns, responsive)

**Save Scenario**
- "Save Current Scenario" button
- Automatically names scenarios: `{region} ({horizon}d)`
- Instant comparison against other saved scenarios

---

### 5. Statistics Panel

**Live Statistics**
- **Forecasts Generated:** Total count of forecasts created
- **Avg. Forecast:** Average forecast index across all generated forecasts
- **Avg. Confidence:** Average confidence level
- **Scenarios Saved:** Number of saved scenarios
- Updates in real-time as you generate forecasts

---

### 6. Public Data Snapshot

**Live Data Display** (when backend available)
- Shows latest public data snapshot date
- Displays row counts per source:
  - Wikipedia pageviews
  - OSM changesets
  - NASA FIRMS fires
- Graceful fallback when API unavailable

**API Detection**
- Automatically detects if backend is running on `localhost:8000`
- Falls back to demo mode when API unavailable
- Works seamlessly in both modes

---

## Visual Design

### Color Scheme
- **Primary (Cyan):** Forecast index displays, primary CTAs
- **Secondary (Emerald):** Confidence displays, success states
- **Background:** Dark gradient (slate-900 → slate-950)
- **Borders:** Subtle slate-700/800 borders
- **Text:** Slate-100/200/300 hierarchy

### Animations
- **Fade-in:** New forecast cards fade in smoothly
- **Progress Bar Transitions:** 700ms ease-out transitions
- **Hover Effects:** Modality badges and cards scale on hover
- **Chart Updates:** Smooth line animations

### Responsive Layout
- **Desktop:** 3-column grid (2/3 main content, 1/3 sidebar)
- **Tablet:** 2-column layout
- **Mobile:** Single column, stacked sections

---

## Technical Implementation

### Forecast Generation
- **Deterministic:** Same inputs always produce same outputs
- **Seeded PRNG:** JavaScript implementation matching Python's `random.Random(seed)`
- **Formula:** Matches Python backend exactly:
  - Base value: 0.45-0.85 (random)
  - Modality factor: 1.0 + (0.05 × modality_count)
  - Final forecast: `base × modality_factor`
  - Confidence: 0.55-0.99 (random)

### State Management
- **Forecast History:** Array of last 20 forecasts
- **Saved Scenarios:** Array of up to 6 saved scenarios
- **Current Forecast:** Active forecast object
- **Chart Instance:** Chart.js instance (cleaned up on updates)

### Performance
- **Debounced Inputs:** Region input debounced (500ms)
- **Efficient Updates:** Only updates necessary DOM elements
- **Chart Optimization:** Limits history to 20 forecasts for performance

---

## Usage Instructions

### Basic Usage

1. **Open the demo:**
   ```
   python3 -m http.server 8080 --directory docs
   # Then open: http://localhost:8080/index.html
   ```

2. **Generate a forecast:**
   - Adjust parameters (region, horizon, modalities)
   - Click "Generate Now" or enable auto-update
   - Watch forecast update in real-time

3. **Compare scenarios:**
   - Generate different forecasts
   - Click "Save Current Scenario" for each
   - Compare forecasts side-by-side

4. **Track history:**
   - Enable auto-update
   - Adjust simulation speed
   - Watch forecast history chart update live

### Advanced Features

**Real-Time Simulation:**
1. Enable "Auto-update forecast"
2. Adjust simulation speed (1-5)
3. Change parameters to see live updates

**Scenario Comparison:**
1. Generate forecast for `us-midwest`, horizon `7`, modalities `satellite, mobility`
2. Save scenario
3. Change to `us-west`, horizon `14`, modalities `satellite, social, environmental`
4. Save scenario
5. Compare both side-by-side

**Forecast History:**
1. Generate multiple forecasts
2. Watch line chart update
3. Clear history when needed
4. Focus on trends and patterns

---

## Deployment

### GitHub Pages

The demo is automatically deployed to GitHub Pages when pushed to `main` branch:

**URL:** https://codethor0.github.io/human-behaviour-convergence/docs/index.html

**Deployment Workflow:**
- `.github/workflows/deploy-pages.yml` handles deployment
- Triggers on changes to `docs/**`, `diagram/**`, or `index.html`
- No build step required (pure HTML/CSS/JS)

### Local Development

**Standalone Mode (No Backend):**
```bash
python3 -m http.server 8080 --directory docs
open http://localhost:8080/index.html
```

**With Backend API:**
```bash
# Terminal 1: Backend
docker compose up app

# Terminal 2: Demo
python3 -m http.server 8080 --directory docs
open http://localhost:8080/index.html
```

---

## Browser Compatibility

**Tested On:**
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

**Required Features:**
- ES6 JavaScript (arrow functions, template literals, destructuring)
- Canvas API (for Chart.js)
- CSS Grid and Flexbox
- CSS Transitions and Animations

**Polyfills:** None required (modern browsers only)

---

## Future Enhancements

**Potential Additions:**
1. **Export Forecasts:** Download forecasts as JSON/CSV
2. **Forecast Share:** Generate shareable URLs with parameters
3. **Parameter Presets:** Quick-load common configurations
4. **Advanced Visualizations:** Heatmaps, 3D charts, network graphs
5. **Forecast Validation:** Compare predictions vs. actuals (synthetic)
6. **Multi-Region Comparison:** Simultaneous forecasts for multiple regions
7. **Time Series Simulation:** Animate forecasts over time
8. **Interactive Diagram:** Click diagram nodes to filter data sources

---

**Status:** ✅ Fully Interactive - Ready for GitHub Pages Deployment

