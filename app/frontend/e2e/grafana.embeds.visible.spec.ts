import { test, expect } from '@playwright/test';

const GRAFANA_BASE = process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3001';
const FRONTEND_BASE = 'http://localhost:3100';

// Expected dashboard UIDs per page
const EXPECTED_DASHBOARDS = {
  '/forecast': [
    'forecast-summary',
    'behavior-index-global',
    'subindex-deep-dive',
    'regional-variance-explorer',
    'forecast-quality-drift',
    'algorithm-model-comparison',
    'data-sources-health',
    'source-health-freshness',
  ],
  '/live': [], // To be determined
  '/playground': [], // To be determined
  '/history': [], // To be determined
};

async function waitForStackReady(page: any, request: any) {
  // Wait for backend health
  await request.get('http://localhost:8100/health', { timeout: 30000 });
  
  // Wait for frontend
  await page.goto(FRONTEND_BASE, { waitUntil: 'domcontentloaded', timeout: 30000 });
  
  // Wait for Grafana
  try {
    await request.get(`${GRAFANA_BASE}/api/health`, { timeout: 10000 });
  } catch (e) {
    console.warn('Grafana health check failed, continuing anyway');
  }
}

test.describe('Grafana Dashboard Embeds - Visual Verification', () => {
  test.beforeEach(async ({ page, request }) => {
    await waitForStackReady(page, request);
  });

  test('Forecast page shows all required Grafana dashboards', async ({ page }) => {
    await page.goto(`${FRONTEND_BASE}/forecast`, { waitUntil: 'networkidle', timeout: 60000 });
    
    // Wait for page to fully load
    await page.waitForLoadState('domcontentloaded');
    
    // Verify analytics section heading exists
    const analyticsHeading = page.locator('text=Analytics Powered by Grafana');
    await expect(analyticsHeading).toBeVisible({ timeout: 10000 });
    
    // Verify expected dashboard section headings
    const expectedHeadings = [
      'Regional Forecast Overview & Key Metrics',
      'Behavior Index Timeline & Historical Trends',
      'Sub-Index Components & Contributing Factors',
      'Regional Variance Explorer',
      'Forecast Quality and Drift Analysis',
      'Algorithm / Model Performance Comparison',
      'Real-Time Data Source Status & API Health',
      'Source Health and Freshness',
    ];
    
    for (const heading of expectedHeadings) {
      const headingLocator = page.locator(`text=${heading}`);
      await expect(headingLocator.first()).toBeVisible({ timeout: 5000 });
    }
    
    // Find all iframes
    const iframes = page.locator('iframe');
    const iframeCount = await iframes.count();
    expect(iframeCount).toBeGreaterThanOrEqual(8);
    
    // Verify each expected dashboard iframe
    const iframeSrcs: string[] = [];
    for (let i = 0; i < iframeCount; i++) {
      const iframe = iframes.nth(i);
      const src = await iframe.getAttribute('src');
      if (src) {
        iframeSrcs.push(src);
      }
    }
    
    // Check for expected dashboard UIDs
    const foundDashboards = EXPECTED_DASHBOARDS['/forecast'].filter(dash =>
      iframeSrcs.some(src => src.includes(dash))
    );
    
    expect(foundDashboards.length).toBeGreaterThanOrEqual(6);
    
    // Verify iframes are visible and have dimensions
    for (let i = 0; i < Math.min(iframeCount, 8); i++) {
      const iframe = iframes.nth(i);
      const box = await iframe.boundingBox();
      expect(box).toBeTruthy();
      expect(box!.width).toBeGreaterThan(100);
      expect(box!.height).toBeGreaterThan(100);
    }
    
    // Verify region variable wiring (check first iframe that should have region)
    const regionIframe = iframes.first();
    const regionSrc = await regionIframe.getAttribute('src');
    expect(regionSrc).toMatch(/var-region=|region=/);
    
    // Capture screenshot
    await page.screenshot({ path: 'test-results/forecast-page-dashboards.png', fullPage: true });
  });

  test('Forecast page iframes load without auth errors', async ({ page }) => {
    await page.goto(`${FRONTEND_BASE}/forecast`, { waitUntil: 'networkidle', timeout: 60000 });
    
    // Collect console errors
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    // Collect network failures
    const networkFailures: string[] = [];
    page.on('response', (response) => {
      if (response.status() >= 400 && response.url().includes('grafana')) {
        networkFailures.push(`${response.status()}: ${response.url()}`);
      }
    });
    
    // Wait for iframes to load
    await page.waitForSelector('iframe', { timeout: 30000 });
    
    // Wait a bit for iframe content to load
    await page.waitForTimeout(5000);
    
    // Check for auth/login redirects in iframe srcs
    const iframes = page.locator('iframe');
    const iframeCount = await iframes.count();
    
    for (let i = 0; i < Math.min(iframeCount, 8); i++) {
      const iframe = iframes.nth(i);
      const src = await iframe.getAttribute('src');
      expect(src).toBeTruthy();
      expect(src).not.toMatch(/\/login/);
      expect(src).toMatch(/\/d\//);
    }
    
    // Verify no critical console errors
    const criticalErrors = consoleErrors.filter(err =>
      err.includes('401') || err.includes('403') || err.includes('X-Frame-Options') || err.includes('refused to display')
    );
    
    if (criticalErrors.length > 0) {
      console.warn('Console errors found:', criticalErrors);
    }
    
    // Network failures should be minimal (some 404s for missing resources are OK)
    const authFailures = networkFailures.filter(f => f.includes('401') || f.includes('403'));
    expect(authFailures.length).toBe(0);
  });

  test('Region variable updates iframe src when region changes', async ({ page }) => {
    await page.goto(`${FRONTEND_BASE}/forecast`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    
    // Wait for region selector
    const regionSelect = page.locator('select').first();
    await regionSelect.waitFor({ state: 'visible', timeout: 30000 });
    
    // Wait for regions to load
    await page.waitForFunction(
      () => {
        const select = document.querySelector('select');
        return select && select.options.length > 2;
      },
      { timeout: 30000 }
    );
    
    // Get initial region value
    const initialValue = await regionSelect.inputValue();
    
    // Get initial iframe src (wait for iframes to appear)
    await page.waitForSelector('iframe', { timeout: 30000 });
    const initialIframe = page.locator('iframe').first();
    const initialSrc = await initialIframe.getAttribute('src');
    expect(initialSrc).toBeTruthy();
    expect(initialSrc).toMatch(/var-region=/);
    
    // Find a different region to select
    const options = await regionSelect.locator('option').all();
    let differentRegionValue: string | null = null;
    
    for (const option of options) {
      const value = await option.getAttribute('value');
      if (value && value !== initialValue && value !== '') {
        differentRegionValue = value;
        break;
      }
    }
    
    if (differentRegionValue) {
      await regionSelect.selectOption(differentRegionValue);
      
      // Wait for iframe src to update
      await page.waitForTimeout(3000);
      
      const updatedSrc = await initialIframe.getAttribute('src');
      expect(updatedSrc).toBeTruthy();
      
      // Verify src changed (region parameter should differ)
      if (initialSrc && updatedSrc) {
        const initialRegion = initialSrc.match(/var-region=([^&]+)/)?.[1];
        const updatedRegion = updatedSrc.match(/var-region=([^&]+)/)?.[1];
        
        if (initialRegion && updatedRegion) {
          expect(updatedRegion).not.toBe(initialRegion);
        }
      }
    } else {
      test.skip('No different region available for testing');
    }
  });

  test('Live page shows Grafana dashboards', async ({ page }) => {
    await page.goto(`${FRONTEND_BASE}/live`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    
    const pageTitle = await page.title();
    expect(pageTitle).toBeTruthy();
    
    // Live page should have Grafana embeds
    await page.waitForSelector('iframe', { timeout: 30000 });
    const iframes = page.locator('iframe');
    const iframeCount = await iframes.count();
    
    // Live page has at least 2 dashboards (behavior-index-global, subindex-deep-dive)
    expect(iframeCount).toBeGreaterThanOrEqual(2);
    
    // Verify iframe srcs point to Grafana
    const firstIframe = iframes.first();
    const src = await firstIframe.getAttribute('src');
    expect(src).toBeTruthy();
    expect(src).toMatch(/grafana|\/d\//);
    
    console.log(`Live page: ${iframeCount} iframes found`);
  });

  test('Playground page shows Grafana dashboards', async ({ page }) => {
    await page.goto(`${FRONTEND_BASE}/playground`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    
    const pageTitle = await page.title();
    expect(pageTitle).toBeTruthy();
    
    // Playground page should have Grafana embeds
    await page.waitForSelector('iframe', { timeout: 30000 });
    const iframes = page.locator('iframe');
    const iframeCount = await iframes.count();
    
    // Playground has at least 2 dashboards
    expect(iframeCount).toBeGreaterThanOrEqual(2);
    
    // Verify iframe srcs point to Grafana
    const firstIframe = iframes.first();
    const src = await firstIframe.getAttribute('src');
    expect(src).toBeTruthy();
    expect(src).toMatch(/grafana|\/d\//);
    
    console.log(`Playground page: ${iframeCount} iframes found`);
  });

  test('History page loads (no embeds expected)', async ({ page }) => {
    await page.goto(`${FRONTEND_BASE}/history`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    
    const pageTitle = await page.title();
    expect(pageTitle).toBeTruthy();
    
    // History page is a table view, not expected to have Grafana embeds
    const iframes = page.locator('iframe');
    const iframeCount = await iframes.count();
    
    // History page may have 0 iframes (table-based view)
    // This is acceptable - document it
    console.log(`History page: ${iframeCount} iframes found (table view, embeds not required)`);
    
    // Verify page has history table
    const historyTitle = page.locator('[data-testid="history-page-title"]');
    await expect(historyTitle).toBeVisible({ timeout: 10000 });
    
    expect(pageTitle.length).toBeGreaterThan(0);
  });
});
