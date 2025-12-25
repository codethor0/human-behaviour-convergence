import { test, expect } from '@playwright/test';

test.describe('Forecast Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to forecast page
    await page.goto('/forecast');
    
    // Wait for regions API response (backend contract)
    await page.waitForResponse(
      (response) => response.url().includes('/api/forecasting/regions') && response.status() === 200,
      { timeout: 30000 }
    );
    
    // Wait for network to be idle
    await page.waitForLoadState('networkidle');
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
      
      // Wait for the POST request to complete
      const requestPromise = page.waitForRequest(
        (request) => {
          const url = request.url();
          return url.includes('/api/forecast') && request.method() === 'POST';
        },
        { timeout: 60000 }
      );
      
      // Click generate button
      await generateButton.click();
    
    // Wait for request to complete
    const request = await requestPromise;
    const response = await request.response();
    
    // Assertions
    expect(request.method()).toBe('POST');
    expect(response?.status()).toBe(200);
    
    // Wait for Quick Summary section to appear
    await page.waitForSelector('[data-testid="forecast-quick-summary"]', { timeout: 10000 });
    
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
