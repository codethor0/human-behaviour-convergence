# Testing Guide

## E2E UI Contracts

The E2E Playwright tests enforce specific UI contracts for key pages. Tests must align with these contracts to remain stable.

### `/forecast` Page Contract

**UI Flow**:
1. Page loads with a region selection dropdown (`<select>`)
2. User selects a region from the dropdown
3. User clicks the "Generate Forecast" button (`data-testid="forecast-generate-button"`)
4. **After generation**: Grafana dashboard iframes appear

**Key Elements** (all must be present):
- Region `<select>` dropdown (first select element on page)
- Generate button with `data-testid="forecast-generate-button"`
- **Post-generation**: Multiple Grafana `<iframe>` elements with `src` matching `/d/` or `grafana`

**Why this matters**: Tests must NOT expect Grafana iframes before forecast generation. The page uses a traditional form → submit → results flow.

### `/history` Page Contract

**UI Type**: Traditional UI/table page (NO Grafana iframes)

**Key Elements** (all must be present):
- Page title with `data-testid="history-page-title"` containing "Forecast History"
- Forecast history container with `data-testid="forecast-history-container"`
- Filter controls:
  - Limit selector: `data-testid="history-limit-select"`
  - Region filter input: `data-testid="history-region-filter"`
  - Date range inputs: `data-testid="history-date-from"`, `data-testid="history-date-to"`
  - Sort order selector: `data-testid="history-sort-order"`
- History table or empty state message

**Why NO iframes**: The history page displays tabular forecast metadata with client-side filtering. It does NOT embed Grafana dashboards.

### Test Stability Rules

1. **Navigate first, then wait for UI**: Always navigate to the page before waiting for elements
2. **Use stable selectors**: Prefer `data-testid` attributes over brittle text/class selectors
3. **Timeouts**: Use explicit timeouts (60s) for first-load elements; shorter for already-loaded interactions
4. **Diagnostics**: Capture screenshots and console errors on failure
5. **No arbitrary waits**: Use `waitFor` with conditions, not `page.waitForTimeout`

---

## Location Normalization Testing

## Server Status

Backend server is running on: **http://localhost:8000**

## Quick Test Results

All location normalization tests passed:

```
 TEST 1: Ambiguous Washington Case - PASS
   Input: 'Event happened near Washington'
   Output: best_guess_region_id="us_wa", alternate_region_ids=["us_dc"]

 TEST 2: DC Context Case - PASS
   Input: 'Event happened near Washington D.C.'
   Output: normalized_location.region_id="us_dc"

 TEST 3: WA State Context Case - PASS
   Input: 'Event in Seattle, Washington'
   Output: normalized_location.region_id="us_wa"

 TEST 4: ForecastConfigBuilder Ambiguity - PASS
   Correctly converts best_guess_region_id to normalized_location
```

## Test Location Normalization

### Option 1: Run Test Script

```bash
export PYTHONPATH=$PWD
.venv/bin/python3 test_location_normalization.py
```

### Option 2: Run Pytest Tests

```bash
export PYTHONPATH=$PWD
pytest tests/test_location_normalizer.py::TestLocationNormalizer::test_ambiguity_handling -xvs
pytest tests/test_forecast_config.py::TestForecastConfigBuilder::test_ambiguity_handling -xvs
```

## Test via API

### Health Check

```bash
curl http://localhost:8000/health
```

### List Available Regions

```bash
curl http://localhost:8000/api/forecasting/regions | python3 -m json.tool
```

### Test Playground Compare (uses region IDs)

```bash
curl -X POST "http://localhost:8000/api/playground/compare" \
  -H "Content-Type: application/json" \
  -d '{
    "regions": ["us_wa", "us_dc"],
    "historical_days": 30,
    "forecast_horizon_days": 7
  }'
```

## Expected Behavior Summary

### Ambiguous Washington

- **Input:** "Event happened near Washington"
- **Output:**
  - `normalized_location = None`
  - `best_guess_region_id = "us_wa"`
  - `alternate_region_ids = ["us_dc"]`
  - `ambiguity_reason = "Ambiguous: Washington could refer to WA or DC"`

### DC Context

- **Input:** "Event at the White House" or "Event in Washington D.C."
- **Output:**
  - `normalized_location.region_id = "us_dc"`
  - Definite match (not ambiguous)

### WA State Context

- **Input:** "Event in Seattle, Washington"
- **Output:**
  - `normalized_location.region_id = "us_wa"`
  - Definite match (not ambiguous)

## CI Artifact Contract

### E2E Playwright Workflow Artifacts

The E2E Playwright Tests workflow (`.github/workflows/e2e-playwright.yml`) uploads three artifacts on every run (success or failure) via `if: always()`:

1. **backend-log**: Backend server logs (`/tmp/backend.log`)
2. **playwright-report**: HTML test report (`app/frontend/playwright-report/`)
3. **test-results**: Playwright test results directory (`app/frontend/test-results/`)

The `test-results` artifact is guaranteed to exist (CI creates the directory with a placeholder file) to avoid "no files found" warnings. Playwright only writes traces/screenshots to this directory on test failures or retries, so the placeholder ensures deterministic artifact upload.

**Note:** Do not remove the "Ensure test-results directory exists" step in the workflow; it prevents annotation warnings and ensures the artifact contract is maintained.

## Next Steps

1. Run the test script to verify all fixes
2. Test via API endpoints if available
3. Push changes to GitHub to verify CI passes
