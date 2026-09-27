// Local smoke test of build/artifact: serves it, maps the three.js CDN import to the local copy.
import { chromium } from 'playwright';
import http from 'http';
import fs from 'fs';
import path from 'path';
const root = path.resolve('build/artifact');
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.m4a': 'audio/mp4' };
const srv = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]); if (p === '/') p = '/index.html';
  const f = path.join(root, p);
  if (!fs.existsSync(f)) { res.writeHead(404); res.end(); return; }
  let body = fs.readFileSync(f);
  if (p === '/index.html') body = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + body + '</body></html>';
  res.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); res.end(body);
}).listen(8777);
const [, , out, w = '1280', h = '1500', seekScene = ''] = process.argv;
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on('pageerror', e => console.log('[err]', e.message));
page.on('console', m => { if (m.type() !== 'log') console.log('[page]', m.type(), m.text()); });
await page.route('https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js', r => r.fulfill({ path: 'web/node_modules/three/build/three.module.js', contentType: 'text/javascript' }));
await page.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
await page.goto('http://127.0.0.1:8777/');
await page.waitForFunction(() => !document.getElementById('bigplay').disabled, null, { timeout: 180000 });
await page.waitForTimeout(500);
await page.screenshot({ path: out.replace('.png', '_rest.png'), fullPage: true });
if (seekScene) {
  await page.click(`#chap li:nth-child(${seekScene}) button`);
  await page.waitForTimeout(2500);
  await page.click('#pp');
  await page.waitForTimeout(400);
}
await page.screenshot({ path: out, fullPage: false });
await browser.close(); srv.close();
