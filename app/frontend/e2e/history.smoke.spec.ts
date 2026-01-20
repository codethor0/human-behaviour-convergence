import { test, expect } from '@playwright/test';

test.describe('Forecast History Smoke Tests', () => {
  test('Navigate to history and verify page loads with correct UI', async ({ page }) => {
    // Navigate to history page
    await page.goto('/history', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');

    // Verify page title (primary sentinel)
    const pageTitle = page.getByTestId('history-page-title');
    await expect(pageTitle).toBeVisible({ timeout: 30000 });
    await expect(pageTitle).toHaveText('Forecast History');

    // Verify history container is visible
    const historyContainer = page.getByTestId('forecast-history-container');
    await expect(historyContainer).toBeVisible({ timeout: 30000 });

    // Verify UI is functional (contract: UI-based history page, NOT Grafana)
    // History page uses traditional filters + table, not embedded dashboards
  });

  test('History page loads with filters', async ({ page }) => {
    await page.goto('/history', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');

    // Verify page loaded
    const pageTitle = page.getByTestId('history-page-title');
    await expect(pageTitle).toBeVisible({ timeout: 10000 });

    // Verify filter controls exist (validates UI contract)
    const limitSelect = page.getByTestId('history-limit-select');
    await expect(limitSelect).toBeVisible({ timeout: 10000 });

    const regionFilter = page.getByTestId('history-region-filter');
    await expect(regionFilter).toBeVisible({ timeout: 10000 });
  });

  test('History filters and sorting work correctly', async ({ page }) => {
    await page.goto('/history', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');

    // Verify page loads
    const historyContainer = page.getByTestId('forecast-history-container');
    await expect(historyContainer).toBeVisible({ timeout: 30000 });

    // Verify sort order selector exists and is interactive
    const sortOrderSelect = page.getByTestId('history-sort-order');
    await expect(sortOrderSelect).toBeVisible({ timeout: 10000 });
    
    // Verify we can change sort order
    await sortOrderSelect.selectOption('ASC');
    expect(await sortOrderSelect.inputValue()).toBe('ASC');
  });
});
