// يصوّر ما يجهّزه «python3 build.py --og» في .og/ :
//   بطاقات المشاركة  → assets/og/<slug>.png
//   صور رسائل البريد → assets/mail/<slug>.jpg  و assets/mail/logo.png
// يحتاج Playwright. التشغيل:  node tools/og.mjs
import { readdirSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
let chromium;
try { ({ chromium } = await import('playwright')); }
catch { ({ chromium } = await import(process.env.PLAYWRIGHT_PATH || '/opt/npm-tools/node_modules/playwright/index.mjs')); }

mkdirSync(join(root, 'assets/og'), { recursive: true });
mkdirSync(join(root, 'assets/mail'), { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage();
const files = readdirSync(join(root, '.og')).filter(f => f.endsWith('.html'));
for (const f of files) {
  const name = f.replace('.html', '');
  let size = { width: 1200, height: 630 }, out = join(root, 'assets/og', name + '.png'), opts = {};
  if (name === 'mail-logo') { size = { width: 240, height: 220 }; out = join(root, 'assets/mail/logo.png'); opts = { omitBackground: true }; }
  else if (name.startsWith('mail-')) { size = { width: 1200, height: 675 }; out = join(root, 'assets/mail', name.slice(5) + '.jpg'); opts = { type: 'jpeg', quality: 84 }; }
  await page.setViewportSize(size);
  await page.goto('file://' + join(root, '.og', f));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(200);
  await page.screenshot({ path: out, ...opts });
}
await browser.close();
console.log(`✓ صُوّر ${files.length} ملفًا`);
