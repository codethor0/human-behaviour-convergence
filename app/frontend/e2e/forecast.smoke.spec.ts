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
      const firstValidOption = options.find(async (opt) => {
        const value = await opt.getAttribute('value');
        return value && value !== '' && value !== 'default';
      }) || options[1];

      const regionValue = await firstValidOption.getAttribute('value');
      if (regionValue) {
        await regionSelect.selectOption(regionValue);
      }

      // Assert button is visible and enabled before clicking
      const generateButton = page.getByTestId('forecast-generate-button');
      await expect(generateButton).toBeVisible({ timeout: 10000 });
      await expect(generateButton).toBeEnabled({ timeout: 30000 });

      // Wait for the POST request AND response to complete
      const responsePromise = page.waitForResponse(
        (response) => {
          const url = response.url();
          return url.includes('/api/forecast') && response.request().method() === 'POST' && response.status() === 200;
        },
        { timeout: 60000 }
      );

      // Click generate button
      await generateButton.click();

    // Wait for response to complete
    const response = await responsePromise;

    // Assertions
    expect(response.request().method()).toBe('POST');
    expect(response.status()).toBe(200);

    // Wait for Quick Summary section to appear and have content (UI updates after response is parsed)
    // The div exists but content only appears when forecastData is set
    await page.waitForFunction(
      () => {
        const summary = document.querySelector('[data-testid="forecast-quick-summary"]');
        if (!summary) return false;
        // Check if content exists (not just the placeholder text)
        const hasContent = summary.textContent &&
          !summary.textContent.includes('Generate a forecast to see summary') &&
          (summary.textContent.includes('Behavior Index') ||
           summary.textContent.includes('Risk Tier') ||
           summary.textContent.includes('Convergence Score'));
        return hasContent;
      },
      { timeout: 30000 }
    );

    // Verify Quick Summary exists and has content
    const quickSummary = page.locator('[data-testid="forecast-quick-summary"]');
    await expect(quickSummary).toBeVisible();

    // Verify at least one metric card exists in Quick Summary
    const metricCards = quickSummary.locator('div').filter({ hasText: /Behavior Index|Risk Tier|Convergence Score|Shock Events/ });
    const cardCount = await metricCards.count();
    expect(cardCount).toBeGreaterThan(0);

    // Verify Sub-Index Breakdown exists (if explanations are present)
    const subIndexBreakdown = page.locator('[data-testid="forecast-subindex-breakdown"]');
    const breakdownExists = await subIndexBreakdown.count() > 0;

    // Sub-Index Breakdown is optional, but if it exists, it should be visible
    if (breakdownExists) {
      await expect(subIndexBreakdown).toBeVisible();
    }

      // Verify button returns to normal state
      await expect(generateButton).not.toBeDisabled();
      await expect(generateButton).toHaveText('Generate Forecast');
    } catch (error) {
      // Capture screenshot on failure for debugging
      await page.screenshot({ path: 'test-results/forecast-fail.png', fullPage: true });
      throw error;
    }
  });
});
