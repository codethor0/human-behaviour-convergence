import { test, expect } from '@playwright/test';

test.describe('Live Monitoring - Selection Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to live monitoring page
    await page.goto('/live');
    
    // Wait for regions to load by checking for the selected count element
    // This element only appears when regions have loaded successfully
    await page.waitForSelector('[data-testid="live-selected-count"]', { timeout: 30000 });
    
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
    
    // Wait for initial data fetch to complete
    await page.waitForLoadState('networkidle');
  });

  test('Test 4: Exactly 1 region selection', async ({ page }) => {
    // Wait for regions to be loaded - wait for select-1 button to be enabled (proves regions state is populated)
    const select1Button = page.locator('[data-testid="live-select-1"]');
    await expect(select1Button).toBeEnabled({ timeout: 30000 });
    
    // Verify checkboxes exist
    const checkboxes = page.locator('input[type="checkbox"]');
    const checkboxCount = await checkboxes.count();
    if (checkboxCount === 0) {
      throw new Error('No regions available - regions failed to load');
    }
    
    // Clear all selections
    await page.click('[data-testid="live-clear-selection"]');
    await expect(page.locator('[data-testid="live-selected-count"]')).toHaveText('Selected: 0 regions');
    // Select exactly 1 region
    await select1Button.click();
    // Wait for state to update (React state update is async)
    await expect(page.locator('[data-testid="live-selected-count"]')).toHaveText('Selected: 1 regions', { timeout: 10000 });
    
    // Wait for the request and capture it
    const requestPromise = page.waitForRequest(
      (request) => {
        const url = request.url();
        return url.includes('/api/live/summary') && request.method() === 'GET';
      },
      { timeout: 10000 }
    );
    
    // Click refresh
    await page.click('[data-testid="live-refresh"]');
    
    // Wait for request to complete
    const request = await requestPromise;
    const url = new URL(request.url());
    const regionsParams = url.searchParams.getAll('regions');
    
    // Assertions
    expect(request.method()).toBe('GET');
    const response = await request.response();
    expect(response?.status()).toBe(200);
    expect(regionsParams.length).toBe(1);
    
    // Wait for UI to update
    await page.waitForSelector('[data-testid^="live-region-card-"]', { timeout: 5000 });
    
    // Count region cards
    const regionCards = page.locator('[data-testid^="live-region-card-"]');
    const cardCount = await regionCards.count();
    
    expect(cardCount).toBe(1);
    
    // Verify the card shows the correct region ID
    const firstCard = regionCards.first();
    const cardTestId = await firstCard.getAttribute('data-testid');
    const regionId = cardTestId?.replace('live-region-card-', '');
    expect(regionId).toBe(regionsParams[0]);
  });

  test('Test 5: Exactly 3 regions selection', async ({ page }) => {
    // Wait for regions to be loaded (checkboxes must exist)
    await page.waitForSelector('input[type="checkbox"]', { timeout: 30000 });
    const checkboxes = page.locator('input[type="checkbox"]');
    const checkboxCount = await checkboxes.count();
    if (checkboxCount < 3) {
      throw new Error(`Only ${checkboxCount} regions available, need at least 3`);
    }
    
    // Clear all selections
    await page.click('[data-testid="live-clear-selection"]');
    await expect(page.locator('[data-testid="live-selected-count"]')).toHaveText('Selected: 0 regions');
    
    // Select exactly 3 regions (skip if not enough regions available)
    if (checkboxCount < 3) {
      test.skip(`Only ${checkboxCount} regions available, need at least 3`);
      return;
    }
    // Wait for select-3 button to be enabled (regions loaded)
    const select3Button = page.locator('[data-testid="live-select-3"]');
    await expect(select3Button).toBeEnabled({ timeout: 30000 });
    await select3Button.click();
    // Wait for state to update (React state update is async)
    await expect(page.locator('[data-testid="live-selected-count"]')).toHaveText('Selected: 3 regions', { timeout: 10000 });
    
    // Wait for the request and capture it
    const requestPromise = page.waitForRequest(
      (request) => {
        const url = request.url();
        return url.includes('/api/live/summary') && request.method() === 'GET';
      },
      { timeout: 10000 }
    );
    
    // Click refresh
    await page.click('[data-testid="live-refresh"]');
    
    // Wait for request to complete
    const request = await requestPromise;
    const url = new URL(request.url());
    const regionsParams = url.searchParams.getAll('regions');
    
    // Assertions
    expect(request.method()).toBe('GET');
    const response = await request.response();
    expect(response?.status()).toBe(200);
    expect(regionsParams.length).toBe(3);
    
    // Wait for UI to update
    await page.waitForSelector('[data-testid^="live-region-card-"]', { timeout: 5000 });
    
    // Count region cards
    const regionCards = page.locator('[data-testid^="live-region-card-"]');
    const cardCount = await regionCards.count();
    
    expect(cardCount).toBe(3);
    
    // Verify all 3 region IDs match
    const cardTestIds: string[] = [];
    for (let i = 0; i < 3; i++) {
      const card = regionCards.nth(i);
      const testId = await card.getAttribute('data-testid');
      if (testId) {
        cardTestIds.push(testId.replace('live-region-card-', ''));
      }
    }
    
    // Verify all selected regions are rendered
    regionsParams.forEach((regionId) => {
      expect(cardTestIds).toContain(regionId);
    });
  });
});
