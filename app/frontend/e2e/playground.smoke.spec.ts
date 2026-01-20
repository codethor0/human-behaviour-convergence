import { test, expect } from '@playwright/test';

test.describe('Playground Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to playground page
    await page.goto('/playground');

    // Wait for region dropdown to be populated
    // The select element is always present, but initially shows "Loading regions..."
    const regionSelect = page.locator('select[aria-label="Select region for playground"]');
    await regionSelect.waitFor({ state: 'visible', timeout: 60000 });

    // Wait for regions to actually load by checking that we have real options (not just "Loading...")
    await page.waitForFunction(
      () => {
        const select = document.querySelector('select[aria-label="Select region for playground"]') as HTMLSelectElement;
        if (!select) return false;
        const options = Array.from(select.options);
        // Check if we have options that aren't loading/error states
        return options.some(opt => opt.value && !opt.text.includes('Loading') && !opt.text.includes('Error'));
      },
      { timeout: 60000 }
    );

    // Small delay for stability
    await page.waitForTimeout(2000);
  });

  test('Region selection and Grafana dashboard embedding', async ({ page }) => {
    // Verify page title/heading
    await expect(page.locator('text=/Live Playground/i')).toBeVisible();
    await expect(page.locator('text=/Interactive Analytics Playground/i')).toBeVisible();

    // Verify region dropdown is functional
    const regionSelect = page.locator('select[aria-label="Select region for playground"]');
    await expect(regionSelect).toBeEnabled();

    // Get the current selected value
    const initialRegion = await regionSelect.inputValue();
    expect(initialRegion).toBeTruthy(); // Should have a default region selected

    // Verify region selection displays correctly
    await expect(page.locator('text=/Selected:/i')).toBeVisible();

    // Verify both Grafana dashboards are embedded
    const iframes = page.locator('iframe');
    const iframeCount = await iframes.count();
    expect(iframeCount).toBeGreaterThanOrEqual(2); // At least 2 dashboards

    // Verify the dashboard titles
    await expect(page.locator('text=/Behavior Index - Regional View/i')).toBeVisible();
    await expect(page.locator('text=/Sub-Index Analysis - Deep Dive/i')).toBeVisible();

    // Verify iframe src contains expected dashboard UIDs
    const firstIframe = iframes.first();
    const firstSrc = await firstIframe.getAttribute('src');
    expect(firstSrc).toContain('behavior-index-global');

    const secondIframe = iframes.nth(1);
    const secondSrc = await secondIframe.getAttribute('src');
    expect(secondSrc).toContain('subindex-deep-dive');

    // Verify iframes contain region parameter
    expect(firstSrc).toContain('var-region=');
    expect(secondSrc).toContain('var-region=');

    // Try changing region (if we have multiple options)
    const optionCount = await regionSelect.locator('option').count();
    if (optionCount > 1) {
      // Get the second option value
      const secondOption = regionSelect.locator('option').nth(1);
      const secondValue = await secondOption.getAttribute('value');
      
      if (secondValue) {
        // Select a different region
        await regionSelect.selectOption(secondValue);
        await page.waitForTimeout(1000);

        // Verify the iframe src updated with new region
        const updatedIframeSrc = await iframes.first().getAttribute('src');
        expect(updatedIframeSrc).toContain(`var-region=${secondValue}`);
      }
    }
  });
});
