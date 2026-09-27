// Render a tick range of the film to an MP4 segment.
// usage: node web/capture.mjs <startTick> <endTick> <fps> <w> <h> <out.mp4>
import { chromium } from 'playwright';
import { spawn } from 'child_process';
const [,, a, b, fps, w, h, out] = process.argv;
const start = +a, end = +b, FPS = +fps;
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on('pageerror', e => console.log('[err]', e.message));
await page.goto(`http://127.0.0.1:8765/web/film.html?w=${w}&h=${h}`);
await page.waitForFunction('window.READY === true', null, { timeout: 180000 });
const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
const n = Math.round((end - start) / 20 * FPS);
const t0 = Date.now();
for (let i = 0; i < n; i++) {
  const tick = start + i * 20 / FPS;
  await page.evaluate(t => window.renderTick(t), tick);
  const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % 200 === 0) console.log(`${out}: ${i}/${n} frames, ${((Date.now() - t0) / 1000 / (i + 1)).toFixed(3)} s/frame`);
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));
await browser.close();
console.log(`${out}: done ${n} frames in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
