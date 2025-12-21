const fs = require('fs');
const path = require('path');

const OUT_MD = path.join(__dirname, '..', '基本操作ガイド_自動生成.md');
const STEPS_JSON = path.join(__dirname, '..', 'steps.json');
const SHOT_DIR = path.join(__dirname, 'screenshots');

function safeReadJSON(p) {
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch (e) {
    console.error('failed to parse', p, e.message);
    return null;
  }
}

function rel(p) {
  return path.relative(path.join(__dirname, '..'), p).replace(/\\/g, '/');
}

function build() {
  const data = safeReadJSON(STEPS_JSON);
  if (!data || !Array.isArray(data.steps)) {
    console.error('no steps found in', STEPS_JSON);
    process.exit(1);
  }
  const steps = data.steps;
  const lines = [];
  lines.push('# 自動生成：基本操作ガイド (stepdocs)');
  lines.push('');
  lines.push('このドキュメントは `stepdocs` の実行結果(`steps.json` と `screenshots/`) から自動生成されました。');
  lines.push('');
  lines.push('---');
  lines.push('');

  steps.forEach((s, idx) => {
    const id = s.id || idx + 1;
    const title = s.title || `Step ${id}`;
    const action = s.action || '';
    const target = s.target || '';
    const note = s.note || '';
    const shot = s.screenshot || `screenshots/step${String(id).padStart(2,'0')}.png`;

    lines.push(`## ${id}. ${title}`);
    lines.push('');
    if (action) lines.push(`- **Action**: ${action}`);
    if (target) lines.push(`- **Target**: ${target}`);
    if (note) lines.push(`- **Note**: ${note.replace(/\n/g, ' ')}`);
    lines.push('');
    const shotPath = path.join(path.dirname(STEPS_JSON), shot);
    if (fs.existsSync(shotPath)) {
      lines.push(`![](${rel(shotPath)})`);
      lines.push('');
    } else {
      lines.push('> スクリーンショットが見つかりません。');
      lines.push('');
    }
  });

  fs.writeFileSync(OUT_MD, lines.join('\n'), 'utf8');
  console.log('wrote', OUT_MD);
}

build();
