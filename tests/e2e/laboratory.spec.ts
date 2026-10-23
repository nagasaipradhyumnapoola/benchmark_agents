import { test, expect, APIRequestContext } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { spawn, ChildProcess } from 'node:child_process';
import { createInterface } from 'node:readline';
import { resolve } from 'node:path';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

let experiment: string;
let runIds: string[] = [];
const api = 'http://127.0.0.1:8000/api';
const python = process.env.BENCH_AGENTS_TEST_PYTHON || (process.platform === 'win32' ? resolve('.venv/Scripts/python.exe') : resolve('.venv/bin/python'));
let provider: ChildProcess;
let providerUrl = '';
let keyedProvider: ChildProcess;
let keyedProviderUrl = '';

async function startProvider(authenticated = false): Promise<[ChildProcess, string]> {
  const child = spawn(python, ['tests/fixtures/browser_provider.py', ...(authenticated ? ['--authenticated'] : [])], { stdio: ['ignore', 'pipe', 'pipe'] });
  const url = await new Promise<string>((accept, reject) => {
    const timer = setTimeout(() => { child.kill(); reject(new Error('Local browser HTTP fixture did not start')); }, 10000);
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('exit', code => { clearTimeout(timer); reject(new Error(`HTTP fixture exited ${code}`)); });
    const lines = createInterface({ input: child.stdout! });
    lines.once('line', line => { clearTimeout(timer); lines.close(); accept(JSON.parse(line).base_url); });
  });
  return [child, url];
}

async function finished(request: APIRequestContext, id: string) {
  await expect.poll(async () => (await (await request.get(`${api}/experiments/${id}`)).json()).status, { timeout: 20000 }).not.toMatch(/queued|running/);
  return (await request.get(`${api}/experiments/${id}`)).json();
}

test.describe('Real backend research workflow', () => {
  test.describe.configure({ mode: 'serial' });
  test.beforeAll(async () => {
    [provider, providerUrl] = await startProvider();
    [keyedProvider, keyedProviderUrl] = await startProvider(true);
  });
  test.afterAll(() => { provider?.kill(); keyedProvider?.kill(); });
  test('fresh workspace starts empty with understandable next steps', async ({ page, request }) => {
    expect(await (await request.get(`${api}/models`)).json()).toEqual([]);
    expect(await (await request.get(`${api}/agents`)).json()).toEqual([]);
    expect(await (await request.get(`${api}/experiments`)).json()).toEqual([]);
    await page.goto('/');
    await expect(page.getByText('No experiments yet', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Register model', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Run offline demonstration' })).toHaveCount(0);
    await page.screenshot({ path: 'docs/evidence/empty-workspace-desktop.png', fullPage: true });
    await page.setViewportSize({ width: 390, height: 900 });
    await page.screenshot({ path: 'docs/evidence/empty-workspace-mobile.png', fullPage: true });
  });
  test('first-run guide explains demonstration, real systems and limitations', async ({ page }) => {
    await page.goto('/docs');
    await expect(page.getByRole('heading', { name: 'Documentation', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Your first experiment' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Optional offline demonstration' })).toBeVisible();
    await page.screenshot({ path: 'docs/evidence/onboarding-desktop.png', fullPage: true });
  });

  test('Agent Hub uses the exact supplied logo and exposes publication and safety rules', async ({ page, request }) => {
    const originalHash = '9601aad360601e8fa7a09d299008a8340d914b366cb86b6c7fc158cb00cc7edc';
    for (const path of ['/agent-hub-logo.png', '/icon.png']) {
      const asset = await request.get(`http://127.0.0.1:3000${path}`);
      expect(asset.status()).toBe(200);
      expect(createHash('sha256').update(await asset.body()).digest('hex')).toBe(originalHash);
    }
    await page.goto('/rules');
    await expect(page).toHaveTitle('Agent Hub — Discover, test and share agents');
    await expect(page.getByRole('heading', { name: 'Rules & safety', exact: true })).toBeVisible();
    await expect(page.getByRole('navigation', { name: 'Rules sections' })).toBeVisible();
    await page.screenshot({ path: 'docs/evidence/rules-desktop.png', fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: 'docs/evidence/rules-mobile.png', fullPage: true });
  });

  test('offline demonstration queues real execution and retains rejected results', async ({ page, request }) => {
    await page.goto('/docs#demonstration');
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
    await expect(page.getByRole('heading', { name: /Live run monitor|Experiment activity/ }).first()).toBeVisible();
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
    await dialog.getByLabel('Display name', { exact: true }).fill('Browser protocol fixture');
    await dialog.getByLabel('Provider model identifier').fill('fixture-model');
    await dialog.getByLabel('Endpoint base URL').fill('http://127.0.0.1:65530/v1');
    await dialog.getByLabel('Authentication', { exact: true }).selectOption('environment');
    await dialog.getByLabel('API key environment variable').fill('sk-invalid-key');
    await dialog.getByRole('button', { name: 'Register configuration' }).click();
    await expect(dialog.getByText('Use an environment variable name, never a secret value.')).toBeVisible();
    await dialog.getByLabel('Authentication', { exact: true }).selectOption('none');
    await dialog.getByRole('button', { name: 'Register configuration' }).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByText('Browser protocol fixture', { exact: true }).first()).toBeVisible();
    const models = await (await request.get(`${api}/models`)).json();
    expect(models.some((row: any) => row.config.name === 'Browser protocol fixture')).toBe(true);
  });

  test('a user connects an endpoint and agent then verifies and exports a real HTTP-backed run', async ({ page, request }) => {
    await page.goto('/models');
    await page.getByRole('button', { name: /Register model/ }).click();
    let dialog = page.getByRole('dialog');
    await dialog.getByLabel('Display name', { exact: true }).fill('Browser HTTP integration fixture');
    await dialog.getByLabel('Provider model identifier').fill('browser-wire-model');
    await dialog.getByLabel('Endpoint base URL').fill(providerUrl);
    await dialog.getByRole('button', { name: 'Register configuration' }).click();
    await expect(dialog).not.toBeVisible();
    await page.getByRole('button', { name: 'Probe compatibility' }).click();
    await expect(page.getByText('Compatibility confirmed', { exact: true })).toBeVisible();
    const models = await (await request.get(`${api}/models`)).json();
    const model = models.filter((row: any) => row.config.name === 'Browser HTTP integration fixture' && row.config.base_url === providerUrl).at(-1);

    await page.goto('/agents');
    await page.getByRole('button', { name: /Register agent/ }).click();
    dialog = page.getByRole('dialog');
    await dialog.getByLabel('Display name', { exact: true }).fill('Browser subprocess HTTP fixture');
    await dialog.getByLabel(/^Executable/).fill(python);
    await dialog.getByLabel(/^Script path \(optional\)/).fill(resolve('examples/adapters/minimal_chat_agent.py'));
    await dialog.getByLabel(/^Model flag/).fill('--model');
    await dialog.getByLabel(/^Model endpoint environment variable/).fill('HARNESS_BASE_URL');
    await dialog.getByLabel(/^Model API key environment variable/).fill('HARNESS_API_KEY');
    await dialog.getByRole('button', { name: 'Register configuration' }).click();
    await expect(dialog).not.toBeVisible();
    const agents = await (await request.get(`${api}/agents`)).json();
    const agent = agents.filter((row: any) => row.config.name === 'Browser subprocess HTTP fixture').at(-1);
    await page.getByRole('button', { name: 'Probe compatibility' }).click();
    await expect(page.getByText('Compatibility confirmed', { exact: true })).toBeVisible();
    await page.getByRole('link', { name: /Build an experiment with this agent/ }).click();
    await page.getByLabel('Experiment name', { exact: true }).fill('Browser real HTTP controlled pairing');
    await page.getByLabel('Shared model for agent evaluation').selectOption(model.id);
    await page.getByRole('button', { name: 'Use one quick text task' }).click();
    await page.getByLabel('Authorize host agent processes for this experiment', { exact: false }).check();
    await page.getByRole('button', { name: 'Validate compatibility' }).click();
    await expect(page.getByRole('button', { name: 'Launch experiment', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: 'Launch experiment', exact: true }).click();
    await expect(page).toHaveURL(/experiments\?id=/);
    const id = new URL(page.url()).searchParams.get('id')!;
    const detail = await finished(request, id);
    expect(detail.status).toBe('completed');
    expect(detail.config.systems).toEqual([expect.objectContaining({ model_id: model.id, agent_id: agent.id })]);
    const run = await (await request.get(`${api}/runs/${detail.runs[0].id}`)).json();
    expect(run.results).toHaveLength(1);
    expect(run.results[0].passed).toBe(true);
    expect(run.manifest.config.demo).toBe(false);
    const stats = await (await request.get(providerUrl.replace('/v1', '/stats'))).json();
    expect(stats.requests).toBe(1);
    expect(stats.models).toEqual(['browser-wire-model']);
    const download = page.waitForEvent('download');
    await page.getByRole('link', { name: 'ZIP', exact: true }).click();
    expect((await download).suggestedFilename()).toMatch(/\.zip$/);
    await page.screenshot({ path: 'docs/evidence/browser-http-agent.png', fullPage: true });
  });

  test('agent registration saves a clearly marked deterministic configuration', async ({ page }) => {
    await page.goto('/agents');
    await page.getByRole('button', { name: /Register agent/ }).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByLabel('Display name', { exact: true }).fill('Browser demo agent');
    await dialog.getByRole('combobox', { name: 'Adapter', exact: true }).selectOption('demo');
    await dialog.getByText('Advanced configuration', { exact: true }).click();
    await dialog.getByLabel('Explicit demonstration configuration').check();
    await dialog.getByRole('button', { name: 'Register configuration' }).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByText('Browser demo agent', { exact: true }).first()).toBeVisible();
  });

  test('a user benchmarks two agents against local and API-key model connections', async ({ page, request }) => {
    await page.goto('/models');
    await page.getByRole('button', { name: /Register model/ }).click();
    let dialog = page.getByRole('dialog');
    await dialog.getByLabel('Display name', { exact: true }).fill('Browser API key integration fixture');
    await dialog.getByLabel('Connection type', { exact: true }).selectOption('hosted');
    await dialog.getByLabel('Provider model identifier').fill('browser-key-model');
    await dialog.getByLabel('Endpoint base URL').fill(keyedProviderUrl);
    await dialog.getByLabel(/^Session API key/).fill('browser-session-fixture-key');
    await dialog.getByRole('button', { name: 'Register configuration' }).click();
    await expect(dialog).not.toBeVisible();
    await page.getByRole('button', { name: 'Probe compatibility' }).click();
    await expect(page.getByText('Compatibility confirmed', { exact: true })).toBeVisible();
    await page.getByLabel(/^Re-enter session API key/).fill('browser-session-fixture-key');
    await page.getByRole('button', { name: 'Update session key', exact: true }).click();
    await expect(page.getByLabel(/^Re-enter session API key/)).toHaveValue('');
    const models = await (await request.get(`${api}/models`)).json();
    const keyed = models.find((row: any) => row.config.name === 'Browser API key integration fixture');
    expect(keyed.config.connection_type).toBe('hosted');
    expect(JSON.stringify(models)).not.toContain('browser-session-fixture-key');
    await page.goto('/agents');
    await page.getByRole('button', { name: /Register agent/ }).click();
    dialog = page.getByRole('dialog');
    await dialog.getByLabel('Display name', { exact: true }).fill('Browser second subprocess fixture');
    await dialog.getByLabel(/^Executable/).fill(python);
    await dialog.getByLabel(/^Script path \(optional\)/).fill(resolve('examples/adapters/minimal_chat_agent.py'));
    await dialog.getByLabel(/^Model flag/).fill('--model');
    await dialog.getByLabel(/^Model endpoint environment variable/).fill('HARNESS_BASE_URL');
    await dialog.getByLabel(/^Model API key environment variable/).fill('HARNESS_API_KEY');
    await dialog.getByRole('button', { name: 'Register configuration' }).click();
    await expect(dialog).not.toBeVisible();
    await page.goto('/experiments/new');
    await page.getByLabel('Experiment name', { exact: true }).fill('Browser two-by-two matrix');
    await page.getByRole('combobox', { name: /^Evaluation mode/ }).selectOption('matrix');
    for (const name of ['Browser HTTP integration fixture', 'Browser API key integration fixture', 'Browser subprocess HTTP fixture', 'Browser second subprocess fixture']) {
      await page.getByRole('checkbox', { name: new RegExp(`^${name}`) }).check();
    }
    await page.getByRole('button', { name: 'Use one quick text task' }).click();
    await expect(page.getByText('4 task checks', { exact: true })).toBeVisible();
    await page.getByLabel('Authorize host agent processes for this experiment', { exact: false }).check();
    await page.getByRole('button', { name: 'Validate compatibility' }).click();
    await expect(page.getByRole('button', { name: 'Launch experiment', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: 'Launch experiment', exact: true }).click();
    await expect(page).toHaveURL(/experiments\?id=/);
    const detail = await finished(request, new URL(page.url()).searchParams.get('id')!);
    expect(detail.status).toBe('completed');
    expect(detail.runs).toHaveLength(4);
    expect(new Set(detail.config.systems.map((pair: any) => `${pair.model_id}:${pair.agent_id}`)).size).toBe(4);
    const runs = await Promise.all(detail.runs.map(async (run: any) => (await request.get(`${api}/runs/${run.id}`)).json()));
    expect(runs.every(run => run.results.length === 1 && run.results[0].passed)).toBe(true);
    expect(JSON.stringify(runs)).not.toContain('browser-session-fixture-key');
    expect((await (await request.get(keyedProviderUrl.replace('/v1', '/stats'))).json()).requests).toBe(2);
    await page.screenshot({ path: 'docs/evidence/matrix-results-desktop.png', fullPage: true });
    await page.goto(`/compare?runs=${detail.runs.map((run: any) => run.id).join(',')}`);
    await expect(page.getByText('Matched experimental conditions', { exact: true })).toBeVisible();
  });

  test('community suggestions stay local until reviewed for manual GitHub submission', async ({ page, request }) => {
    await page.goto('/community');
    await expect(page.getByRole('heading', { name: 'Community', exact: true })).toBeVisible();
    await page.getByRole('combobox', { name: /^Suggestion type/ }).selectOption('agent');
    await page.getByLabel('Title', { exact: true }).fill('Browser community integration fixture');
    await page.getByLabel('Description', { exact: true }).fill('Protocol fixture for testing contribution review, not a published capability claim.');
    await page.getByLabel('Public source URL', { exact: true }).fill('https://github.com/nagasaipradhyumnapoola/benchmark_agents');
    await page.getByLabel('License', { exact: true }).fill('Apache-2.0');
    await page.getByLabel('Suggested models (one exact model name per line)', { exact: true }).fill('browser-wire-model\nbrowser-key-model');
    await page.getByRole('button', { name: 'Save local draft', exact: true }).click();
    await expect(page.getByText('Browser community integration fixture', { exact: true })).toBeVisible();
    await expect(page.getByText('Local draft · unverified', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Open GitHub to submit yourself', exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: 'Review GitHub submission', exact: true }).click();
    const link = page.getByRole('link', { name: 'Open GitHub to submit yourself', exact: true });
    const share = new URL((await link.getAttribute('href'))!);
    expect(share.hostname).toBe('github.com');
    expect(share.searchParams.get('body')).toContain('browser-key-model');
    expect(share.searchParams.get('body')).not.toContain('browser-session-fixture-key');
    const download = page.waitForEvent('download');
    await page.getByRole('link', { name: 'Download contribution JSON', exact: true }).click();
    expect((await download).suggestedFilename()).toMatch(/\.json$/);
    const catalog = await (await request.get(`${api}/community`)).json();
    expect(catalog.published).toEqual([]);
    expect(catalog.drafts).toHaveLength(1);
    await page.screenshot({ path: 'docs/evidence/community-desktop.png', fullPage: true });
  });

  test('developer publishes source, imports it, benchmarks it and shares a versioned result', async ({ page, request }) => {
    test.setTimeout(90000);
    await page.goto('/hub');
    await expect(page.getByRole('heading', { name: 'Agent Hub', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Create account', exact: true }).click();
    await page.getByLabel('Username', { exact: true }).fill('hub-browser-author');
    await page.getByLabel('Password', { exact: true }).fill('local-hub-fixture-password-2026');
    await page.getByRole('button', { name: 'Register account', exact: true }).click();
    await expect(page.getByText('Signed in as hub-browser-author', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Publish an agent', exact: true }).click();
    await page.getByLabel('Agent name', { exact: true }).fill('Browser published harness');
    await page.getByLabel('Slug', { exact: true }).fill('browser-published-harness');
    await page.getByLabel('Version', { exact: true }).fill('1.0.0');
    await page.getByLabel('Summary', { exact: true }).fill('Protocol test release, not an agent capability claim.');
    await page.getByLabel('README', { exact: true }).fill('A public stdin/stdout wrapper used only to verify publish, source import and model binding. Requires a configured OpenAI-compatible endpoint.');
    await page.getByLabel('License', { exact: true }).fill('Apache-2.0');
    await page.getByLabel('Entrypoint', { exact: true }).fill('agent.py');
    await page.getByLabel('Source file path', { exact: true }).fill('agent.py');
    await page.getByLabel('Source code', { exact: true }).fill(readFileSync('examples/adapters/minimal_chat_agent.py', 'utf8'));
    await page.getByLabel(/^Recommended models/).fill('browser-wire-model');
    await page.getByText('Model bindings, arguments and dependencies', { exact: true }).click();
    await page.getByLabel('Model flag (optional)', { exact: true }).fill('--model');
    await page.getByLabel('Model base URL environment variable (optional)', { exact: true }).fill('HARNESS_BASE_URL');
    await page.getByLabel('Model API key environment variable (optional)', { exact: true }).fill('HARNESS_API_KEY');
    await page.getByRole('checkbox', { name: /^I have reviewed the publication rules/ }).check();
    await page.getByRole('button', { name: 'Publish release', exact: true }).click();
    await expect(page).toHaveURL(/agent=browser-published-harness/);
    await expect(page.getByRole('button', { name: 'Import agent', exact: true })).toBeVisible();
    const importedResponse = page.waitForResponse(response => response.url().endsWith('/api/hub/import') && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Import agent', exact: true }).click();
    const imported = await (await importedResponse).json();
    expect(imported.agent.config.adapter).toBe('subprocess');
    expect(imported.source.version).toBe('1.0.0');
    expect(await (await request.get(`${api}/experiments`)).json()).not.toContainEqual(expect.objectContaining({ name: 'Hub imported execution' }));
    await page.screenshot({ path: 'docs/evidence/agent-hub-release-desktop.png', fullPage: true });
    await page.getByRole('link', { name: 'Benchmark imported agent', exact: true }).click();
    await page.getByLabel('Experiment name', { exact: true }).fill('Hub imported execution');
    const models = await (await request.get(`${api}/models`)).json();
    const model = models.find((row: any) => row.config.name === 'Browser HTTP integration fixture');
    await page.getByLabel('Shared model for agent evaluation').selectOption(model.id);
    await page.getByRole('button', { name: 'Use one quick text task' }).click();
    await page.getByLabel('Authorize host agent processes for this experiment', { exact: false }).check();
    await page.getByRole('button', { name: 'Validate compatibility' }).click();
    await expect(page.getByRole('button', { name: 'Launch experiment', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: 'Launch experiment', exact: true }).click();
    await expect(page).toHaveURL(/experiments\?id=/);
    const experimentId = new URL(page.url()).searchParams.get('id')!;
    const detail = await finished(request, experimentId);
    expect(detail.status).toBe('completed');
    const runId = detail.runs[0].id;
    const run = await (await request.get(`${api}/runs/${runId}`)).json();
    expect(run.results[0].passed).toBe(true);
    await page.getByRole('link', { name: /Share this benchmark in Agent Hub/ }).click();
    await expect(page.getByRole('button', { name: 'Share this benchmark result', exact: true })).toBeVisible();
    const sharedResponse = page.waitForResponse(response => response.url().endsWith('/api/hub/share-run') && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Share this benchmark result', exact: true }).click();
    expect((await sharedResponse).status()).toBe(200);
    await expect(page.getByRole('button', { name: 'Benchmark result shared', exact: true })).toBeVisible();
    const reports = await (await request.get(`${api}/hub/agents/browser-published-harness/versions/1.0.0/reports`)).json();
    expect(reports.items).toHaveLength(1);
    expect(reports.items[0]).toMatchObject({ passed: 1, total: 1, model: 'browser-wire-model', self_reported: true });
    expect(JSON.stringify(reports)).not.toContain('browser-session-fixture-key');
    await page.screenshot({ path: 'docs/evidence/agent-hub-result-desktop.png', fullPage: true });
    await page.goto('/hub');
    await expect(page.getByRole('link', { name: 'Browser published harness', exact: true })).toBeVisible();
    await page.screenshot({ path: 'docs/evidence/agent-hub-directory-desktop.png', fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: 'docs/evidence/agent-hub-directory-mobile.png', fullPage: true });
    await page.getByLabel('Search agents', { exact: true }).fill('no-such-agent-filter');
    await page.getByRole('button', { name: 'Search registry', exact: true }).click();
    await expect(page).toHaveURL(/search=no-such-agent-filter/);
    await expect(page.getByText('No agents match these filters', { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Search agents', { exact: true })).toHaveValue('no-such-agent-filter');
    await page.getByRole('button', { name: 'Clear filters', exact: true }).click();
    await expect(page).toHaveURL(/\/hub$/);
    await expect(page.getByRole('link', { name: 'Browser published harness', exact: false })).toBeVisible();
  });

  test('benchmark library filters public tasks and exposes requirements', async ({ page }) => {
    await page.goto('/benchmarks');
    await expect(page.getByRole('heading', { name: 'Benchmark library', exact: true })).toBeVisible();
    await expect(page.getByText('Agent Hub public starter', { exact: true }).first()).toBeVisible();
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

  test('all fifteen routes render at 1440/1024/768/390 without viewport overflow', async ({ page }) => {
    test.setTimeout(180000);
    const routes = ['/', '/models', '/agents', '/benchmarks', '/community', '/hub', '/rules', '/experiments/new', '/experiments', '/compare', '/replay', '/optimize', '/reports', '/settings', '/docs'];
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
    for (const path of ['/', '/experiments/new', '/community', '/hub', '/rules', '/hub?agent=browser-published-harness&version=1.0.0', `/replay?run=${runIds[0]}`]) {
      await page.goto(path);
      await expect(page.locator('main h1')).toBeVisible();
      await page.getByRole('link', { name: 'Skip to content' }).focus();
      await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
      const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
      expect(result.violations, JSON.stringify(result.violations, null, 2)).toEqual([]);
    }
  });
});
