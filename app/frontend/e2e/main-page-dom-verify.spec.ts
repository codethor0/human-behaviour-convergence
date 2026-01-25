/**
 * Main Page DOM Verification (Phase 4 - Visual Verification)
 *
 * Programmatic DOM checks that dashboards are present and visible.
 * Does not require Grafana to be running (iframes may load error/login).
 * Run: npx playwright test e2e/main-page-dom-verify.spec.ts
 */

import { test, expect } from '@playwright/test';

test.describe('Main Page DOM - Dashboard Visibility', () => {
  test('dashboard embed containers exist and are visible', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const embeds = page.locator('[data-testid^="dashboard-embed-"]');
    const count = await embeds.count();
    expect(count).toBeGreaterThanOrEqual(23);
  });

  test('each dashboard embed has an iframe with valid src', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const embeds = await page.locator('[data-testid^="dashboard-embed-"]').all();
    const uids = new Set<string>();

    for (const el of embeds) {
      const iframe = el.locator('iframe');
      await expect(iframe).toHaveCount(1);

      const src = await iframe.getAttribute('src');
      expect(src).toBeTruthy();
      const match = src?.match(/\/d\/([a-z0-9-]+)/);
      expect(match).toBeTruthy();
      if (match) uids.add(match[1]);
    }

    expect(uids.size).toBeGreaterThanOrEqual(18);
  });

  test('iframes have non-zero dimensions from layout', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(500);

    const iframes = await page.locator('[data-testid^="dashboard-embed-"] iframe').all();
    expect(iframes.length).toBeGreaterThanOrEqual(18);

    for (const iframe of iframes) {
      const box = await iframe.boundingBox();
      expect(box).toBeTruthy();
      expect((box?.height ?? 0)).toBeGreaterThan(100);
      expect((box?.width ?? 0)).toBeGreaterThan(100);
    }
  });

  test('dashboard sections are in the DOM and not hidden by CSS', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const ids = ['behavior-forecast', 'live-playground', 'results-dashboard', 'grafana-analytics'];
    for (const id of ids) {
      const el = page.locator(`#${id}`);
      await expect(el).toBeVisible();
      const hidden = await el.evaluate((e) => {
        const s = window.getComputedStyle(e);
        return s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) === 0;
      });
      expect(hidden).toBe(false);
    }
  });
});
