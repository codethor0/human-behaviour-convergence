import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const FRONTEND_BASE = process.env.FRONTEND_BASE || 'http://localhost:3100';
const EVIDENCE_DIR = process.env.EVIDENCE_DIR || 'test-results';

// Expected section headings
const EXPECTED_SECTIONS = [
  'Regional Forecast Overview & Key Metrics',
  'Behavior Index Timeline & Historical Trends',
  'Sub-Index Components & Contributing Factors',
  'Real-Time Data Source Status & API Health',
];

test.describe('Visual Dashboard Verification', () => {
  test('Forecast page shows all expected dashboard sections and iframes', async ({ page, request }) => {
    const iframes: Array<{ src: string; status: number; visible: boolean }> = [];
    const consoleErrors: string[] = [];
    const networkFailures: string[] = [];

    // Collect console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Collect network failures
    page.on('response', (response) => {
      const url = response.url();
      if (url.includes('grafana') || url.includes('/d/')) {
        if (response.status() >= 400) {
          networkFailures.push(`${response.status()}: ${url}`);
        }
      }
    });

    // Navigate to forecast page
    await page.goto(`${FRONTEND_BASE}/forecast`, { waitUntil: 'networkidle', timeout: 60000 });

    // Wait for page to load
    await page.waitForLoadState('domcontentloaded');

    // Verify expected section headings exist
    const foundSections: string[] = [];
    for (const heading of EXPECTED_SECTIONS) {
      const headingLocator = page.locator(`text=${heading}`);
      const isVisible = await headingLocator.first().isVisible({ timeout: 10000 }).catch(() => false);
      if (isVisible) {
        foundSections.push(heading);
      }
    }

    // Assert all sections found
    expect(foundSections.length).toBe(EXPECTED_SECTIONS.length);

    // Wait for iframes to appear
    await page.waitForSelector('iframe', { timeout: 30000 });

    // Collect all iframe elements
    const iframeElements = page.locator('iframe');
    const iframeCount = await iframeElements.count();
    expect(iframeCount).toBeGreaterThanOrEqual(4);

    // Extract iframe src and verify each
    for (let i = 0; i < iframeCount; i++) {
      const iframe = iframeElements.nth(i);
      const src = await iframe.getAttribute('src');
      const isVisible = await iframe.isVisible();

      if (src) {
        // Verify HTTP 200
        let status = 0;
        try {
          const response = await request.get(src, { timeout: 10000 });
          status = response.status();
        } catch (e) {
          status = 0;
        }

        iframes.push({ src, status, visible: isVisible });
      }
    }

    // Save iframe list as JSON
    const iframesPath = path.join(EVIDENCE_DIR, 'iframes.json');
    fs.writeFileSync(iframesPath, JSON.stringify(iframes, null, 2));

    // Verify all iframes return 200
    const all200 = iframes.every(iframe => iframe.status === 200);
    expect(all200).toBe(true);

    // Take full page screenshot
    await page.screenshot({
      path: path.join(EVIDENCE_DIR, 'screenshots', 'forecast_page_full.png'),
      fullPage: true,
    });

    // Take section screenshots
    for (let i = 0; i < EXPECTED_SECTIONS.length; i++) {
      const heading = EXPECTED_SECTIONS[i];
      const headingLocator = page.locator(`text=${heading}`).first();
      if (await headingLocator.isVisible()) {
        await headingLocator.scrollIntoViewIfNeeded();
        await page.waitForTimeout(1000); // Wait for iframes to load

        try {
          await page.screenshot({
            path: path.join(EVIDENCE_DIR, 'screenshots', `section_${i + 1}_${heading.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30)}.png`),
            fullPage: false,
          });
        } catch (e) {
          console.warn(`Screenshot failed for section ${i + 1}:`, e);
        }
      }
    }

    // Dump DOM HTML
    const htmlContent = await page.content();
    const htmlPath = path.join(EVIDENCE_DIR, 'ui_dom_dump.html');
    fs.writeFileSync(htmlPath, htmlContent);

    // Save verification results
    const results = {
      sectionsFound: foundSections,
      iframeCount,
      iframes,
      consoleErrors,
      networkFailures,
      allIframes200: all200,
    };

    const resultsPath = path.join(EVIDENCE_DIR, 'verification_results.json');
    fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2));

    // Final assertions
    expect(foundSections.length).toBe(EXPECTED_SECTIONS.length);
    expect(iframeCount).toBeGreaterThanOrEqual(4);
    expect(all200).toBe(true);
    expect(consoleErrors.filter(e => e.includes('401') || e.includes('403') || e.includes('X-Frame-Options')).length).toBe(0);
  });
});
