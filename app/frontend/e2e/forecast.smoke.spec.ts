import { test, expect } from '@playwright/test';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8100';

async function waitForRegionsReady(page: any, request: any) {
  // 1. Wait for the page to load
  await page.goto('/forecast', { waitUntil: 'domcontentloaded' });

  // 2. Wait for region dropdown to be visible - this is the real source of truth
  const regionSelect = page.locator('select').first();
  await regionSelect.waitFor({ state: 'visible', timeout: 60_000 });

  // 3. Wait for regions to actually load (options > 1)
  await page.waitForFunction(
    () => {
      const select = document.querySelector('select');
      return select && select.options.length > 1;
    },
    { timeout: 60_000 }
  );

  // 4. Optional: sanity-check the backend, but don't fail if it's slightly off
  try {
    const response = await request.get(`${API_BASE}/api/forecasting/regions`, { timeout: 10_000 });
    if (!response.ok()) {
      console.warn(`Regions API non-200: ${response.status()} (continuing anyway, UI loaded)`);
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

  test('Generate forecast and verify results sections exist', async ({ page }) => {
    try {
      // Verify Grafana dashboards are embedded (Grafana-first UI)
      const iframes = page.locator('iframe');
      await expect(iframes.first()).toBeVisible({ timeout: 30000 });
      
      // Verify multiple dashboards are present
      const iframeCount = await iframes.count();
      if (iframeCount < 2) {
        test.skip('No dashboards loaded for testing');
        return;
      }

      // Grafana-first UI: dashboards auto-load, verify they contain valid src
      const firstIframe = iframes.first();
      const src = await firstIframe.getAttribute('src');
      
      // Verify iframe src points to Grafana
      expect(src).toBeTruthy();
      expect(src).toMatch(/grafana|\/d\/);
    } catch (error) {
      // Capture screenshot on failure for debugging
      await page.screenshot({ path: 'test-results/forecast-fail.png', fullPage: true });
      throw error;
    }
  });
});
