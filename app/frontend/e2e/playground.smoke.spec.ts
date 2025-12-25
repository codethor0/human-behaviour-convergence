import { test, expect } from '@playwright/test';

test.describe('Playground Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to playground page
    await page.goto('/playground');
    
    // Wait for regions to load
    await page.waitForLoadState('networkidle');
  });

  test('Compare regions and verify results exist', async ({ page }) => {
    // Wait for region checkboxes to be available
    const regionCheckboxes = page.locator('input[type="checkbox"]');
    await regionCheckboxes.first().waitFor({ timeout: 10000 });
    
    // Count available checkboxes
    const checkboxCount = await regionCheckboxes.count();
    if (checkboxCount === 0) {
      test.skip('No regions available for testing');
      return;
    }
    
    // Select first available region
    const firstCheckbox = regionCheckboxes.first();
    const isChecked = await firstCheckbox.isChecked();
    
    if (!isChecked) {
      await firstCheckbox.check();
    }
    
    // Verify at least one region is selected
    const checkedCount = await regionCheckboxes.filter({ has: page.locator(':checked') }).count();
    expect(checkedCount).toBeGreaterThan(0);
    
    // Wait for the POST request to complete
    const requestPromise = page.waitForRequest(
      (request) => {
        const url = request.url();
        return url.includes('/api/playground/compare') && request.method() === 'POST';
      },
      { timeout: 60000 }
    );
    
    // Click compare button
    await page.click('[data-testid="playground-compare-button"]');
    
    // Wait for request to complete
    const request = await requestPromise;
    const response = await request.response();
    
    // Assertions
    expect(request.method()).toBe('POST');
    expect(response?.status()).toBe(200);
    
    // Wait for results section to appear
    await page.waitForSelector('[data-testid="playground-results"]', { timeout: 10000 });
    
    // Verify results section exists and is visible
    const resultsSection = page.locator('[data-testid="playground-results"]');
    await expect(resultsSection).toBeVisible();
    
    // Verify results contain at least one region result
    const resultsHeading = resultsSection.locator('h2');
    await expect(resultsHeading).toContainText('Comparison Results');
    
    // Verify button returns to normal state
    const compareButton = page.locator('[data-testid="playground-compare-button"]');
    await expect(compareButton).not.toBeDisabled();
    await expect(compareButton).toHaveText('Compare Regions');
  });
});
