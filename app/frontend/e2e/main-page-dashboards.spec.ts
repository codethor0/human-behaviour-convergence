import { test, expect } from '@playwright/test';

test.describe('Main Page Dashboard Hub', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
  });

  test('Main page loads all dashboard sections', async ({ page }) => {
    await expect(page.locator('#behavior-forecast')).toBeVisible();
    await expect(page.locator('#live-playground')).toBeVisible();
    await expect(page.locator('#live-monitoring')).toBeVisible();
    await expect(page.locator('#results-dashboard')).toBeVisible();
    await expect(page.locator('#grafana-analytics')).toBeVisible();
  });

  test('Main page has 18+ Grafana iframe embeds', async ({ page }) => {
    const iframes = page.locator('iframe[src*="grafana"]');
    const count = await iframes.count();
    expect(count).toBeGreaterThanOrEqual(18);
  });

  test('All iframes have valid src attributes and non-zero dimensions', async ({ page }) => {
    const iframes = await page.locator('iframe').all();
    expect(iframes.length).toBeGreaterThanOrEqual(18);

    for (const iframe of iframes) {
      const src = await iframe.getAttribute('src');
      expect(src).toBeTruthy();
      expect(src).toContain('grafana');

      const box = await iframe.boundingBox();
      expect(box?.height).toBeGreaterThan(100);
      expect(box?.width).toBeGreaterThan(100);
    }
  });

  test('Global region selector exists and is functional', async ({ page }) => {
    const regionSelector = page.locator('[data-testid="global-region-selector"]');
    await expect(regionSelector).toBeVisible();
    await expect(regionSelector).toBeEnabled();

    const options = await regionSelector.locator('option').count();
    expect(options).toBeGreaterThan(0);
  });

  test('Region selector updates all dashboard URLs', async ({ page }) => {
    const regionSelector = page.locator('[data-testid="global-region-selector"]');

    const initialValue = await regionSelector.inputValue();
    expect(initialValue).toBeTruthy();

    const allOptions = await regionSelector.locator('option').all();
    if (allOptions.length > 1) {
      const secondOption = allOptions[1];
      const secondValue = await secondOption.getAttribute('value');

      if (secondValue && secondValue !== initialValue) {
        await regionSelector.selectOption(secondValue);
        await page.waitForTimeout(1000);

        const iframes = await page.locator('iframe[src*="var-region"]').all();
        for (const iframe of iframes) {
          const src = await iframe.getAttribute('src');
          expect(src).toContain(`var-region=${encodeURIComponent(secondValue)}`);
        }
      }
    }
  });

  test('Section headings are visible and properly formatted', async ({ page }) => {
    const sections = [
      { id: 'behavior-forecast', title: 'Behavior Forecast' },
      { id: 'live-playground', title: 'Live Playground' },
      { id: 'results-dashboard', title: 'Results Dashboard' },
      { id: 'grafana-analytics', title: 'Analytics Powered by Grafana' },
    ];

    for (const section of sections) {
      const sectionElement = page.locator(`#${section.id}`);
      await expect(sectionElement).toBeVisible();
      const heading = sectionElement.locator('h2').first();
      await expect(heading).toBeVisible();
      await expect(heading).toContainText(section.title);
    }
  });

  test('Dashboard embeds have proper test IDs', async ({ page }) => {
    const dashboardEmbeds = await page.locator('[data-testid^="dashboard-embed-"]').all();
    expect(dashboardEmbeds.length).toBeGreaterThanOrEqual(18);
  });

  test('No console errors on page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    expect(errors.length).toBe(0);
  });

  test('Responsive layout: mobile view stacks to single column', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);

    const grid2Col = page.locator('.dashboard-grid-cols-2');
    const grid4Col = page.locator('.dashboard-grid-cols-4');

    const grid2ColCount = await grid2Col.count();
    const grid4ColCount = await grid4Col.count();

    if (grid2ColCount > 0) {
      const firstGrid = grid2Col.first();
      const computedStyle = await firstGrid.evaluate((el) => {
        return window.getComputedStyle(el).gridTemplateColumns;
      });
      expect(computedStyle).toBe('1fr');
    }

    if (grid4ColCount > 0) {
      const firstGrid = grid4Col.first();
      const computedStyle = await firstGrid.evaluate((el) => {
        return window.getComputedStyle(el).gridTemplateColumns;
      });
      expect(computedStyle).toBe('1fr');
    }
  });

  test('All Grafana iframe URLs are valid and iframes have non-zero dimensions', async ({ page }) => {
    const iframes = await page.locator('iframe[src*="grafana"], iframe[src*="/d/"]').all();
    expect(iframes.length).toBeGreaterThanOrEqual(18);

    for (const iframe of iframes) {
      const src = await iframe.getAttribute('src');
      expect(src).toBeTruthy();
      expect(src).toMatch(/\/d\/[a-z0-9-]+/);

      const box = await iframe.boundingBox();
      expect(box?.height).toBeGreaterThan(100);
      expect(box?.width).toBeGreaterThan(100);
    }
  });
});
