import { test, expect } from '@playwright/test';

test.describe('Live Monitoring - Selection Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to live monitoring page
    await page.goto('/live');
    
    // Wait for regions to load
    await page.waitForSelector('[data-testid="live-selected-count"]', { timeout: 10000 });
    
    // Wait for initial data fetch to complete
    await page.waitForLoadState('networkidle');
  });

  test('Test 4: Exactly 1 region selection', async ({ page }) => {
    // Clear all selections
    await page.click('[data-testid="live-clear-selection"]');
    await expect(page.locator('[data-testid="live-selected-count"]')).toHaveText('Selected: 0');
    
    // Select exactly 1 region
    await page.click('[data-testid="live-select-1"]');
    await expect(page.locator('[data-testid="live-selected-count"]')).toHaveText('Selected: 1');
    
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
    // Clear all selections
    await page.click('[data-testid="live-clear-selection"]');
    await expect(page.locator('[data-testid="live-selected-count"]')).toHaveText('Selected: 0');
    
    // Select exactly 3 regions
    await page.click('[data-testid="live-select-3"]');
    await expect(page.locator('[data-testid="live-selected-count"]')).toHaveText('Selected: 3');
    
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
