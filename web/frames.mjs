// usage: node web/frames.mjs <outdir> <w> <h> tick1 tick2 ...   -> outdir/f_<tick>.png
import { chromium } from 'playwright';
import fs from 'fs';
const [,, out, w, h, ...ticks] = process.argv;
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on('pageerror', e => console.log('[err]', e.message));
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text()); });
await page.goto(`http://127.0.0.1:8765/web/film.html?w=${w}&h=${h}${process.env.NOSUB ? '&nosub=1' : ''}`);
await page.waitForFunction('window.READY === true', null, { timeout: 120000 });
for (const t of ticks) {
  await page.evaluate(t => window.renderTick(t), +t);
  await page.waitForTimeout(80);
  await page.screenshot({ path: `${out}/f_${t}.png` });
}
await browser.close();
