import { test, expect, APIRequestContext } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

let experiment: string;
let runIds: string[] = [];
const api = 'http://127.0.0.1:8000/api';

async function finished(request: APIRequestContext, id: string) {
  await expect.poll(async () => (await (await request.get(`${api}/experiments/${id}`)).json()).status, { timeout: 20000 }).not.toMatch(/queued|running/);
  return (await request.get(`${api}/experiments/${id}`)).json();
}

test.describe('Real backend research workflow', () => {
  test.beforeAll(async ({ request }) => {
    if (!experiment) {
      const response = await request.post(`${api}/demo`);
      expect(response.status()).toBe(201);
      experiment = (await response.json()).id;
      runIds = (await finished(request, experiment)).runs.map((run: { id: string }) => run.id);
    }
  });
  test('first-run guide explains demonstration, real systems and limitations', async ({ page }) => {
    await page.goto('/docs');
    await expect(page.getByRole('heading', { name: 'Documentation', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Your first experiment' })).toBeVisible();
    await expect(page.getByText('Demo results', { exact: false }).first()).toBeVisible();
    await page.screenshot({ path: 'docs/evidence/onboarding-desktop.png', fullPage: true });
  });

  test('offline demonstration queues real execution and retains rejected results', async ({ page, request }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Run offline demonstration' }).click();
    await expect(page).toHaveURL(/experiments\?id=/);
    experiment = new URL(page.url()).searchParams.get('id')!;
    const detail = await finished(request, experiment);
    expect(detail.status).toBe('completed');
    expect(detail.runs).toHaveLength(2);
    runIds = detail.runs.map((run: { id: string }) => run.id);
    const runs = await Promise.all(runIds.map(async id => (await request.get(`${api}/runs/${id}`)).json()));
    expect(runs.flatMap(run => run.results).some(result => result.passed)).toBe(true);
    expect(runs.flatMap(run => run.results).some(result => !result.passed)).toBe(true);
    await expect(page.getByRole('heading', { name: 'Live run monitor' })).toBeVisible();
    await page.screenshot({ path: 'docs/evidence/live-results-desktop.png', fullPage: true });
  });

  test('refresh rehydrates persisted experiment state', async ({ page }) => {
    await page.goto(`/experiments?id=${experiment}`);
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Offline verification demonstration', exact: true })).toBeVisible();
    await expect(page.getByText('Execution stopped', { exact: false })).toBeVisible();
  });

  test('model registration validates credential references and saves configuration', async ({ page, request }) => {
    await page.goto('/models');
    await page.getByRole('button', { name: /Register model/ }).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByLabel('Display name').fill('Browser protocol fixture');
    await dialog.getByLabel('Provider model identifier').fill('fixture-model');
    await dialog.getByLabel('Endpoint base URL').fill('http://127.0.0.1:65530/v1');
    await dialog.getByLabel('API key environment variable').fill('sk-invalid-key');
    await dialog.getByRole('button', { name: 'Register configuration' }).click();
    await expect(dialog.getByText('Use an environment variable name, never a secret value.')).toBeVisible();
    await dialog.getByLabel('API key environment variable').fill('');
    await dialog.getByRole('button', { name: 'Register configuration' }).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByText('Browser protocol fixture', { exact: true }).first()).toBeVisible();
    const models = await (await request.get(`${api}/models`)).json();
    expect(models.some((row: any) => row.config.name === 'Browser protocol fixture')).toBe(true);
  });

  test('agent registration saves a clearly marked deterministic configuration', async ({ page }) => {
    await page.goto('/agents');
    await page.getByRole('button', { name: /Register agent/ }).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByLabel('Display name').fill('Browser demo agent');
    await dialog.getByRole('combobox', { name: 'Adapter', exact: true }).selectOption('demo');
    await dialog.getByLabel('Explicit demonstration configuration').check();
    await dialog.getByRole('button', { name: 'Register configuration' }).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByText('Browser demo agent', { exact: true }).first()).toBeVisible();
  });

  test('benchmark library filters public tasks and exposes requirements', async ({ page }) => {
    await page.goto('/benchmarks');
    await expect(page.getByRole('heading', { name: 'Benchmark library', exact: true })).toBeVisible();
    await expect(page.getByText('BenchLab public starter', { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/Docker/).first()).toBeVisible();
    await page.screenshot({ path: 'docs/evidence/benchmarks-desktop.png', fullPage: true });
  });

  test('experiment builder gates launch on backend compatibility validation', async ({ page, request }) => {
    await page.goto('/experiments/new?model=demo-reference');
    await page.getByLabel('Experiment name', { exact: true }).fill('Browser controlled experiment');
    await expect(page.getByRole('button', { name: 'Launch experiment', exact: true })).toBeDisabled();
    await page.getByRole('button', { name: 'Validate compatibility' }).click();
    await expect(page.getByRole('button', { name: 'Launch experiment', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: 'Launch experiment', exact: true }).click();
    await expect(page).toHaveURL(/experiments\?id=/);
    const id = new URL(page.url()).searchParams.get('id')!;
    expect((await finished(request, id)).status).toBe('completed');
  });

  test('cancellation persists while execution is active', async ({ page, request }) => {
    const source = (await request.get(`${api}/experiments/${experiment}`));
    const config = (await source.json()).config;
    const response = await request.post(`${api}/experiments`, { data: { ...config, name: 'Browser cancellation', trials: 50 } });
    expect(response.status()).toBe(201);
    const row = await response.json();
    await page.goto(`/experiments?id=${row.id}`);
    await page.getByRole('button', { name: 'Cancel experiment' }).click();
    expect((await finished(request, row.id)).status).toBe('cancelled');
    await page.reload();
    await expect(page.getByText('cancelled', { exact: true }).first()).toBeVisible();
  });

  test('comparison renders matched conditions, intervals and task failures', async ({ page }) => {
    await page.goto(`/compare?runs=${runIds.join(',')}`);
    await expect(page.getByText('Matched experimental conditions', { exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: '95% Wilson intervals' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Per-task evidence' })).toBeVisible();
    await page.screenshot({ path: 'docs/evidence/comparison-desktop.png', fullPage: true });
  });

  test('execution replay filters events and inspects protected verification evidence', async ({ page }) => {
    await page.goto(`/replay?run=${runIds[1]}`);
    await expect(page.getByRole('heading', { name: 'Event timeline' })).toBeVisible();
    await page.getByRole('tab', { name: 'Verification', exact: true }).click();
    await expect(page.getByRole('tabpanel')).toContainText('Inventory reconciliation');
    await page.getByRole('tab', { name: 'Manifest', exact: true }).click();
    await expect(page.getByRole('tabpanel')).toContainText('condition_fingerprint');
    await page.getByRole('tab', { name: 'Event', exact: true }).click();
    const options = await page.getByLabel('Filter event type').locator('option').allTextContents();
    expect(options.length).toBeGreaterThan(1);
    await page.getByLabel('Filter event type').selectOption({ label: options[1] });
    await expect(page.locator('.event-button').first()).toBeVisible();
    await page.locator('.event-button').first().click();
    await page.screenshot({ path: 'docs/evidence/replay-desktop.png', fullPage: true });
  });

  test('optimization clones an immutable baseline and executes candidate', async ({ page, request }) => {
    await page.goto(`/optimize?baseline=${experiment}`);
    await page.getByLabel('Candidate name').fill('Browser ablation');
    await page.getByLabel('Hypothesis').fill('Lower token ceiling retains demo verifier behavior; demo does not estimate intelligence.');
    await page.getByRole('button', { name: 'Validate changes' }).click();
    await expect(page.getByRole('button', { name: 'Clone and launch ablation' })).toBeEnabled();
    await page.getByRole('button', { name: 'Clone and launch ablation' }).click();
    await expect(page).toHaveURL(/experiments\?id=/);
    const id = new URL(page.url()).searchParams.get('id')!;
    expect((await finished(request, id)).config.baseline_id).toBe(experiment);
  });

  test('JSON/CSV/HTML/ZIP evidence downloads are genuine backend responses', async ({ page, request }) => {
    await page.goto(`/experiments?id=${experiment}`);
    for (const format of ['JSON', 'CSV', 'HTML', 'ZIP']) {
      const download = page.waitForEvent('download');
      await page.getByRole('link', { name: format, exact: true }).click();
      const file = await download;
      expect(file.suggestedFilename()).toMatch(new RegExp(`\\.${format.toLowerCase()}$`));
      expect(await file.failure()).toBeNull();
    }
    const data = await (await request.get(`${api}/experiments/${experiment}/report?format=json`)).json();
    expect(data.experiment.demo).toBe(true);
    expect(data.runs.every((run: any) => run.results.length === 8)).toBe(true);
  });

  test('settings validates configuration import without executing it', async ({ page, request }) => {
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: 'Runtime diagnostics' })).toBeVisible();
    const before = (await (await request.get(`${api}/experiments`)).json()).length;
    await page.getByLabel('Experiment JSON').fill(JSON.stringify({ name: 'Imported only', systems: [{ model_id: 'demo-reference' }], demo: true }));
    await page.getByRole('button', { name: 'Validate import' }).click();
    await expect(page.getByText('Configuration is schema-valid.', { exact: false })).toBeVisible();
    expect((await (await request.get(`${api}/experiments`)).json()).length).toBe(before);
  });

  test('search empty state and missing record errors remain actionable', async ({ page }) => {
    await page.goto('/models');
    await page.getByRole('textbox', { name: /Search/ }).fill('no-such-configuration');
    await expect(page.getByText('No matching configurations', { exact: true })).toBeVisible();
    await page.goto('/experiments?id=missing');
    await expect(page.getByText('Resource not found', { exact: true })).toBeVisible();
  });

  test('all twelve routes render at 1440/1024/768/390 without viewport overflow', async ({ page }) => {
    test.setTimeout(180000);
    const routes = ['/', '/models', '/agents', '/benchmarks', '/experiments/new', '/experiments', '/compare', '/replay', '/optimize', '/reports', '/settings', '/docs'];
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    for (const width of [1440, 1024, 768, 390]) {
      await page.setViewportSize({ width, height: 900 });
      for (const route of routes) {
        await page.goto(route);
        await expect(page.locator('main h1')).toBeVisible();
        await expect(page.getByRole('status', { name: 'Loading workspace data' })).toHaveCount(0);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${route} at ${width}`).toBe(true);
      }
      await page.goto('/');
      await expect(page.locator('main h1')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Experiment activity', exact: true })).toBeVisible();
      await page.screenshot({ path: `docs/evidence/overview-${width}.png`, fullPage: true });
      if (width === 390) {
        await page.getByRole('button', { name: /navigation|menu/i }).first().click();
        await expect(page.getByRole('dialog')).toBeVisible();
        await page.getByRole('dialog').getByRole('link', { name: 'Comparison studio', exact: true }).click();
        await expect(page).toHaveURL('/compare');
        await expect(page.getByRole('dialog')).not.toBeVisible();
      }
    }
    expect(errors).toEqual([]);
  });

  test('keyboard access and axe WCAG scan on the overview, builder and replay', async ({ page }) => {
    test.setTimeout(90000);
    for (const path of ['/', '/experiments/new', `/replay?run=${runIds[0]}`]) {
      await page.goto(path);
      await expect(page.locator('main h1')).toBeVisible();
      await page.getByRole('link', { name: 'Skip to content' }).focus();
      await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
      const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
      expect(result.violations, JSON.stringify(result.violations, null, 2)).toEqual([]);
    }
  });
});
