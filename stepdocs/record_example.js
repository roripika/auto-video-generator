// Playwright step recorder.
// Usage:
//   cd stepdocs && npm install
//   npm run record -- --scenario=stepdocs/scenarios/sample.json

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const OUT_DIR = path.resolve(__dirname, '../docs/stepdocs');
const SHOT_DIR = path.join(OUT_DIR, 'screenshots');
const STEPS_JSON = path.join(OUT_DIR, 'steps.json');
const DEFAULT_SCENARIO = path.resolve(__dirname, 'scenarios/sample.json');

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
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

function aAfter(str, prefix) {
  return str.slice(prefix.length);
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
    const url = this.page.url();
    let title = '';
    try {
      title = await this.page.title();
    } catch (e) {
      title = '';
    }
    const timestamp = new Date().toISOString();
    this.steps.push({ id: this.stepNo, timestamp, url, title, action, target, note, screenshot: relPath });
  }

  save() {
    ensureDir(SHOT_DIR);
    fs.writeFileSync(STEPS_JSON, JSON.stringify({ steps: this.steps }, null, 2), 'utf-8');
  }
}

async function runAction(page, step) {
  const { action, target, value, note } = step;
  switch (action) {
    case 'goto':
      await page.goto(target, { waitUntil: 'load' });
      break;
    case 'click':
      await page.locator(target).first().click({ timeout: step.timeout || 15000 });
      break;
    case 'fill':
      await page.locator(target).first().fill(value ?? '', { timeout: step.timeout || 15000 });
      break;
    case 'waitForSelector':
      await page.locator(target).first().waitFor({ state: step.state || 'visible', timeout: step.timeout || 15000 });
      break;
    default:
      throw new Error(`Unsupported action: ${action}`);
  }
  return note || '';
}

async function main() {
  const { steps, scenarioPath } = loadScenarioFromArgv();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
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
    await browser.close();
  }
}

if (require.main === module) {
  main().catch((err) => {
    console.error(
      '[stepdocs] シナリオを実行中にエラーが発生しました。scenarios/*.json をアプリ操作用に編集してください。エラー:',
      err && err.message ? err.message : err
    );
    process.exit(1);
  });
}
