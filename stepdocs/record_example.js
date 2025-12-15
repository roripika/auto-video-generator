// A minimal Playwright recorder that captures screenshots and step metadata.
// Usage:
//   cd stepdocs
//   npm install
//   npm run record

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const OUT_DIR = path.resolve(__dirname, '../docs/stepdocs');
const SHOT_DIR = path.join(OUT_DIR, 'screenshots');
const STEPS_JSON = path.join(OUT_DIR, 'steps.json');

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
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

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const recorder = new StepRecorder(page);
  try {
    // Step 1: Open example.com
    await page.goto('https://example.com');
    await recorder.snap({ action: 'goto', target: 'https://example.com', note: 'Open Example home page' });

    // Step 2: Try to click the More information link; fall back to just capture if not found
    const moreInfo = page.locator('text=More information').first();
    try {
      await moreInfo.waitFor({ state: 'visible', timeout: 15000 });
      await moreInfo.click({ timeout: 5000 });
      await recorder.snap({ action: 'click', target: 'text=More information', note: 'Go to IANA page' });
    } catch (e) {
      await recorder.snap({
        action: 'capture',
        target: 'text=More information',
        note: 'Link not found or not clickable; captured current page instead',
      });
    }
  } finally {
    recorder.save();
    await browser.close();
  }
}

if (require.main === module) {
  main().catch((err) => {
    console.error('Recorder failed:', err);
    process.exit(1);
  });
}
