const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const baseDir = __dirname;
  const stepsPath = path.join(baseDir, 'steps.json');
  const logPath = path.join(baseDir, 'replay.log');
  const screenshotsDir = path.join(baseDir, 'screenshots');

  if (!fs.existsSync(stepsPath)) {
    console.error('steps.json が見つかりません:', stepsPath);
    process.exit(1);
  }

  if (!fs.existsSync(screenshotsDir)) fs.mkdirSync(screenshotsDir, { recursive: true });

  const raw = fs.readFileSync(stepsPath, 'utf8');
  let data = null;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    console.error('steps.json の解析に失敗しました:', e);
    process.exit(1);
  }

  const steps = data.steps || [];
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // selector mapping for legacy or recorded selectors that differ from current DOM
  const selectorMap = {
    '#scriptBrief': '#aiBriefInput'
  };

  for (let i = 0; i < steps.length; i++) {
    const step = steps[i];
    const id = step.id || i + 1;
    const action = step.action;
    let target = step.target;
    if (target && selectorMap[target]) target = selectorMap[target];
    const screenshotRel = step.screenshot || `screenshots/step${String(id).padStart(2,'0')}.png`;
    const screenshotPath = path.join(baseDir, screenshotRel);
    try {
      if (action === 'goto') {
        // Use step.url if present, otherwise try to map app:// to file URL
        let url = step.url || step.target;
        if (!url) throw new Error('goto に URL がありません');
        if (url.startsWith('app://')) {
          // fallback to steps.json's file url if present in step
          if (step.url && step.url.startsWith('file://')) url = step.url;
        }
        console.log(`[${id}] goto ${url}`);
        await page.goto(url, { timeout: 30000 });
      } else if (action === 'waitForSelector') {
        console.log(`[${id}] waitForSelector ${target}`);
        await page.waitForSelector(target, { timeout: 30000 });
      } else if (action === 'click') {
        console.log(`[${id}] click ${target}`);
        await page.click(target, { timeout: 30000 });
      } else if (action === 'fill') {
        // Try to extract a value; fallback to placeholder text
        let value = step.value || step.input || step.note || '自動入力テスト';
        // If note contains an error message, replace with sensible default
        if (/Action failed|Timeout/.test(value)) value = '自動入力テスト';
        console.log(`[${id}] fill ${target} -> ${value}`);
        // try to wait for the selector first with an extended timeout
        await page.waitForSelector(target, { timeout: 30000 });
        await page.fill(target, value, { timeout: 30000 });
      } else {
        console.log(`[${id}] 未対応のアクション: ${action}`);
      }

      // Ensure screenshot directory exists for the step path
      const stepDir = path.dirname(screenshotPath);
      if (!fs.existsSync(stepDir)) fs.mkdirSync(stepDir, { recursive: true });
      await page.screenshot({ path: screenshotPath, fullPage: true });
      fs.appendFileSync(logPath, `${new Date().toISOString()} [INFO] step ${id} ${action} ok -> ${screenshotRel}\n`);
    } catch (err) {
      console.error(`[${id}] エラー:`, err.message);
      fs.appendFileSync(logPath, `${new Date().toISOString()} [ERROR] step ${id} ${action} failed: ${err.stack}\n`);
      // continue to next step
    }
  }

  await browser.close();
  console.log('再生完了。ログ:', logPath);
})();
