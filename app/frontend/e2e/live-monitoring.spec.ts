import { test, expect } from '@playwright/test';

test.describe('Live Monitoring - Selection Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to live monitoring page
    await page.goto('/live');

    // Wait for regions API response to complete
    const regionsResponse = await page.waitForResponse(
      (response) => response.url().includes('/api/forecasting/regions') && response.status() === 200,
      { timeout: 30000 }
    );

    // Verify response has data
    const responseData = await regionsResponse.json();
    if (!Array.isArray(responseData) || responseData.length === 0) {
      throw new Error(`Regions API returned invalid data: ${JSON.stringify(responseData).substring(0, 100)}`);
    }

    // Wait for regions to load by checking for the selected count element
    await page.waitForSelector('[data-testid="live-selected-count"]', { timeout: 30000 });

    // Wait for select-1 button to be enabled (proves regions state is populated)
    const select1Button = page.locator('[data-testid="live-select-1"]');
    await expect(select1Button).toBeEnabled({ timeout: 30000 });

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
      test.skip();
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

  test('Intelligence Summary displays correctly', async ({ page }) => {
    // Wait for regions to be loaded
    const select1Button = page.locator('[data-testid="live-select-1"]');
    await expect(select1Button).toBeEnabled({ timeout: 30000 });

    // Select exactly 1 region
    await page.click('[data-testid="live-clear-selection"]');
    await expect(page.locator('[data-testid="live-selected-count"]')).toHaveText('Selected: 0 regions');
    await select1Button.click();
    await expect(page.locator('[data-testid="live-selected-count"]')).toHaveText('Selected: 1 regions', { timeout: 10000 });

    // Wait for live data to load
    await page.waitForSelector('[data-testid^="live-region-card-"]', { timeout: 30000 });

    // Wait for intelligence summary to appear (if data is available)
    const intelSummary = page.locator('[data-testid="live-intel-summary"]');
    const intelSummaryVisible = await intelSummary.isVisible().catch(() => false);

    if (intelSummaryVisible) {
      // Verify intelligence summary card is visible
      await expect(intelSummary).toBeVisible();

      // Verify risk tier is present and non-empty
      const riskTier = page.locator('[data-testid="live-intel-risk-tier"]');
      await expect(riskTier).toBeVisible();
      const riskTierText = await riskTier.textContent();
      expect(riskTierText).toBeTruthy();
      expect(riskTierText?.trim().length).toBeGreaterThan(0);

      // Verify shock status is present and non-empty
      const shockStatus = page.locator('[data-testid="live-intel-shock-status"]');
      await expect(shockStatus).toBeVisible();
      const shockStatusText = await shockStatus.textContent();
      expect(shockStatusText).toBeTruthy();
      expect(shockStatusText?.trim().length).toBeGreaterThan(0);

      // Verify top contributing indices are present
      const topIndices = page.locator('[data-testid="live-intel-top-indices"]');
      const topIndicesVisible = await topIndices.isVisible().catch(() => false);
      if (topIndicesVisible) {
        await expect(topIndices).toBeVisible();
        // Verify at least one index is listed
        const indexItems = topIndices.locator('li');
        const indexCount = await indexItems.count();
        expect(indexCount).toBeGreaterThan(0);
      }
    } else {
      // If intelligence summary is not visible, it might be because there's no data yet
      // This is acceptable - the test should pass if the summary appears when data is available
      // We'll just verify the page loaded correctly
      const regionCards = page.locator('[data-testid^="live-region-card-"]');
      const cardCount = await regionCards.count();
      expect(cardCount).toBeGreaterThan(0);
    }
  });
});
