// Render a Three.js scene in headless Chromium.
//
//   node scripts/render_scene.mjs <file.html> <out.png> [--settle 6000]
//
// Prints one JSON object on stdout:
//   { consoleErrors, consoleWarnings, canvas, image: {meanLuma, darkRatio,
//     brightRatio, stdLuma, buckets}, png }
//
// The image statistics are computed by the browser itself: the PNG we just
// captured is decoded back into a 2D canvas and sampled. That keeps the
// project dependency-free (no image library on either side) while still
// giving the Python side a deterministic, script-level gate - "the frame is
// almost black" can be caught without spending a single model token.

import { chromium } from "playwright";
import path from "node:path";
import { pathToFileURL } from "node:url";

const args = process.argv.slice(2);
const positional = [];
let settleFlag = 6000;
for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if (arg === "--settle") {
    settleFlag = Number(args[i + 1]);
    i++;
    continue;
  }
  if (arg.startsWith("--")) continue;
  positional.push(arg);
}

const [htmlPath, pngPath] = positional;
if (!htmlPath || !pngPath) {
  console.error("usage: node render_scene.mjs <file.html> <out.png> [--settle ms]");
  process.exit(2);
}
const settle = settleFlag;

const browser = await chromium.launch({
  args: [
    "--no-sandbox",
    "--use-gl=angle",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
  ],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

const errors = [];
const warnings = [];
let errorCount = 0;
let warningCount = 0;
const MAX_ERRORS = 12;
page.on("console", (m) => {
  const t = m.type();
  if (t === "error") {
    errorCount++;
    if (errors.length < MAX_ERRORS) errors.push(m.text().slice(0, 300));
  } else if (t === "warning") {
    warningCount++;
    if (warnings.length < 4) warnings.push(m.text().slice(0, 200));
  }
});
page.on("pageerror", (e) => {
  errorCount++;
  if (errors.length < MAX_ERRORS) errors.push("PAGEERROR: " + String(e).slice(0, 300));
});

let canvas = { canvas: false };
try {
  await page.goto(pathToFileURL(path.resolve(htmlPath)).href, {
    waitUntil: "load",
    timeout: 60000,
  });
  await page.waitForTimeout(settle);
  canvas = await page.evaluate(() => {
    const c = document.querySelector("canvas");
    if (!c) return { canvas: false };
    return { canvas: true, w: c.width, h: c.height };
  });
} catch (err) {
  errors.push("NAVIGATION: " + String(err).slice(0, 300));
}

await page.screenshot({ path: pngPath });

// Decode the captured PNG inside the browser and compute frame statistics.
let image = null;
try {
  const buf = await page.screenshot();
  const dataUrl = "data:image/png;base64," + buf.toString("base64");
  image = await page.evaluate(async (url) => {
    const img = new Image();
    img.src = url;
    await img.decode();
    const c = document.createElement("canvas");
    c.width = img.width;
    c.height = img.height;
    const ctx = c.getContext("2d");
    ctx.drawImage(img, 0, 0);
    const data = ctx.getImageData(0, 0, c.width, c.height).data;
    let sum = 0;
    let sumSq = 0;
    let dark = 0;
    let bright = 0;
    const buckets = new Array(16).fill(0);
    const n = data.length / 4;
    for (let i = 0; i < data.length; i += 4) {
      const luma =
        (0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2]) / 255;
      sum += luma;
      sumSq += luma * luma;
      if (luma < 0.08) dark++;
      if (luma > 0.95) bright++;
      buckets[Math.min(15, Math.floor(luma * 16))]++;
    }
    const mean = sum / n;
    const variance = Math.max(0, sumSq / n - mean * mean);
    return {
      w: img.width,
      h: img.height,
      meanLuma: Number(mean.toFixed(4)),
      stdLuma: Number(Math.sqrt(variance).toFixed(4)),
      darkRatio: Number((dark / n).toFixed(4)),
      brightRatio: Number((bright / n).toFixed(4)),
      buckets: buckets.map((v) => Number((v / n).toFixed(4))),
    };
  }, dataUrl);
} catch (err) {
  errors.push("IMAGE_STATS: " + String(err).slice(0, 200));
}

console.log(
  JSON.stringify(
    {
      file: path.basename(htmlPath),
      png: path.resolve(pngPath),
      consoleErrors: errors,
      consoleErrorCount: errorCount,
      consoleWarnings: warnings,
      canvas,
      image,
    },
    null,
    2
  )
);

await browser.close();
process.exit(errorCount ? 1 : 0);
