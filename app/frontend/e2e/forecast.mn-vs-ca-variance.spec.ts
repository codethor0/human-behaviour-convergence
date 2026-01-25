/**
 * E2E: MN vs CA forecast variance.
 * Open /forecast, generate Minnesota and California forecasts, capture behavior_index
 * and regional sub-indices, assert they differ (or at least one REGIONAL index differs).
 * On failure, print a diagnostic table.
 */
import { test, expect } from '@playwright/test';

const REGIONAL_INDICES = [
  'environmental_stress',
  'political_stress',
  'crime_stress',
  'misinformation_stress',
  'social_cohesion_stress',
] as const;

async function waitForRegionsReady(page: any) {
  await page.goto('/forecast', { waitUntil: 'domcontentloaded' });
  const regionSelect = page.locator('select').first();
  await regionSelect.waitFor({ state: 'visible', timeout: 60_000 });
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('select');
      return sel && sel.options.length > 1;
    },
    { timeout: 60_000 }
  );
}

function extractBiAndSubindices(data: any): {
  behavior_index: number | null;
  sub_indices: Record<string, number>;
} {
  const sub_indices: Record<string, number> = {};
  let behavior_index: number | null = null;
  const history = data?.history ?? [];
  if (history.length) {
    const last = history[history.length - 1];
    behavior_index =
      typeof last?.behavior_index === 'number' ? last.behavior_index : null;
    const si = last?.sub_indices;
    if (si && typeof si === 'object') {
      for (const k of REGIONAL_INDICES) {
        const v = (si as Record<string, number>)[k];
        if (typeof v === 'number') sub_indices[k] = v;
      }
    }
  }
  return { behavior_index, sub_indices };
}

test.describe('Forecast MN vs CA variance', () => {
  test('MN and CA forecasts differ (behavior_index or regional sub-indices)', async ({
    page,
  }) => {
    test.setTimeout(240_000);
    await waitForRegionsReady(page);

    const regionSelect = page.locator('select').first();
    const generateBtn = page.getByTestId('forecast-generate-button');

    const runForRegion = async (regionId: string) => {
      const respPromise = page.waitForResponse(
        (r) => {
          const u = r.url();
          const m = r.request().method();
          return (u.includes('/api/forecast') || (u.includes('8100') && u.includes('forecast'))) && m === 'POST';
        },
        { timeout: 120_000 }
      );
      await regionSelect.selectOption(regionId);
      await expect(generateBtn).toBeEnabled({ timeout: 15_000 });
      await generateBtn.click();
      const resp = await respPromise;
      const data = await resp.json();
      return extractBiAndSubindices(data);
    };

    const mn = await runForRegion('us_mn');
    const ca = await runForRegion('us_ca');

    const diag: string[] = [];
    diag.push(
      'Region | behavior_index | ' + REGIONAL_INDICES.join(' | ')
    );
    diag.push(
      'MN | ' +
        [
          mn.behavior_index ?? '',
          ...REGIONAL_INDICES.map((k) => mn.sub_indices[k] ?? ''),
        ].join(' | ')
    );
    diag.push(
      'CA | ' +
        [
          ca.behavior_index ?? '',
          ...REGIONAL_INDICES.map((k) => ca.sub_indices[k] ?? ''),
        ].join(' | ')
    );

    const biDiffer =
      mn.behavior_index != null &&
      ca.behavior_index != null &&
      mn.behavior_index !== ca.behavior_index;
    let regionalDiffer = false;
    for (const k of REGIONAL_INDICES) {
      const a = mn.sub_indices[k];
      const b = ca.sub_indices[k];
      if (typeof a === 'number' && typeof b === 'number' && a !== b) {
        regionalDiffer = true;
        break;
      }
    }

    if (!biDiffer && !regionalDiffer) {
      // eslint-disable-next-line no-console
      console.log('Diagnostic table:\n' + diag.join('\n'));
      expect(
        biDiffer || regionalDiffer,
        'MN vs CA: behavior_index or at least one REGIONAL sub-index must differ'
      ).toBe(true);
    }
  });
});
