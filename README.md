# threejs-scene-gen

Generate a Three.js scene from a sentence, then let a model look at the render
and fix what it sees.

```bash
python3 make_scene.py "an Apollo spacecraft on its launch pad at dawn"
```

That is the whole idea. There is no mesh file, no model download, no
`.glb`, no texture pack. The output is one self-contained HTML file containing
JavaScript that builds the scene procedurally. Your browser runs it at 60fps,
exactly like a game.

---

## Two modes

### `oneshot` — one call, one file

```bash
python3 make_scene.py --mode oneshot "a Japanese village at dusk with glowing lanterns" \
                       --out scenes/village.html
```

One model call, roughly 30-160 seconds, about **$0.005**. No verification: the
file is what the model produced, as-is.

### `repair` — generate, render, judge, fix, repeat

```bash
python3 make_scene.py --mode repair --repair 3 --threshold 7 \
    "an Apollo spacecraft on its launch pad at dawn"
```

The loop:

```
generate ──► render (headless Chromium) ──► screenshot
                                              │
                            model looks at the screenshot
                                              │
                         verdict + issues + concrete fixes
                                              │
                              patch the HTML, render again
```

A scene is accepted only when the reviewer says `pass`, the score reaches the
threshold, and no deterministic gate complains. Everything is recorded in
`history.json`.

---

## Why the loop exists

"Zero console errors" does not mean "looks right". A scene can run perfectly
and still render a black blob where a cherry tree should be — that happened
here, and it was caught by looking at a screenshot, not by a log line.

The review step closes that gap. Three rules keep it honest:

1. **Scripts enforce, the model judges.** Python owns rendering, measuring and
   patching. The model only ever looks at one image and returns a verdict. It
   never touches the file itself.
2. **Fail fast, before the browser.** Static gates reject a truncated file, a
   missing canvas or an unbalanced `<script>` without spending a render.
3. **Deterministic frame gates.** A render that is almost black, blown out or
   completely flat is rejected by the script, no matter what the model said.

---

## Requirements

- Python 3.10+ (standard library only — no pip install, no virtualenv)
- Node.js 18+ and Playwright Chromium (only for rendering)
- A MiniMax API key in `~/.nanobot/config.json` under `providers.minimaxAnthropic`

```bash
npm install          # playwright
npx playwright install chromium
```

The API key is read from the config file at runtime. It is never passed on the
command line and never written to a log.

---

## Usage

```bash
# one-shot
python3 make_scene.py --mode oneshot "a neon alley in the rain" --out scenes/neon.html

# repair loop
python3 make_scene.py --mode repair --repair 3 --threshold 7 "a neon alley in the rain"

# refine an existing scene instead of starting over (exact A/B comparison)
python3 make_scene.py --mode repair --repair 3 \
    --start-from results/apollo-A-oneshot/scene.html "an Apollo spacecraft..."

# build from a reference image
python3 make_scene.py --image examples/reference-voxel-tree.png \
    "recreate this scene in low-poly voxels"
```

| Flag | Default | Meaning |
|---|---|---|
| `--mode` | `repair` | `oneshot` or `repair` |
| `--repair N` | `3` | maximum repair rounds |
| `--threshold N` | `7` | minimum review score to accept |
| `--out PATH` | — | write the final HTML here |
| `--workdir PATH` | `runs/<slug>-<ts>` | where attempts, screenshots and history land |
| `--start-from PATH` | — | refine an existing HTML instead of generating one |
| `--image PATH` | — | reference image for the first generation |
| `--model` | `MiniMax-M3.1-Flash` | any MiniMax model id |
| `--effort` | `medium` | `low｜medium｜high｜xhigh｜max` — reasoning depth |
| `--max-tokens` | `32768` | counts thinking tokens too |
| `--settle MS` | `6000` | how long the scene gets to render |
| `--system TEXT` | built-in | the rules handed to the model |

---

## Output layout

```
runs/<slug>-<timestamp>/
  attempt-0.html      generation
  attempt-0.png       render
  sheet-0.png         comparison sheet the reviewer saw
  attempt-1.html      patched by the model
  ...
  scene.html          the accepted (or best) scene
  scene.png           its render
  history.json        every attempt: scores, issues, fixes, tokens, cost
```

`history.json` is the audit trail. It records what each attempt scored, what
was wrong, what was changed, and how many tokens it cost.

---

## Cost

MiniMax-M3.1-Flash: $0.15 / M input tokens, $0.60 / M output tokens.

| | one-shot | repair loop (3 rounds) |
|---|---|---|
| Tokens | ~13k output | ~45k output (patch + review per round) |
| Cost | ~$0.005 | ~$0.02 |
| Time | 30-160s | 5-15 min |

For comparison, an image-to-3D agent pipeline with the same idea — staged
passes, render-review gates — runs about 80k-180k tokens per object, which is
one to six dollars.

---

## Publishing the gallery

`docs/` is a static gallery (`index.html` + `scenes/*.html` + `shots/*.png`).
Rebuild it from `examples/` and `results/` with `python3 scripts/build_gallery.py`.

**ngrok is the default publishing path.** It needs no account setup, no DNS and
no changes to any production service:

```bash
bash scripts/serve_gallery.sh     # static server on :8899 + ngrok tunnel
cat /home/anhuynh/workspace/gallery-url.txt
```

The free ngrok tier hands out a random subdomain, so the URL changes whenever the
tunnel restarts. `scripts/gallery_watchdog.sh` (registered in the OS crontab,
every 15 minutes) restarts the server and the tunnel if the URL stops
answering, and writes the fresh URL to `gallery-url.txt`.

GitHub Pages is the durable alternative. The workflow in
`.github/workflows/pages.yml` is already committed, but it cannot run yet: the
fine-grained PAT has no **Administration: write** permission, so
`POST /repos/{owner}/{repo}/pages` returns 403 and `actions/configure-pages`
with `enablement: true` fails with "Resource not accessible by integration".
Grant that permission and the workflow publishes on its own.

**Do not publish to `moon.id.vn/leaf/`** — that service was removed on
2026-11-02. It could not have worked anyway: Moon's own API holds port 3030,
so `/leaf/` proxied back to the API itself.

---

## Layout

```
make_scene.py         CLI
scene_gen/
  api.py              MiniMax client (text + vision), cost accounting
  extract.py          HTML extraction, static gates, JSON parsing
  render.py           render orchestration, deterministic frame gates
  review.py           the review prompt and its parser
  pipeline.py         one-shot + repair loop
  report.py           human-readable run summary
scripts/
  render_scene.mjs    headless Chromium: render, console errors, frame stats
  make_sheet.mjs      packs renders into one comparison sheet
  build_gallery.py    rebuilds docs/ (static gallery) from examples/ + results/
  serve_gallery.sh    static server + ngrok tunnel
  gallery_watchdog.sh restarts the tunnel if the public URL dies
  check_gallery.mjs   Playwright check: every image loads, every scene renders
  enable_pages.py     checks/enables GitHub Pages via the GitHub API
tests/                unit tests for the deterministic parts
examples/             example scenes and their renders
results/              recorded runs
docs/                 the published gallery (GitHub Pages source)
```

The Python side has no third-party dependencies. Frame statistics are computed
by the browser itself — the captured PNG is decoded back into a 2D canvas and
sampled — which keeps both sides of the project dependency-free.

```bash
python3 -m unittest discover -s tests -v
```

---

## Credits

The staged, gated idea in the repair loop is inspired by
[img2threejs](https://github.com/img2threejs/img2threejs) (Apache-2.0), which
applies the same "scripts enforce, the model judges" principle to rebuilding
objects from reference photographs. This project takes the loop in a different
direction: text in, whole scene out, and a frontier model doing the judging.
