// Checks the player's sound: MP3 decoder delay, seamless joins between the
// 30 s pieces, and that playback keeps the audio clock and picture in step.
import { chromium } from 'playwright';
import http from 'http';
import fs from 'fs';
import path from 'path';
const root = path.resolve('build/artifact');
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.mp3': 'audio/mpeg' };
const srv = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]); if (p === '/') p = '/index.html';
  const f = path.join(root, p);
  if (!fs.existsSync(f)) { res.writeHead(404); res.end(); return; }
  let body = fs.readFileSync(f);
  if (p === '/index.html') body = '<!doctype html><html><head><meta charset="utf-8"></head><body>' + body + '</body></html>';
  res.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); res.end(body);
}).listen(8778);
const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
page.on('pageerror', e => console.log('[err]', e.message));
page.on('console', m => { if (m.type() !== 'log') console.log('[page]', m.type(), m.text()); });
await page.route('https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js', r => r.fulfill({ path: 'web/node_modules/three/build/three.module.js', contentType: 'text/javascript' }));
await page.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
await page.goto('http://127.0.0.1:8778/');
// 1. decoder delay + seam continuity, measured the way the page does it
const r = await page.evaluate(async () => {
  const ctx = new AudioContext();
  const dec = async u => { const b = await (await fetch(u)).arrayBuffer(); return await ctx.decodeAudioData(b); };
  const meta = await (await fetch('audio/meta.json')).json();
  const sync = await dec('audio/sync.mp3');
  const d = sync.getChannelData(0); let im = 0;
  for (let i = 1; i < d.length; i++) if (Math.abs(d[i]) > Math.abs(d[im])) im = i;
  const delay = im / sync.sampleRate - meta.sync;
  const out = { rate: ctx.sampleRate, delay, seams: [] };
  for (const k of [3, 20]) {
    const a = await dec(`audio/c${String(k).padStart(3, '0')}.mp3`), b = await dec(`audio/c${String(k + 1).padStart(3, '0')}.mp3`);
    const sr = a.sampleRate, n = Math.round(0.05 * sr);
    const ia = Math.round((delay + meta.pad + meta.chunk) * sr), ib = Math.round((delay + meta.pad) * sr);
    const A = a.getChannelData(0), B = b.getChannelData(0);
    let err = 0, pow = 0;
    for (let i = 0; i < n; i++) { err += (A[ia + i] - B[ib + i]) ** 2; pow += A[ia + i] ** 2; }
    // same comparison 1 ms off, to show the alignment is what matters
    let err1 = 0; const o = Math.round(0.001 * sr);
    for (let i = 0; i < n; i++) err1 += (A[ia + i] - B[ib + i + o]) ** 2;
    out.seams.push({ k, rel_err: Math.sqrt(err / (pow + 1e-12)), rel_err_1ms_off: Math.sqrt(err1 / (pow + 1e-12)), rms: Math.sqrt(pow / n) });
  }
  return out;
});
console.log(JSON.stringify(r));
// 2. play from scene 5 for a while: audio clock vs picture, no errors
await page.waitForFunction(() => !document.getElementById('bigplay').disabled, null, { timeout: 180000 });
await page.click('#chap li:nth-child(5) button');
await page.waitForTimeout(6000);
const s1 = await page.evaluate(() => document.getElementById('cur').textContent);
await page.waitForTimeout(34000);   // crosses a piece boundary
const s2 = await page.evaluate(() => document.getElementById('cur').textContent);
await page.click('#pp');
console.log('time shown', s1, '->', s2);
await page.screenshot({ path: process.argv[2] || 'build/test_audio.png' });
await browser.close(); srv.close();
