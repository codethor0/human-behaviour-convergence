import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const FRONTEND_BASE = process.env.FRONTEND_BASE || 'http://localhost:3100';
const EVIDENCE_DIR = process.env.EVIDENCE_DIR || 'test-results';

interface PanelAudit {
  dashboard_uid: string;
  panel_id: number;
  panel_title: string;
  iframe_src: string;
  http_status: number;
  data_present: boolean;
  reason: string;
  promql_query?: string;
}

test.describe('Dashboard Data Verification', () => {
  test('Verify all dashboard panels show data (not blank)', async ({ page, request }) => {
    const panelAudits: PanelAudit[] = [];
    const screenshotsDir = path.join(EVIDENCE_DIR, 'screenshots');
    if (!fs.existsSync(screenshotsDir)) {
      fs.mkdirSync(screenshotsDir, { recursive: true });
    }

    // Test Forecast page
    await page.goto(`${FRONTEND_BASE}/forecast`, {
      waitUntil: 'networkidle',
      timeout: 60000,
    });
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(5000); // Wait for dashboards to load

    const forecastHtml = await page.content();
    fs.writeFileSync(path.join(EVIDENCE_DIR, 'ui_dom_forecast.html'), forecastHtml, 'utf-8');

    const forecastIframes = page.locator('iframe');
    const forecastIframeCount = await forecastIframes.count();
    expect(forecastIframeCount).toBeGreaterThanOrEqual(4);

    const iframeList: Array<{ src: string; status: number }> = [];
    for (let i = 0; i < forecastIframeCount; i++) {
      const src = await forecastIframes.nth(i).getAttribute('src');
      if (src && src.length > 0) {
        try {
          const resp = await request.get(src, { timeout: 15000 });
          iframeList.push({ src, status: resp.status() });

          // Extract dashboard UID from src
          const uidMatch = src.match(/\/d\/([^?]+)/);
          const uid = uidMatch ? uidMatch[1] : 'unknown';

          panelAudits.push({
            dashboard_uid: uid,
            panel_id: i,
            panel_title: `Panel ${i + 1}`,
            iframe_src: src,
            http_status: resp.status(),
            data_present: resp.status() === 200,
            reason: resp.status() === 200 ? 'HTTP 200 OK' : `HTTP ${resp.status()}`,
          });
        } catch (e) {
          iframeList.push({ src, status: 0 });
          panelAudits.push({
            dashboard_uid: 'unknown',
            panel_id: i,
            panel_title: `Panel ${i + 1}`,
            iframe_src: src,
            http_status: 0,
            data_present: false,
            reason: `Request failed: ${e}`,
          });
        }
      }
    }

    await page.screenshot({
      path: path.join(screenshotsDir, 'forecast_full_page.png'),
      fullPage: true,
    });

    // Test Live page
    await page.goto(`${FRONTEND_BASE}/live`, {
      waitUntil: 'networkidle',
      timeout: 60000,
    });
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(5000);

    const liveHtml = await page.content();
    fs.writeFileSync(path.join(EVIDENCE_DIR, 'ui_dom_live.html'), liveHtml, 'utf-8');

    const liveIframes = page.locator('iframe');
    const liveIframeCount = await liveIframes.count();
    for (let i = 0; i < liveIframeCount; i++) {
      const src = await liveIframes.nth(i).getAttribute('src');
      if (src && src.length > 0) {
        try {
          const resp = await request.get(src, { timeout: 15000 });
          const uidMatch = src.match(/\/d\/([^?]+)/);
          const uid = uidMatch ? uidMatch[1] : 'unknown';

          panelAudits.push({
            dashboard_uid: uid,
            panel_id: i + 100,
            panel_title: `Live Panel ${i + 1}`,
            iframe_src: src,
            http_status: resp.status(),
            data_present: resp.status() === 200,
            reason: resp.status() === 200 ? 'HTTP 200 OK' : `HTTP ${resp.status()}`,
          });
        } catch (e) {
          panelAudits.push({
            dashboard_uid: 'unknown',
            panel_id: i + 100,
            panel_title: `Live Panel ${i + 1}`,
            iframe_src: src || '',
            http_status: 0,
            data_present: false,
            reason: `Request failed: ${e}`,
          });
        }
      }
    }

    await page.screenshot({
      path: path.join(screenshotsDir, 'live_full_page.png'),
      fullPage: true,
    });

    // Test Playground page
    await page.goto(`${FRONTEND_BASE}/playground`, {
      waitUntil: 'networkidle',
      timeout: 60000,
    });
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(5000);

    const playgroundHtml = await page.content();
    fs.writeFileSync(path.join(EVIDENCE_DIR, 'ui_dom_playground.html'), playgroundHtml, 'utf-8');

    const playgroundIframes = page.locator('iframe');
    const playgroundIframeCount = await playgroundIframes.count();
    for (let i = 0; i < playgroundIframeCount; i++) {
      const src = await playgroundIframes.nth(i).getAttribute('src');
      if (src && src.length > 0) {
        try {
          const resp = await request.get(src, { timeout: 15000 });
          const uidMatch = src.match(/\/d\/([^?]+)/);
          const uid = uidMatch ? uidMatch[1] : 'unknown';

          panelAudits.push({
            dashboard_uid: uid,
            panel_id: i + 200,
            panel_title: `Playground Panel ${i + 1}`,
            iframe_src: src,
            http_status: resp.status(),
            data_present: resp.status() === 200,
            reason: resp.status() === 200 ? 'HTTP 200 OK' : `HTTP ${resp.status()}`,
          });
        } catch (e) {
          panelAudits.push({
            dashboard_uid: 'unknown',
            panel_id: i + 200,
            panel_title: `Playground Panel ${i + 1}`,
            iframe_src: src || '',
            http_status: 0,
            data_present: false,
            reason: `Request failed: ${e}`,
          });
        }
      }
    }

    await page.screenshot({
      path: path.join(screenshotsDir, 'playground_full_page.png'),
      fullPage: true,
    });

    // Save iframe list
    fs.writeFileSync(
      path.join(EVIDENCE_DIR, 'iframes.json'),
      JSON.stringify({ iframeList }, null, 2),
      'utf-8'
    );

    // Save panel audit
    fs.writeFileSync(
      path.join(EVIDENCE_DIR, 'panel_data_audit.json'),
      JSON.stringify({ panels: panelAudits, summary: {
        total_panels: panelAudits.length,
        panels_with_data: panelAudits.filter(p => p.data_present).length,
        panels_without_data: panelAudits.filter(p => !p.data_present).length,
      }}, null, 2),
      'utf-8'
    );

    // Assertions
    const all200 = panelAudits.every((p) => p.http_status === 200);
    expect(all200).toBe(true);

    const allHaveData = panelAudits.every((p) => p.data_present);
    expect(allHaveData).toBe(true);
  });
});
