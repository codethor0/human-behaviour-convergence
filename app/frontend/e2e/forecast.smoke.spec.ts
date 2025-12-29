import { test, expect } from '@playwright/test';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8100';

async function waitForRegionsReady(request: any) {
  const url = `${API_BASE}/api/forecasting/regions`;
  const started = Date.now();
  let lastErr = '';
  while (Date.now() - started < 60_000) {
    try {
      const res = await request.get(url, { timeout: 10_000 });
      const status = res.status();
      if (status === 200) {
        const json = await res.json().catch(() => null);
        if (Array.isArray(json) && json.length > 0) return;
        lastErr = `regions shape invalid: ${JSON.stringify(json)?.slice(0,200)}`;
      } else {
        lastErr = `regions status=${status}`;
      }
    } catch (e: any) {
      lastErr = `regions request error: ${String(e).slice(0,200)}`;
    }
    await new Promise(r => setTimeout(r, 1000));
  }
  throw new Error(`Backend not ready: ${lastErr}`);
}

test.describe('Forecast Smoke Tests', () => {
  test.beforeEach(async ({ page, request }) => {
    // Wait for backend to be ready before navigating
    await waitForRegionsReady(request);
    
    // Instrument page to capture browser-side errors
    const apiFailures: string[] = [];
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    
    page.on('pageerror', (err) => {
      pageErrors.push(String(err));
    });
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    
    const failedRequests = new Set<string>();
    
    page.on('requestfailed', (req) => {
      const url = req.url();
      if (!failedRequests.has(url)) {
        failedRequests.add(url);
        apiFailures.push(`REQUEST_FAILED ${url} :: ${req.failure()?.errorText || ''}`);
      }
    });
    
    page.on('response', async (res) => {
      try {
        const url = res.url();
        const status = res.status();
        if (status === 404) {
          // Capture all 404s (not just /api/) to identify missing resources
          if (!failedRequests.has(url)) {
            failedRequests.add(url);
            // Don't await text() to avoid blocking - just capture URL
            apiFailures.push(`404 ${url}`);
          }
        } else if (status >= 400 && url.includes('/api/')) {
          // Capture other API failures
          const body = (await res.text().catch(() => '')).slice(0, 400);
          apiFailures.push(`${status} ${url} :: ${body}`);
        }
      } catch {}
    });
    
    // Navigate to forecast page
    await page.goto('/forecast');
    
    // Wait for select element to exist first (may show "Loading regions..." initially)
    try {
      await page.waitForSelector('select', { timeout: 30_000 });
      
      // Wait for "Loading regions..." text to disappear (if it exists)
      const loadingText = page.getByText('Loading regions...');
      const loadingExists = await loadingText.isVisible().catch(() => false);
      if (loadingExists) {
        await expect(loadingText).toHaveCount(0, { timeout: 30_000 });
      }
      
      // Wait for select to be visible
      await expect(page.locator('select')).toBeVisible({ timeout: 30_000 });
      
      // Wait for at least one option in the select (proves regions loaded)
      await page.waitForFunction(
        () => {
          const select = document.querySelector('select');
          return select && select.options.length > 1;
        },
        { timeout: 30000 }
      );
    } catch (error) {
      // Emit diagnostics before failing
      const diag = [
        `ConsoleErrors(${consoleErrors.length}): ${consoleErrors.slice(0,5).join(' | ')}`,
        `PageErrors(${pageErrors.length}): ${pageErrors.slice(0,5).join(' | ')}`,
        `ApiFailures(${apiFailures.length}): ${apiFailures.slice(0,10).join(' | ')}`
      ].join('\n');
      
      console.error(`DOCKER_E2E_DIAGNOSTICS\n${diag}`);
      throw error;
    }
    
    // Verify regions API call completed successfully by checking network response
    const regionsResponse = await page.waitForResponse(
      (response) => response.url().includes('/api/forecasting/regions') && response.status() === 200,
      { timeout: 30_000 }
    ).catch(async () => {
      // On failure, capture diagnostic info
      const response = await page.request.get(`${API_BASE}/api/forecasting/regions`).catch(() => null);
      if (response) {
        const status = response.status();
        const body = await response.text().catch(() => '');
        throw new Error(`Regions API failed: status=${status} body=${body.slice(0, 200)}`);
      }
      throw new Error('Regions API request failed or timed out');
    });
    
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
      
      // Wait for the POST request AND response to complete
      const responsePromise = page.waitForResponse(
        (response) => {
          const url = response.url();
          return url.includes('/api/forecast') && response.request().method() === 'POST' && response.status() === 200;
        },
        { timeout: 60000 }
      );
      
      // Click generate button
      await generateButton.click();
    
    // Wait for response to complete
    const response = await responsePromise;
    
    // Assertions
    expect(response.request().method()).toBe('POST');
    expect(response.status()).toBe(200);
    
    // Wait for Quick Summary section to appear and have content (UI updates after response is parsed)
    // The div exists but content only appears when forecastData is set
    await page.waitForFunction(
      () => {
        const summary = document.querySelector('[data-testid="forecast-quick-summary"]');
        if (!summary) return false;
        // Check if content exists (not just the placeholder text)
        const hasContent = summary.textContent && 
          !summary.textContent.includes('Generate a forecast to see summary') &&
          (summary.textContent.includes('Behavior Index') || 
           summary.textContent.includes('Risk Tier') ||
           summary.textContent.includes('Convergence Score'));
        return hasContent;
      },
      { timeout: 30000 }
    );
    
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
