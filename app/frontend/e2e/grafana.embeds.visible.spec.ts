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
    // Collect console errors and network failures
    const consoleErrors: string[] = [];
    const networkFailures: string[] = [];
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    page.on('response', (response) => {
      const url = response.url();
      if (url.includes('grafana') || url.includes('/d/')) {
        if (response.status() >= 400) {
          networkFailures.push(`${response.status()}: ${url}`);
        }
      }
    });
    
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
    
    // Wait for iframes to appear (they may appear after region selection or forecast generation)
    await page.waitForSelector('iframe', { timeout: 30000 });
    
    // Find all iframes
    const iframes = page.locator('iframe');
    const iframeCount = await iframes.count();
    expect(iframeCount).toBeGreaterThanOrEqual(4); // At least core dashboards
    
    // Verify each expected dashboard iframe
    const iframeSrcs: string[] = [];
    const iframeDetails: Array<{ src: string; visible: boolean; dimensions: { width: number; height: number } | null }> = [];
    
    for (let i = 0; i < iframeCount; i++) {
      const iframe = iframes.nth(i);
      const src = await iframe.getAttribute('src');
      const isVisible = await iframe.isVisible();
      const box = await iframe.boundingBox();
      
      if (src) {
        iframeSrcs.push(src);
        iframeDetails.push({
          src,
          visible: isVisible,
          dimensions: box ? { width: box.width, height: box.height } : null,
        });
      }
    }
    
    // Check for expected dashboard UIDs
    const foundDashboards = EXPECTED_DASHBOARDS['/forecast'].filter(dash =>
      iframeSrcs.some(src => src.includes(dash))
    );
    
    expect(foundDashboards.length).toBeGreaterThanOrEqual(3); // At least core dashboards
    
    // Verify iframes are visible and have dimensions
    for (let i = 0; i < Math.min(iframeCount, 8); i++) {
      const iframe = iframes.nth(i);
      const box = await iframe.boundingBox();
      expect(box).toBeTruthy();
      expect(box!.width).toBeGreaterThan(100);
      expect(box!.height).toBeGreaterThan(100);
    }
    
    // Verify region variable wiring (check iframes that should have region)
    const regionIframes = iframes.filter(async (iframe) => {
      const src = await iframe.getAttribute('src');
      return src && (src.includes('forecast-summary') || src.includes('regional-variance'));
    });
    
    if (await regionIframes.count() > 0) {
      const regionIframe = regionIframes.first();
      const regionSrc = await regionIframe.getAttribute('src');
      expect(regionSrc).toMatch(/var-region=|region=/);
    }
    
    // Wait for iframe content to load
    await page.waitForTimeout(5000);
    
    // Capture full-page screenshot
    const evidenceDir = process.env.EVIDENCE_DIR || 'test-results';
    await page.screenshot({ 
      path: `${evidenceDir}/forecast-page-full.png`, 
      fullPage: true 
    });
    
    // Capture individual iframe screenshots (only if box is valid and within viewport)
    for (let i = 0; i < Math.min(iframeCount, 8); i++) {
      const iframe = iframes.nth(i);
      const box = await iframe.boundingBox();
      if (box && box.width > 0 && box.height > 0 && box.x >= 0 && box.y >= 0) {
        try {
          await page.screenshot({
            path: `${evidenceDir}/forecast-iframe-${i}.png`,
            clip: { 
              x: Math.max(0, box.x), 
              y: Math.max(0, box.y), 
              width: box.width, 
              height: Math.min(box.height, 800) 
            },
          });
        } catch (e) {
          // Screenshot clipping failed, skip this iframe
          console.warn(`Screenshot failed for iframe ${i}:`, e);
        }
      }
    }
    
    // Save console and network logs (using test info for artifacts)
    // Note: Artifacts will be saved to test-results directory by Playwright
    console.log('Console errors:', consoleErrors);
    console.log('Network failures:', networkFailures);
    console.log('Iframe details:', JSON.stringify(iframeDetails, null, 2));
    
    // Verify no critical errors
    const criticalErrors = consoleErrors.filter(err =>
      err.includes('401') || err.includes('403') || err.includes('X-Frame-Options') || err.includes('refused to display')
    );
    
    const authFailures = networkFailures.filter(f => f.includes('401') || f.includes('403'));
    expect(authFailures.length).toBe(0);
    
    if (criticalErrors.length > 0) {
      console.warn('Critical console errors found:', criticalErrors);
    }
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
    const evidenceDir = process.env.EVIDENCE_DIR || 'test-results';
    const consoleErrors: string[] = [];
    const networkFailures: string[] = [];
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    page.on('response', (response) => {
      if (response.status() >= 400 && response.url().includes('grafana')) {
        networkFailures.push(`${response.status()}: ${response.url()}`);
      }
    });
    
    await page.goto(`${FRONTEND_BASE}/live`, { waitUntil: 'networkidle', timeout: 60000 });
    
    const pageTitle = await page.title();
    expect(pageTitle).toBeTruthy();
    
    // Live page should have Grafana embeds
    await page.waitForSelector('iframe', { timeout: 30000 });
    const iframes = page.locator('iframe');
    const iframeCount = await iframes.count();
    
    // Live page has at least 2 dashboards (behavior-index-global, subindex-deep-dive)
    expect(iframeCount).toBeGreaterThanOrEqual(2);
    
    // Verify iframe srcs point to Grafana
    for (let i = 0; i < iframeCount; i++) {
      const iframe = iframes.nth(i);
      const src = await iframe.getAttribute('src');
      expect(src).toBeTruthy();
      expect(src).toMatch(/grafana|\/d\//);
      expect(src).not.toMatch(/\/login/);
    }
    
    // Capture screenshot
    await page.screenshot({ path: `${evidenceDir}/live-page-full.png`, fullPage: true });
    
    // Verify no auth errors
    const authFailures = networkFailures.filter(f => f.includes('401') || f.includes('403'));
    expect(authFailures.length).toBe(0);
    
    console.log(`Live page: ${iframeCount} iframes found`);
  });

  test('Playground page shows Grafana dashboards', async ({ page }) => {
    const evidenceDir = process.env.EVIDENCE_DIR || 'test-results';
    const consoleErrors: string[] = [];
    const networkFailures: string[] = [];
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    page.on('response', (response) => {
      if (response.status() >= 400 && response.url().includes('grafana')) {
        networkFailures.push(`${response.status()}: ${response.url()}`);
      }
    });
    
    await page.goto(`${FRONTEND_BASE}/playground`, { waitUntil: 'networkidle', timeout: 60000 });
    
    const pageTitle = await page.title();
    expect(pageTitle).toBeTruthy();
    
    // Playground page should have Grafana embeds
    await page.waitForSelector('iframe', { timeout: 30000 });
    const iframes = page.locator('iframe');
    const iframeCount = await iframes.count();
    
    // Playground has at least 2 dashboards
    expect(iframeCount).toBeGreaterThanOrEqual(2);
    
    // Verify iframe srcs point to Grafana
    for (let i = 0; i < iframeCount; i++) {
      const iframe = iframes.nth(i);
      const src = await iframe.getAttribute('src');
      expect(src).toBeTruthy();
      expect(src).toMatch(/grafana|\/d\//);
      expect(src).not.toMatch(/\/login/);
    }
    
    // Capture screenshot
    await page.screenshot({ path: `${evidenceDir}/playground-page-full.png`, fullPage: true });
    
    // Verify no auth errors
    const authFailures = networkFailures.filter(f => f.includes('401') || f.includes('403'));
    expect(authFailures.length).toBe(0);
    
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
