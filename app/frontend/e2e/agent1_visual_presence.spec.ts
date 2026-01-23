import { test, expect } from '@playwright/test';

const FRONTEND_BASE = 'http://localhost:3100';
const EVIDENCE_DIR = process.env.EVIDENCE_DIR || 'test-results';

// Expected section headings on forecast page
const EXPECTED_SECTIONS = [
  'Regional Forecast Overview & Key Metrics',
  'Behavior Index Timeline & Historical Trends',
  'Sub-Index Components & Contributing Factors',
  'Real-Time Data Source Status & API Health',
];

test.describe('Agent 1: Visual Presence Verification', () => {
  test('Forecast page shows all expected dashboard sections and iframes', async ({ page, request }) => {
    const iframeSrcs: string[] = [];
    const iframeStatuses: Array<{ src: string; status: number }> = [];
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
    for (const heading of EXPECTED_SECTIONS) {
      const headingLocator = page.locator(`text=${heading}`);
      await expect(headingLocator.first()).toBeVisible({ timeout: 10000 });
    }

    // Wait for iframes to appear
    await page.waitForSelector('iframe', { timeout: 30000 });

    // Find all iframes
    const iframes = page.locator('iframe');
    const iframeCount = await iframes.count();
    expect(iframeCount).toBeGreaterThanOrEqual(4);

    // Extract iframe src values
    for (let i = 0; i < iframeCount; i++) {
      const iframe = iframes.nth(i);
      const src = await iframe.getAttribute('src');
      if (src) {
        iframeSrcs.push(src);
      }
    }

    // Write iframe srcs to file
    const fs = require('fs');
    const path = require('path');
    const iframeSrcsPath = path.join(EVIDENCE_DIR, 'iframe_srcs.txt');
    fs.writeFileSync(iframeSrcsPath, iframeSrcs.join('\n'));

    // Verify each iframe src returns HTTP 200
    for (const src of iframeSrcs) {
      try {
        const response = await request.get(src, { timeout: 10000 });
        iframeStatuses.push({ src, status: response.status() });
        expect(response.status()).toBe(200);
      } catch (e) {
        iframeStatuses.push({ src, status: 0 });
        console.warn(`Failed to verify iframe src: ${src}`, e);
      }
    }

    // Take full page screenshot
    await page.screenshot({ 
      path: `${EVIDENCE_DIR}/forecast_page_full.png`, 
      fullPage: true 
    });

    // Take screenshots of each section
    for (let i = 0; i < EXPECTED_SECTIONS.length; i++) {
      const heading = EXPECTED_SECTIONS[i];
      const headingLocator = page.locator(`text=${heading}`).first();
      if (await headingLocator.isVisible()) {
        const box = await headingLocator.boundingBox();
        if (box) {
          try {
            await page.screenshot({
              path: `${EVIDENCE_DIR}/section_${i + 1}_${heading.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30)}.png`,
              clip: {
                x: Math.max(0, box.x - 10),
                y: Math.max(0, box.y - 10),
                width: Math.min(box.width + 20, 1600),
                height: Math.min(box.height + 500, 800),
              },
            });
          } catch (e) {
            console.warn(`Screenshot failed for section ${i + 1}:`, e);
          }
        }
      }
    }

    // Write verification results
    const results = {
      sectionsFound: EXPECTED_SECTIONS.length,
      iframeCount,
      iframeSrcs,
      iframeStatuses,
      consoleErrors,
      networkFailures,
      allIframes200: iframeStatuses.every(s => s.status === 200),
    };

    fs.writeFileSync(
      path.join(EVIDENCE_DIR, 'verification_results.json'),
      JSON.stringify(results, null, 2)
    );

    // Assertions
    expect(results.sectionsFound).toBe(EXPECTED_SECTIONS.length);
    expect(iframeCount).toBeGreaterThanOrEqual(4);
    expect(results.allIframes200).toBe(true);
    expect(consoleErrors.filter(e => e.includes('401') || e.includes('403') || e.includes('X-Frame-Options')).length).toBe(0);
  });
});
