import { chromium } from 'playwright';

const base = process.argv[2] || 'http://127.0.0.1:8899';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 1400 } });

const errors = [];
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push('PAGEERROR ' + e.message));

await page.goto(base + '/index.html', { waitUntil: 'networkidle' });
await page.waitForTimeout(800);

const cards = await page.locator('.card').count();
const imgs = await page.evaluate(() =>
  Array.from(document.images).map(i => ({
    src: i.getAttribute('src'),
    ok: i.complete && i.naturalWidth > 0,
    w: i.naturalWidth,
    h: i.naturalHeight,
  }))
);
const links = await page.evaluate(() =>
  Array.from(document.querySelectorAll('a.open')).map(a => a.getAttribute('href'))
);

console.log('cards:', cards);
console.log('images:', JSON.stringify(imgs, null, 1));
console.log('links:', links.join(', '));
console.log('console errors:', errors.length, errors.slice(0, 5));

await page.screenshot({ path: 'results/gallery-index.png', fullPage: true });

// open each scene link and check it renders something on canvas
for (const href of links) {
  const p2 = await browser.newPage({ viewport: { width: 960, height: 540 } });
  const errs = [];
  p2.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  p2.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  await p2.goto(base + '/' + href, { waitUntil: 'load' });
  await p2.waitForTimeout(4000);
  const info = await p2.evaluate(() => {
    const c = document.querySelector('canvas');
    return c ? { w: c.width, h: c.height } : null;
  });
  console.log(href, 'canvas:', JSON.stringify(info), 'errs:', errs.length, errs.slice(0, 2));
  await p2.close();
}

await browser.close();
