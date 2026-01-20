import { test, expect } from '@playwright/test';

test.describe('Live Monitoring - Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to live monitoring page
    await page.goto('/live', { waitUntil: 'domcontentloaded' });

    // Wait for page to be interactive
    await page.waitForLoadState('domcontentloaded');
    
    // Wait for region dropdown to be available
    const regionSelect = page.locator('select').first();
    await regionSelect.waitFor({ state: 'visible', timeout: 60000 });
    
    // Wait for regions to load (options > 1)
    await page.waitForFunction(
      () => {
        const select = document.querySelector('select');
        return select && select.options.length > 1;
      },
      { timeout: 60000 }
    );
  });

  test('Test 4: Exactly 1 region selection', async ({ page }) => {
    // Refactored: Live page now uses single-region dropdown with Grafana dashboards
    const regionSelect = page.locator('select').first();
    await regionSelect.waitFor({ timeout: 10000 });

    // Verify we can select a region
    const options = await regionSelect.locator('option').all();
    expect(options.length).toBeGreaterThan(1);

    // Select first valid region
    const firstValidOption = options[1];
    const regionValue = await firstValidOption?.getAttribute('value');
    if (regionValue) {
      await regionSelect.selectOption(regionValue);
    }

    // Verify Grafana dashboards are embedded (new UI is Grafana-first)
    const iframes = page.locator('iframe');
    await expect(iframes.first()).toBeVisible({ timeout: 15000 });
  });

  test('Test 5: Exactly 3 regions selection', async ({ page }) => {
    // Note: Multi-region selection was removed in UI refactor
    // This test now just verifies region dropdown works
    const regionSelect = page.locator('select').first();
    await expect(regionSelect).toBeVisible();

    // Verify dropdown is enabled and has regions
    await expect(regionSelect).toBeEnabled();
    const options = await regionSelect.locator('option').all();
    expect(options.length).toBeGreaterThan(1);
  });

  test('Intelligence Summary displays correctly', async ({ page }) => {
    // Verify page loads successfully
    await expect(page.locator('header')).toBeVisible();
    
    // Verify region selector is present
    const regionSelect = page.locator('select').first();
    await expect(regionSelect).toBeVisible();
    
    // Verify Grafana iframes are present (intelligence layer shown via dashboards)
    await page.waitForFunction(
      () => document.querySelectorAll('iframe').length > 0,
      { timeout: 15000 }
    );
  });
});
