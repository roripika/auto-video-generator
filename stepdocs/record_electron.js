// Playwright + Electron で操作を自動再生してスクリーンショットを保存するスクリプト
// 使い方（例）:
//   cd stepdocs
//   npm install && npx playwright install   # 初回のみ
//   node record_electron.js --scenario=stepdocs/scenarios/02_basic_flow.json

const fs = require('fs');
const path = require('path');
const { _electron: electron } = require('playwright');

const OUT_DIR = path.resolve(__dirname, '../docs/stepdocs');
const SHOT_DIR = path.join(OUT_DIR, 'screenshots');
const STEPS_JSON = path.join(OUT_DIR, 'steps.json');
const DEFAULT_SCENARIO = path.resolve(__dirname, 'scenarios/02_basic_flow.json');

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function aAfter(str, prefix) {
  return str.slice(prefix.length);
}

function loadScenarioFromArgv() {
  const arg = process.argv.find((a) => a.startsWith('--scenario='));
  const scenarioPath = arg ? aAfter(arg, '--scenario=') : DEFAULT_SCENARIO;
  const resolved = path.resolve(process.cwd(), scenarioPath);
  if (!fs.existsSync(resolved)) {
    throw new Error(`Scenario file not found: ${resolved}`);
  }
  const json = JSON.parse(fs.readFileSync(resolved, 'utf-8'));
  if (!Array.isArray(json)) {
    throw new Error('Scenario JSON must be an array of steps');
  }
  return { steps: json, scenarioPath: resolved };
}

class StepRecorder {
  constructor(page) {
    this.page = page;
    this.steps = [];
    this.stepNo = 0;
  }

  async snap({ action, target, note }) {
    this.stepNo += 1;
    const id = String(this.stepNo).padStart(2, '0');
    const file = `step${id}.png`;
    const relPath = `screenshots/${file}`;
    const absPath = path.join(SHOT_DIR, file);
    await this.page.screenshot({ path: absPath, fullPage: true });
    let title = '';
    try {
      title = await this.page.title();
    } catch (e) {
      title = '';
    }
    const url = this.page.url();
    const timestamp = new Date().toISOString();
    this.steps.push({ id: this.stepNo, timestamp, url, title, action, target, note, screenshot: relPath });
  }

  save() {
    ensureDir(SHOT_DIR);
    fs.writeFileSync(STEPS_JSON, JSON.stringify({ steps: this.steps }, null, 2), 'utf-8');
  }
}

async function runAction(page, step) {
  const { action, target, value, note, state } = step;
  console.log(`[action] ${action} target=${target || ''} value=${value || ''} state=${state || ''}`);
  switch (action) {
    case 'snap':
      // custom no-op action to record a screenshot via recorder.snap in the main loop
      return note || '';
    case 'goto': // Electronでは基本不要
      return note || '';
    case 'click':
      await page.locator(target).first().click({ timeout: step.timeout || 15000 });
      break;
    case 'fill':
      await page.locator(target).first().fill(value ?? '', { timeout: step.timeout || 15000 });
      break;
    case 'check':
      await page.locator(target).first().check({ timeout: step.timeout || 15000 });
      break;
    case 'uncheck':
      await page.locator(target).first().uncheck({ timeout: step.timeout || 15000 });
      break;
    case 'select':
      await page.locator(target).first().selectOption(value ?? '', { timeout: step.timeout || 15000 });
      break;
    case 'waitForSelector':
      await page
        .locator(target)
        .first()
        .waitFor({ state: state || 'visible', timeout: step.timeout || 15000 });
      break;
    default:
      throw new Error(`Unsupported action: ${action}`);
  }
  return note || '';
}

async function main() {
  const { steps, scenarioPath } = loadScenarioFromArgv();

  const electronPath =
    process.env.ELECTRON_PATH ||
    require(path.resolve(__dirname, '../desktop-app/node_modules/electron'));

  const appDir = path.resolve(__dirname, '../desktop-app');
  const env = { ...process.env };
  // Playwright やシェルで ELECTRON_RUN_AS_NODE が立っていると起動に失敗するので明示的に外す
  delete env.ELECTRON_RUN_AS_NODE;

  const app = await electron.launch({
    executablePath: electronPath,
    args: ['.'],
    cwd: appDir,
    env,
  });

  const page = await app.firstWindow();
  // attach network and console logging to detect external API calls and runtime logs
  const networkLog = path.join(OUT_DIR, 'replay_network.log');
  try { fs.writeFileSync(networkLog, ''); } catch (e) {}
  page.on('request', (req) => {
    try {
      const line = `${new Date().toISOString()} REQUEST ${req.method()} ${req.url()}\n`;
      fs.appendFileSync(networkLog, line);
    } catch (e) {}
  });
  page.on('response', (res) => {
    try {
      const line = `${new Date().toISOString()} RESPONSE ${res.status()} ${res.url()}\n`;
      fs.appendFileSync(networkLog, line);
    } catch (e) {}
  });
  page.on('console', (msg) => {
    try {
      const line = `${new Date().toISOString()} CONSOLE ${msg.type()} ${msg.text()}\n`;
      fs.appendFileSync(networkLog, line);
    } catch (e) {}
  });
  console.log('[electron] title:', await page.title());
  console.log('[electron] url:', page.url());

  const recorder = new StepRecorder(page);
  try {
    for (const step of steps) {
      let note = '';
      try {
        note = await runAction(page, step);
      } catch (err) {
        await recorder.snap({
          action: step.action || 'unknown',
          target: step.target,
          note: `Action failed: ${err.message || err}`,
        });
        throw err;
      }
      await recorder.snap({ action: step.action || 'unknown', target: step.target, note });
    }
    console.log(`[stepdocs] Finished scenario: ${scenarioPath}`);
  } finally {
    recorder.save();
    await app.close();
  }
}

if (require.main === module) {
  main().catch((err) => {
    console.error(
      '[stepdocs] シナリオを実行中にエラーが発生しました。シナリオ/セレクタを確認してください。エラー:',
      err && err.message ? err.message : err
    );
    process.exit(1);
  });
}
