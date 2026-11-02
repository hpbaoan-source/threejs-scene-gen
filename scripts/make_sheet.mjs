// Pack one or more renders into a single side-by-side comparison sheet.
//
//   node scripts/make_sheet.mjs <out.png> <label=path.png> [<label=path.png> ...]
//
// The review loop shows the model ONE image per round, so the sheet is what
// the model actually looks at: each attempt labelled, next to each other.
// Built in the browser (no image library needed) by laying the PNGs out in a
// simple HTML page and screenshotting it.

import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [, , outPath, ...pairs] = process.argv;
if (!outPath || pairs.length === 0) {
  console.error("usage: node make_sheet.mjs <out.png> <label=path.png> [...]");
  process.exit(2);
}

const items = pairs.map((p) => {
  const idx = p.indexOf("=");
  const label = idx >= 0 ? p.slice(0, idx) : path.basename(p);
  const file = idx >= 0 ? p.slice(idx + 1) : p;
  const data = fs.readFileSync(file).toString("base64");
  return { label, src: `data:image/png;base64,${data}` };
});

const html = `<!doctype html>
<html><head><meta charset="utf-8"><style>
  * { box-sizing: border-box; }
  body { margin: 0; background: #111; font-family: system-ui, sans-serif; color: #eee; }
  .row { display: flex; flex-wrap: wrap; gap: 8px; padding: 8px; }
  figure { margin: 0; flex: 1 1 320px; }
  img { width: 100%; display: block; border: 1px solid #333; }
  figcaption { padding: 6px 2px; font-size: 15px; font-weight: 600; }
</style></head>
<body><div class="row">
${items.map((i) => `  <figure><figcaption>${i.label}</figcaption><img src="${i.src}"></figure>`).join("\n")}
</div></body></html>`;

const tmp = path.join(path.dirname(path.resolve(outPath)), ".sheet.html");
fs.writeFileSync(tmp, html);

const browser = await chromium.launch({
  args: ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
const page = await browser.newPage({ viewport: { width: 1400, height: 800 } });
await page.goto(pathToFileURL(path.resolve(tmp)).href, { waitUntil: "load" });
await page.waitForTimeout(400);
await page.screenshot({ path: path.resolve(outPath), fullPage: true });
await browser.close();
fs.unlinkSync(tmp);
console.log(JSON.stringify({ sheet: path.resolve(outPath), items: items.length }));
