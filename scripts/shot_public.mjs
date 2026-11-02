import { chromium } from 'playwright';

const url = process.argv[2];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
await page.goto(url + '/index.html', { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
console.log('title:', await page.title());
console.log('h1:', await page.locator('h1').innerText());
console.log('cards:', await page.locator('.card').count());
await page.screenshot({ path: 'results/gallery-public.png' });
await browser.close();
