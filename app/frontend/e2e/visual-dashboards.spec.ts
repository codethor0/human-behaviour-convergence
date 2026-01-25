import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const FRONTEND_BASE = process.env.FRONTEND_BASE || 'http://localhost:3100';
const EVIDENCE_DIR = process.env.EVIDENCE_DIR || 'test-results';

const EXPECTED_SECTIONS = [
  'Regional Forecast Overview & Key Metrics',
  'Behavior Index Timeline & Historical Trends',
  'Sub-Index Components & Contributing Factors',
  'Real-Time Data Source Status & API Health',
];

test.describe('Visual Dashboards Verification', () => {
  test('Forecast page: sections, iframes, HTTP 200, screenshots, DOM dump', async ({
    page,
    request,
  }) => {
    const iframeList: Array<{ src: string; status: number }> = [];
    const consoleErrors: string[] = [];
    const networkFailures: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    page.on('response', (resp) => {
      const u = resp.url();
      if ((u.includes('grafana') || u.includes('/d/')) && resp.status() >= 400) {
        networkFailures.push(`${resp.status()}: ${u}`);
      }
    });

    await page.goto(`${FRONTEND_BASE}/forecast`, {
      waitUntil: 'networkidle',
      timeout: 60000,
    });
    await page.waitForLoadState('domcontentloaded');

    for (const heading of EXPECTED_SECTIONS) {
      const loc = page.locator(`text=${heading}`).first();
      await expect(loc).toBeVisible({ timeout: 10000 });
    }

    await page.waitForSelector('iframe', { timeout: 30000 });
    const iframes = page.locator('iframe');
    const iframeCount = await iframes.count();
    expect(iframeCount).toBeGreaterThanOrEqual(4);

    const iframeSrcs: string[] = [];
    for (let i = 0; i < iframeCount; i++) {
      const src = await iframes.nth(i).getAttribute('src');
      if (src && src.length > 0) {
        iframeSrcs.push(src);
      }
    }
    expect(iframeSrcs.length).toBeGreaterThanOrEqual(4);

    for (const src of iframeSrcs) {
      try {
        const resp = await request.get(src, { timeout: 10000 });
        iframeList.push({ src, status: resp.status() });
      } catch (e) {
        iframeList.push({ src, status: 0 });
      }
    }

    const screenshotsDir = path.join(EVIDENCE_DIR, 'screenshots');
    if (!fs.existsSync(screenshotsDir)) {
      fs.mkdirSync(screenshotsDir, { recursive: true });
    }

    await page.screenshot({
      path: path.join(screenshotsDir, 'forecast_full_page.png'),
      fullPage: true,
    });

    for (let i = 0; i < EXPECTED_SECTIONS.length; i++) {
      const heading = EXPECTED_SECTIONS[i];
      const loc = page.locator(`text=${heading}`).first();
      if (await loc.isVisible()) {
        await loc.scrollIntoViewIfNeeded();
        const box = await loc.boundingBox();
        if (box) {
          try {
            await page.screenshot({
              path: path.join(
                screenshotsDir,
                `section_${i + 1}_${heading.replace(/[^a-zA-Z0-9]/g, '_').slice(0, 30)}.png`
              ),
              clip: {
                x: Math.max(0, box.x - 10),
                y: Math.max(0, box.y - 10),
                width: Math.min(box.width + 20, 1600),
                height: Math.min(box.height + 500, 800),
              },
            });
          } catch (_) {}
        }
      }
    }

    const html = await page.content();
    fs.writeFileSync(path.join(EVIDENCE_DIR, 'ui_dom_dump.html'), html, 'utf-8');

    fs.writeFileSync(
      path.join(EVIDENCE_DIR, 'iframes.json'),
      JSON.stringify({ iframeList, iframeSrcs }, null, 2),
      'utf-8'
    );

    const authFailures = networkFailures.filter(
      (f) => f.includes('401') || f.includes('403')
    );
    expect(authFailures.length).toBe(0);

    const criticalConsole = consoleErrors.filter(
      (e) =>
        e.includes('401') ||
        e.includes('403') ||
        e.includes('X-Frame-Options') ||
        e.includes('refused to display')
    );
    expect(criticalConsole.length).toBe(0);

    const all200 = iframeList.every((x) => x.status === 200);
    expect(all200).toBe(true);
  });
});
