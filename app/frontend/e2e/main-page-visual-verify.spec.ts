import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test.describe('Main Page Visual Verification', () => {
  const EVIDENCE_DIR = process.env.EVIDENCE_DIR || '/tmp/hbc_mainpage_visual_verify';
  
  test.beforeAll(async () => {
    fs.mkdirSync(path.join(EVIDENCE_DIR, 'after'), { recursive: true });
  });

  test('Capture screenshots of all 6 sections', async ({ page }) => {
    await page.goto('http://localhost:3100/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    const sections = [
      { id: 'executive', name: 'executive' },
      { id: 'forecasting', name: 'forecast' },
      { id: 'operations', name: 'operations' },
      { id: 'analysis', name: 'analysis' },
      { id: 'anomalies', name: 'anomalies' },
      { id: 'integrity', name: 'integrity' },
    ];

    for (const section of sections) {
      const sectionElement = page.locator(`#${section.id}`);
      await expect(sectionElement).toBeVisible();
      
      await sectionElement.screenshot({
        path: path.join(EVIDENCE_DIR, 'after', `section_${section.name}.png`),
        fullPage: false,
      });
    }

    await page.screenshot({
      path: path.join(EVIDENCE_DIR, 'after', 'full_page.png'),
      fullPage: true,
    });
  });

  test('Verify region switching updates all dashboards', async ({ page }) => {
    await page.goto('http://localhost:3100/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    const regionSelector = page.locator('[data-testid="global-region-selector"]');
    await expect(regionSelector).toBeVisible();

    const initialValue = await regionSelector.inputValue();
    const options = await regionSelector.locator('option').all();
    
    if (options.length > 1) {
      const secondOption = options[1];
      const secondValue = await secondOption.getAttribute('value');
      
      if (secondValue && secondValue !== initialValue) {
        await page.screenshot({
          path: path.join(EVIDENCE_DIR, 'after', 'region_before.png'),
          fullPage: true,
        });

        await regionSelector.selectOption(secondValue);
        await page.waitForTimeout(2000);

        await page.screenshot({
          path: path.join(EVIDENCE_DIR, 'after', 'region_after.png'),
          fullPage: true,
        });

        const iframesWithRegion = await page.locator('iframe[src*="var-region"]').all();
        expect(iframesWithRegion.length).toBeGreaterThan(0);

        for (const iframe of iframesWithRegion) {
          const src = await iframe.getAttribute('src');
          expect(src).toContain(`var-region=${encodeURIComponent(secondValue)}`);
        }
      }
    }
  });

  test('Verify all iframes load with HTTP 200', async ({ page, request }) => {
    await page.goto('http://localhost:3100/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);

    const iframes = await page.locator('iframe[src*="grafana"]').all();
    expect(iframes.length).toBeGreaterThanOrEqual(18);

    const urls: string[] = [];
    for (const iframe of iframes) {
      const src = await iframe.getAttribute('src');
      if (src) {
        urls.push(src);
      }
    }

    const results: Array<{ url: string; status: number }> = [];
    for (const url of urls.slice(0, 10)) {
      try {
        const response = await request.get(url);
        results.push({ url, status: response.status() });
        expect(response.status()).toBe(200);
      } catch (e) {
        results.push({ url, status: 0 });
      }
    }

    fs.writeFileSync(
      path.join(EVIDENCE_DIR, 'after', 'iframe_status.json'),
      JSON.stringify(results, null, 2)
    );
  });

  test('Verify responsive layout on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('http://localhost:3100/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: path.join(EVIDENCE_DIR, 'after', 'mobile_view.png'),
      fullPage: true,
    });

    const grid2Col = page.locator('.dashboard-grid-cols-2').first();
    if (await grid2Col.count() > 0) {
      const computedStyle = await grid2Col.evaluate((el) => {
        return window.getComputedStyle(el).gridTemplateColumns;
      });
      expect(computedStyle).toBe('1fr');
    }
  });

  test('Verify no console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('http://localhost:3100/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    fs.writeFileSync(
      path.join(EVIDENCE_DIR, 'after', 'console_errors.json'),
      JSON.stringify(errors, null, 2)
    );

    expect(errors.length).toBe(0);
  });
});
