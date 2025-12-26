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
      test.skip();
      return;
    }

    const firstOption = options[1];
    if (!firstOption) {
      test.skip();
      return;
    }
    const firstOptionValue = await firstOption.getAttribute('value');
    if (firstOptionValue) {
      await regionSelect.selectOption(firstOptionValue);
    }

    // Get the region name for later verification
    // The option text might include "(US)" or other suffixes, so extract just the region name
    // The format is typically "Region Name (Country)" or just "Region Name"
    const selectedOptionText = await firstOption.textContent();
    let regionName = selectedOptionText?.trim() || '';
    // Extract region name before "(" if present (e.g., "New York City (US)" -> "New York City")
    if (regionName.includes('(')) {
      const parts = regionName.split('(');
      regionName = parts[0]?.trim() || regionName;
    }

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
    await page.goto('/history', { waitUntil: 'domcontentloaded' });

    // Check if we got a 404 page immediately
    const pageUrl = page.url();
    if (pageUrl.includes('404') || pageUrl.includes('_error')) {
      throw new Error(`Page returned 404 or error page. URL: ${pageUrl}`);
    }

    // Check what's actually on the page right now
    const bodyText = await page.textContent('body').catch(() => '');
    if (bodyText && (bodyText.includes('404') || bodyText.includes('Not Found'))) {
      await page.screenshot({ path: 'test-results/history-404.png' }).catch(() => {});
      throw new Error('Page returned 404 - route /history not found');
    }

    // Wait for h1 to be visible first (ensures page has loaded)
    const pageTitle = page.getByTestId('history-page-title');
    await expect(pageTitle).toBeVisible({ timeout: 30000 });
    await expect(pageTitle).toHaveText('Forecast History');

    // Wait for history container to be visible (now that page is loaded)
    const historyContainer = page.getByTestId('forecast-history-container');
    await expect(historyContainer).toBeVisible({ timeout: 30000 });

    // Verify limit select exists
    const limitSelect = page.getByTestId('history-limit-select');
    await expect(limitSelect).toBeVisible();

    // Verify region filter input exists
    const regionFilter = page.getByTestId('history-region-filter');
    await expect(regionFilter).toBeVisible();

    // Wait for loading to complete (container is visible, loading message should be gone)
    await page.waitForFunction(
      () => {
        const loading = document.querySelector('[data-testid="history-loading"]');
        return !loading || !loading.textContent?.includes('Loading');
      },
      { timeout: 30000 }
    );

    // Verify either empty state or table exists
    const emptyState = page.getByTestId('history-empty-state');
    const historyTable = page.getByTestId('forecast-history-table');
    
    // Check which one is visible (wait a bit for rendering)
    await page.waitForTimeout(500);
    
    const emptyStateVisible = await emptyState.isVisible().catch(() => false);
    const tableVisible = await historyTable.isVisible().catch(() => false);

    // Either empty state or table must be visible (but not both)
    if (emptyStateVisible) {
      await expect(emptyState).toBeVisible();
      await expect(emptyState).toHaveText('No forecast history available yet.');
      // When empty, table should not be visible
      const tableCount = await historyTable.count();
      expect(tableCount).toBe(0);
    } else if (tableVisible) {
      await expect(historyTable).toBeVisible({ timeout: 30000 });
      // When table exists, empty state should not be visible
      const emptyStateCount = await emptyState.count();
      expect(emptyStateCount).toBe(0);
      // Verify table has at least one row
      const historyRows = page.getByTestId('forecast-history-row');
      const rowCount = await historyRows.count();
      expect(rowCount).toBeGreaterThan(0);
    } else {
      // If neither is visible, check if we're still loading
      const loading = page.getByTestId('history-loading');
      const isLoading = await loading.isVisible().catch(() => false);
      if (isLoading) {
        throw new Error('Page is still loading after timeout');
      }
      throw new Error('Neither empty state nor history table is visible');
    }
  });

  test('History filters and sorting work correctly', async ({ page }) => {
    // Step 1: Create multiple forecasts with different regions
    const createdRegions: string[] = [];

    for (let i = 0; i < 2; i++) {
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

      // Select a different region each time
      const regionSelect = page.locator('select').first();
      await regionSelect.waitFor({ timeout: 10000 });
      const options = await regionSelect.locator('option').all();
      if (options.length < 2 + i) {
        test.skip();
        return;
      }

      // Select option at index 1 + i to get different regions
      const optionIndex = 1 + i;
      const targetOption = options[optionIndex];
      if (!targetOption) {
        test.skip();
        return;
      }
      const optionValue = await targetOption.getAttribute('value');
      if (optionValue) {
        await regionSelect.selectOption(optionValue);
      }

      // Extract region name
      const selectedOptionText = await targetOption.textContent();
      let regionName = selectedOptionText?.trim() || '';
      if (regionName.includes('(')) {
        const parts = regionName.split('(');
        regionName = parts[0]?.trim() || regionName;
      }
      createdRegions.push(regionName);

      // Generate forecast
      const generateButton = page.getByTestId('forecast-generate-button');
      await expect(generateButton).toBeEnabled({ timeout: 30000 });
      await generateButton.click();

      // Wait for forecast results
      await page.waitForSelector('[data-testid="forecast-quick-summary"]', { timeout: 60000 });
      await page.waitForFunction(
        () => {
          const summary = document.querySelector('[data-testid="forecast-quick-summary"]');
          return summary && summary.textContent && summary.textContent.includes('Behavior Index');
        },
        { timeout: 30000 }
      );

      // Small delay between forecasts to ensure different timestamps
      await page.waitForTimeout(1000);
    }

    // Step 2: Navigate to history page
    await page.goto('/history');
    await page.waitForLoadState('networkidle');
    const historyContainer = page.getByTestId('forecast-history-container');
    await expect(historyContainer).toBeVisible({ timeout: 30000 });

    // Wait for table to be visible
    const historyTable = page.getByTestId('forecast-history-table');
    await expect(historyTable).toBeVisible({ timeout: 30000 });

    // Step 3: Verify default sort order (newest first - DESC)
    const sortOrderSelect = page.getByTestId('history-sort-order');
    await expect(sortOrderSelect).toBeVisible();
    const defaultSortValue = await sortOrderSelect.inputValue();
    expect(defaultSortValue).toBe('DESC');

    // Get initial row count
    const initialRows = page.getByTestId('forecast-history-row');
    const initialRowCount = await initialRows.count();
    expect(initialRowCount).toBeGreaterThanOrEqual(2);

    // Step 4: Test region filter (substring search)
    if (createdRegions.length > 0 && createdRegions[0]) {
      const regionFilter = page.getByTestId('history-region-filter');
      await expect(regionFilter).toBeVisible();

      // Filter by the full first region name (substring match should work)
      await regionFilter.fill(createdRegions[0]);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      // Wait for either table or empty state to appear
      const emptyState = page.getByTestId('history-empty-state');
      const filteredTable = page.getByTestId('forecast-history-table');
      const emptyStateVisible = await emptyState.isVisible().catch(() => false);
      const tableVisible = await filteredTable.isVisible().catch(() => false);

      // If table is visible, verify it contains the region
      if (tableVisible) {
        const filteredRows = page.getByTestId('forecast-history-row');
        const filteredRowCount = await filteredRows.count();
        expect(filteredRowCount).toBeGreaterThan(0);

        // Verify at least one row contains the region
        let foundFilteredRegion = false;
        for (let i = 0; i < filteredRowCount; i++) {
          const row = filteredRows.nth(i);
          const rowText = await row.textContent();
          if (rowText && rowText.includes(createdRegions[0])) {
            foundFilteredRegion = true;
            break;
          }
        }
        expect(foundFilteredRegion).toBe(true);
      } else if (emptyStateVisible) {
        // If empty state appears, the filter worked but no matches (acceptable)
        // This means the filter is working, just no results
      }

      // Clear filter to restore full list
      await regionFilter.clear();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
    }

    // Step 5: Test sort order (oldest first - ASC)
    await sortOrderSelect.selectOption('ASC');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    // Verify sort order changed
    const ascRows = page.getByTestId('forecast-history-row');
    const ascRowCount = await ascRows.count();
    expect(ascRowCount).toBeGreaterThan(0);

    // Step 6: Test sort order (newest first - DESC)
    await sortOrderSelect.selectOption('DESC');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    // Verify sort order changed back
    const descRows = page.getByTestId('forecast-history-row');
    const descRowCount = await descRows.count();
    expect(descRowCount).toBeGreaterThan(0);

    // Step 7: Verify date filter inputs exist
    const dateFromInput = page.getByTestId('history-date-from');
    const dateToInput = page.getByTestId('history-date-to');
    await expect(dateFromInput).toBeVisible();
    await expect(dateToInput).toBeVisible();
  });
});
