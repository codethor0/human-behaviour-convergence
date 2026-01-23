import { test, expect } from '@playwright/test';

async function waitForRegionsReady(page: any, request: any) {
  // 1. Navigate to forecast page first
  await page.goto('/forecast', { waitUntil: 'domcontentloaded' });

  // 2. Wait for region selector to be visible (primary UI signal)
  const regionSelect = page.locator('select').first();
  await regionSelect.waitFor({ state: 'visible', timeout: 60_000 });

  // 3. Wait for regions to load (options > 1)
  await page.waitForFunction(
    () => {
      const select = document.querySelector('select');
      return select && select.options.length > 1;
    },
    { timeout: 60_000 }
  );

  // 4. Optional: Check regions API (best-effort, non-blocking)
  try {
    const response = await request.get('http://localhost:8100/api/forecasting/regions');
    const regions = await response.json();
    if (!Array.isArray(regions) || regions.length === 0) {
      console.warn('Regions API returned empty array (continuing anyway, UI loaded)');
    }
  } catch (err) {
    console.warn(`Regions API check failed: ${String(err)} (continuing anyway, UI loaded)`);
  }
}

test.describe('Forecast Smoke Tests', () => {
  test.beforeEach(async ({ page, request }) => {
    // Wait for UI to be ready (regions loaded)
    await waitForRegionsReady(page, request);
    
    // Wait for network to settle
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {
      console.warn('Network not idle after 10s, continuing anyway');
    });
  });

  test('Generate forecast and verify Grafana dashboards load', async ({ page }) => {
    try {
      // Wait for region dropdown to be available
      const regionSelect = page.locator('select').first();
      await regionSelect.waitFor({ timeout: 10000 });

      // Select first available region deterministically
      const options = await regionSelect.locator('option').all();
      if (options.length < 2) {
        test.skip('No regions available for testing');
        return;
      }

      // Select the first non-empty option (skip index 0 if it's empty/default)
      const firstValidOption = options[1];
      const regionValue = await firstValidOption.getAttribute('value');
      if (regionValue) {
        await regionSelect.selectOption(regionValue);
      }

      // Wait for generate button
      const generateButton = page.getByTestId('forecast-generate-button');
      await expect(generateButton).toBeVisible({ timeout: 10000 });
      await expect(generateButton).toBeEnabled({ timeout: 30000 });

      // Click generate
      await generateButton.click();

      // Wait for Grafana dashboards to load (they appear after forecast generation)
      await page.waitForFunction(
        () => {
          const iframes = document.querySelectorAll('iframe');
          return iframes.length > 0;
        },
        { timeout: 60000 }
      );

      // Verify Grafana dashboard iframes are embedded
      const dashboardIframes = page.locator('iframe');
      await expect(dashboardIframes.first()).toBeVisible();
      
      // Verify at least one Grafana dashboard is present
      const iframeCount = await dashboardIframes.count();
      expect(iframeCount).toBeGreaterThan(0);

      // Verify iframe src points to Grafana
      const firstIframe = dashboardIframes.first();
      const src = await firstIframe.getAttribute('src');
      expect(src).toBeTruthy();
      expect(src).toMatch(/grafana|\/d\//);
      
      // Verify iframe src contains expected dashboard UIDs
      const allIframes = await dashboardIframes.all();
      const iframeSrcs = await Promise.all(allIframes.map(iframe => iframe.getAttribute('src')));
      const expectedDashboards = [
        'behavior-index-global',
        'subindex-deep-dive',
        'data-sources-health',
        'regional-variance-explorer',
        'forecast-quality-drift',
        'algorithm-model-comparison',
        'source-health-freshness',
      ];
      const foundDashboards = expectedDashboards.filter(dash => 
        iframeSrcs.some(src => src && src.includes(dash))
      );
      // Verify at least 3 dashboards are present (core + new ones)
      expect(foundDashboards.length).toBeGreaterThanOrEqual(3);
      
      // Verify iframes are visible and have non-zero dimensions
      for (const iframe of allIframes) {
        const box = await iframe.boundingBox();
        expect(box).toBeTruthy();
        expect(box!.width).toBeGreaterThan(0);
        expect(box!.height).toBeGreaterThan(0);
      }
    } catch (error) {
      // Capture screenshot on failure for debugging
      await page.screenshot({ path: 'test-results/forecast-fail.png', fullPage: true });
      throw error;
    }
  });
});
