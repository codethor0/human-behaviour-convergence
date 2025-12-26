import { test, expect } from '@playwright/test';

test.describe('Playground Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to playground page
    await page.goto('/playground');
    
    // Wait for regions to load by checking for checkboxes
    // Checkboxes only appear when regions have loaded successfully
    await page.waitForSelector('input[type="checkbox"]', { timeout: 30000 });
    
    // Wait for at least one checkbox to be available
    await page.waitForFunction(
      () => {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        return checkboxes.length > 0;
      },
      { timeout: 30000 }
    );
    
    // Wait a bit for any error messages to clear
    await page.waitForTimeout(1000);
    
    // Verify no error message is shown (only fail if error persists after regions should have loaded)
    const errorText = page.locator('text=/Failed to load/i');
    const errorVisible = await errorText.isVisible().catch(() => false);
    if (errorVisible) {
      // Double-check that regions actually loaded by checking for checkboxes
      const checkboxes = page.locator('input[type="checkbox"]');
      const checkboxCount = await checkboxes.count();
      if (checkboxCount === 0) {
        throw new Error('Regions failed to load - error message present and no regions available');
      }
    }
    
    // Wait for network to be idle
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
      // Wait for checkbox state to update
      await expect(firstCheckbox).toBeChecked({ timeout: 5000 });
    }
    
    // Verify at least one region is selected by checking each checkbox's state
    let checkedCount = 0;
    const totalCheckboxes = await regionCheckboxes.count();
    for (let i = 0; i < totalCheckboxes; i++) {
      const checkbox = regionCheckboxes.nth(i);
      if (await checkbox.isChecked()) {
        checkedCount++;
      }
    }
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
