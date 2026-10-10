import { test, expect, type Page } from '@playwright/test';
import type { TalkWalkData, TalkWalkFirm } from '../../src/dataset';

const apiPaths = new WeakMap<Page, string[]>();
const firm = (talk: number | null, walk: number | null, gap: number | null, greenwasher: boolean | null): TalkWalkFirm => ({ firm_id: '0002.HK', year: 2025, talk, walk, gap, greenwasher, greenhusher: greenwasher == null ? null : false });
function response(dictionary: TalkWalkFirm[] = [], semantic: TalkWalkFirm[] = []): TalkWalkData {
  return {
    dataset_id: 'builtin', market: 'all', limitations: [],
    semantic_llm: { kind: 'semantic_llm', scale: '0–10 semantic rubric', firms: semantic, coverage: { firms: semantic.length, documents: 0 }, methodology: { classification: 'not_provided', gap_is_classifier: false } },
    dictionary: { kind: 'dictionary', scale: '0–10 within-sector percentile', firms: dictionary, methodology: { rule: 'high_talk_low_walk', talk_min: 8, walk_max: 10 / 3, gap_is_classifier: false, source: 'esgx.measures.greenwash' } },
  };
}
async function openScores(page: Page, data: TalkWalkData) {
  const paths: string[] = [];
  apiPaths.set(page, paths);
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    paths.push(path);
    if (path === '/api/talk-walk') return route.fulfill({ json: data });
    if (path === '/api/companies') return route.fulfill({ json: [{ id: '0002.HK', ticker: '0002.HK', name: 'CLP Holdings', sector: 'Utilities', industry: 'Utilities', score: 6, weight: 20, g: -80, carbon: 0, talk: null, walk: null, greenwasher: null, greenhusher: null, assessment_status: 'insufficient_data', notes: '', listing_market: 'hk' }] });
    if (path === '/api/data/status') return route.fulfill({ json: { dataset_id: 'builtin', mode: 'snapshot', label: 'Snapshot', is_latest: false, snapshot_date: '2026-08', markets: {}, missing_markets: [], limitations: [] } });
    if (path === '/api/portfolio/filters') return route.fulfill({ json: { sectors: [] } });
    await route.fulfill({ status: 404, json: { detail: 'Unexpected API request in evidence-only test' } });
  });
  await page.goto('/app');
  await page.getByRole('button', { name: 'Talk & Walk', exact: true }).click();
  await page.getByRole('button', { name: /CLP Holdings/ }).click();
  const dictionary = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Dictionary assessment', exact: true }) });
  await expect(dictionary).toContainText(data.dictionary.scale);
  return dictionary;
}

test.afterEach(async ({ page }) => {
  expect(apiPaths.get(page)?.filter(path => /recommend|optim|solve/.test(path)) ?? []).toEqual([]);
});

for (const scenario of [
  { name: 'large gap with Talk below threshold', talk: 6, walk: 1, gap: 5, flag: false },
  { name: 'high Talk with Walk above threshold', talk: 9, walk: 5, gap: 4, flag: false },
  { name: 'high Talk AND weak Walk', talk: 9, walk: 2, gap: 7, flag: true },
]) {
  test(`dictionary preserves server classification: ${scenario.name}`, async ({ page }) => {
    const panel = await openScores(page, response([firm(scenario.talk, scenario.walk, scenario.gap, scenario.flag)]));
    await expect(panel.getByText(`+${scenario.gap.toFixed(2)}`, { exact: true })).toBeVisible();
    await expect(panel.getByText(/within-sector percentile/)).toContainText(scenario.flag ? 'Greenwash signal detected' : 'No signal detected');
    const details = panel.locator('details');
    await expect(details).not.toHaveAttribute('open');
    await expect(panel.getByText('What the company says', { exact: true })).toBeVisible();
    await expect(panel.getByText('Documented action / performance', { exact: true })).toBeVisible();
    await panel.getByText('How to read these scores', { exact: true }).click();
    await expect(details).toContainText('Talk ≥ 8 AND Walk ≤ 10/3 (≈3.33)');
    await expect(details).toContainText('A large gap alone does not trigger');
    await expect(details.getByRole('row', { name: '6 1 +5 No · Talk is below 8' })).toBeVisible();
    await expect(details.getByRole('row', { name: '9 5 +4 No · Walk is above 10/3' })).toBeVisible();
    await expect(details.getByRole('row', { name: '9 2 +7 Yes · Both conditions hold' })).toBeVisible();
  });
}

test('LLM rubric remains unclassified even when its scores meet dictionary thresholds', async ({ page }) => {
  await openScores(page, response([firm(6, 1, 5, false)], [firm(9, 2, 7, null)]));
  const panel = page.locator('section').filter({ has: page.getByRole('heading', { name: 'LLM semantic assessment', exact: true }) });
  await expect(panel.getByText(/0–10 semantic rubric/)).toContainText('signal classification not provided');
  await expect(panel.getByText(/0–10 semantic rubric/)).not.toContainText('Greenwash signal detected');
  await page.getByText('How to read these scores', { exact: true }).click();
  await expect(page.getByText(/These are semantic ratings, not percentile ranks/)).toBeVisible();
  await expect(page.getByText(/Mounted datasets may use other Walk measures/)).toBeVisible();
});

test('rounded scores never replace server flags and supplied thresholds are displayed', async ({ page }) => {
  const data = response([firm(7.9999, 3.3334, 4.6665, false)]);
  data.dictionary.methodology!.talk_min = 9.1;
  data.dictionary.methodology!.walk_max = 1.25;
  const panel = await openScores(page, data);
  await expect(panel.getByText('8.00', { exact: true })).toBeVisible();
  await expect(panel.getByText('3.33', { exact: true })).toBeVisible();
  await expect(panel.getByText(/within-sector percentile/)).toContainText('No signal detected');
  await panel.getByText('How to read these scores', { exact: true }).click();
  await expect(panel.locator('details')).toContainText('Talk ≥ 9.1 AND Walk ≤ 1.25');
  await expect(panel.locator('details')).toContainText('does not recalculate those flags');
});

test('old payload without methodology never invents classification and shows negative gap direction', async ({ page }) => {
  const data = response([firm(2, 9, -7, null)]);
  delete data.dictionary.methodology;
  delete data.semantic_llm.methodology;
  const panel = await openScores(page, data);
  await expect(panel.getByText('-7.00', { exact: true })).toBeVisible();
  await expect(panel.getByText('Talk − Walk · + Talk higher / − Walk higher', { exact: true })).toBeVisible();
  await expect(panel.getByText(/within-sector percentile/)).toContainText('signal classification not provided');
  await panel.getByText('How to read these scores', { exact: true }).click();
  await expect(panel.locator('details')).toContainText('Reference engine dictionary rule');
  await expect(panel.locator('details')).toContainText('has not supplied supported classifier thresholds');
});

test('missing scores stay insufficient even with flags present', async ({ page }) => {
  const panel = await openScores(page, response([firm(9, null, null, true)]));
  await expect(panel.getByText(/within-sector percentile/)).toContainText('Insufficient data');
  await expect(panel.getByText(/within-sector percentile/)).not.toContainText('Greenwash signal detected');
  await expect(page.getByText(/No stored LLM assessment is available/)).toBeVisible();
});

test('collapsed and expanded explanation fits a mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const panel = await openScores(page, response([firm(9, 2, 7, true)], [firm(6, 9, -3, null)]));
  await expect(panel.locator('details')).not.toHaveAttribute('open');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  await panel.getByText('How to read these scores', { exact: true }).click();
  await expect(panel.getByRole('row', { name: '9 2 +7 Yes · Both conditions hold' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  await page.screenshot({ path: 'output/playwright/talk-walk-explanation-mobile.png', fullPage: true });
});
