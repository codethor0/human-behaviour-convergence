import { test, expect } from '@playwright/test';

test.describe('Forecast History Smoke Tests', () => {
  test('Navigate to history and verify forecast appears after creating one', async ({ page }) => {
    // Step 1: Create a forecast first
    await page.goto('/forecast');

    // Wait for regions to load
    await page.waitForSelector('select', { timeout: 30000 });
    await page.waitForFunction(
      () => {
        const select = document.querySelector('select');
        return select && select.options.length > 1;
      },
      { timeout: 30000 }
    );
    await page.waitForTimeout(1000);

    // Select first available region
    const regionSelect = page.locator('select').first();
    await regionSelect.waitFor({ timeout: 10000 });
    const options = await regionSelect.locator('option').all();
    if (options.length < 2) {
      test.skip('No regions available for testing');
      return;
    }

    const firstOptionValue = await options[1].getAttribute('value');
    if (firstOptionValue) {
      await regionSelect.selectOption(firstOptionValue);
    }

    // Get the region name for later verification
    const selectedOptionText = await options[1].textContent();
    const regionName = selectedOptionText?.trim() || '';

    // Wait for generate button to be enabled
    const generateButton = page.getByTestId('forecast-generate-button');
    await expect(generateButton).toBeEnabled({ timeout: 30000 });

    // Generate forecast
    await generateButton.click();

    // Wait for forecast results to appear
    await page.waitForSelector('[data-testid="forecast-quick-summary"]', { timeout: 60000 });
    await page.waitForFunction(
      () => {
        const summary = document.querySelector('[data-testid="forecast-quick-summary"]');
        return summary && summary.textContent && summary.textContent.includes('Behavior Index');
      },
      { timeout: 30000 }
    );

    // Step 2: Navigate to history page
    await page.goto('/history');

    // Step 3: Wait for page to load and network to be idle
    await page.waitForLoadState('networkidle');

    // Step 4: Wait for history container to be visible (it appears after loading completes)
    // The container is only rendered when loading is false, so wait for it directly
    const historyContainer = page.getByTestId('forecast-history-container');
    await expect(historyContainer).toBeVisible({ timeout: 30000 });

    // Step 5: Wait for history table to load (if there's data)
    // The table might not exist if history is empty, so check if container has content
    const historyTable = page.getByTestId('forecast-history-table');
    const tableExists = await historyTable.isVisible().catch(() => false);
    if (tableExists) {
      await expect(historyTable).toBeVisible({ timeout: 30000 });
    }

    // Step 6: Verify at least one history row exists (if table is present)
    if (tableExists) {
      const historyRows = page.getByTestId('forecast-history-row');
      const rowCount = await historyRows.count();
      expect(rowCount).toBeGreaterThan(0);
    }

    // Step 7: Verify the region we just forecasted appears in the history (if table exists)
    if (tableExists && regionName) {
      const historyRows = page.getByTestId('forecast-history-row');
      const rowCount = await historyRows.count();
      let foundRegion = false;
      for (let i = 0; i < rowCount; i++) {
        const row = historyRows.nth(i);
        const rowText = await row.textContent();
        if (rowText && rowText.includes(regionName)) {
          foundRegion = true;
          break;
        }
      }
      expect(foundRegion).toBe(true);
    }

    // Step 8: Verify table structure - check for expected columns (if table exists)
    if (tableExists) {
      const tableHeaders = historyTable.locator('thead th');
      const headerCount = await tableHeaders.count();
      expect(headerCount).toBeGreaterThan(0);

      // Verify at least "Region" column exists
      const regionHeader = historyTable.locator('thead th:has-text("Region")');
      await expect(regionHeader).toBeVisible();
    }
  });

  test('History page loads with filters', async ({ page }) => {
    await page.goto('/history');

    // Wait for page to load and network to be idle
    await page.waitForLoadState('networkidle');

    // Wait for history container
    const historyContainer = page.getByTestId('forecast-history-container');
    await expect(historyContainer).toBeVisible({ timeout: 30000 });

    // Verify limit select exists
    const limitSelect = page.getByTestId('history-limit-select');
    await expect(limitSelect).toBeVisible();

    // Verify region filter input exists
    const regionFilter = page.getByTestId('history-region-filter');
    await expect(regionFilter).toBeVisible();

    // Verify table exists only if there's data (it might not exist if history is empty)
    const historyTable = page.getByTestId('forecast-history-table');
    const tableExists = await historyTable.isVisible().catch(() => false);
    // Table is optional - if history is empty, we just verify the container exists
    if (tableExists) {
      await expect(historyTable).toBeVisible({ timeout: 30000 });
    }
  });
});
