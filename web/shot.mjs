// usage: node web/shot.mjs <url-path+query> <out.png> [w] [h]
import { chromium } from 'playwright';
const [,, path, out, w = '1200', h = '520'] = process.argv;
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on('console', m => console.log('[page]', m.text()));
page.on('pageerror', e => console.log('[err]', e.message));
await page.goto('http://127.0.0.1:8765' + path);
await page.waitForFunction('window.READY === true', null, { timeout: 60000 });
await page.waitForTimeout(300);
await page.screenshot({ path: out });
await browser.close();
