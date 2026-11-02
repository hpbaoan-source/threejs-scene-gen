# Apollo test - one-shot vs repair loop

Date: 2026-11-02
Prompt: *"an Apollo spacecraft standing on its launch pad at dawn, the tall umbilical
service tower beside it, xenon floodlights on the pad, steam venting from the flame
trench, a cinematic low-angle wide shot, the sun just rising over a clear sky"*

Model: `MiniMax-M3.1-Flash`, effort `medium`, max_tokens 32768

The repair run was started from the one-shot artefact with `--start-from`, so the only
difference between A and B is the repair loop.

| | A: one-shot | B: repair loop |
|---|---|---|
| Attempts | 1 | 4 |
| Wall clock | 139.8s | 391.8s |
| Cost | $0.00822 | $0.03135 |
| Console errors | **346** | **0** |
| Review score | **1 / 10** | **8 / 10** |
| Verdict | `needs_work` | `pass` |
| Frame mean luminance | 0.7127 (washed out) | 0.4101 |
| Frame std deviation | **0.0136** (flat) | 0.1654 |

## Attempt by attempt

| Attempt | Seconds | Score | Verdict | Console errors | meanLuma | stdLuma | Open issues |
|---|---|---|---|---|---|---|---|
| 0 (= A) | 18.5 | 1 | needs_work | 346 | 0.7127 | 0.0136 | 3 |
| 1 | 77.3 | 6 | needs_work | 0 | 0.4136 | 0.1982 | 6 |
| 2 | 141.3 | 7 | needs_work | 0 | 0.3849 | 0.1890 | 5 |
| 3 | 154.6 | **8** | **pass** | 0 | 0.4101 | 0.1654 | 5 |

Attempt 0 costs 18.5s because no model call is needed - it reuses the one-shot file.

## What the one-shot got wrong

The scene never drew. The browser showed a flat blue-grey screen with the loading
caption `INITIALIZING LAUNCH COMPLEX...`, and the console printed the same error
hundreds of times, once per animation frame:

```
TypeError: Cannot set properties of undefined (setting 'intensity')
```

Root cause, in the generated file:

```js
const floodlights = [
  { x: 11, z: 11, tx: -4, tz: 0, ty: 22 },
  ...
];

floodlights.forEach((f, i) => {
  f.light.intensity = (i < 2 ? 330 : 220) * (...);   // f.light does not exist
});
```

The fixture array only ever holds `{x, z, tx, tz, ty}`. The animation loop assumes each
entry also carries the `SpotLight` it created, but the creation loop never stored it.
The exception is thrown **before** `renderer.render(...)`, so the canvas stays blank
forever.

This is the case that motivates the whole project: the code looked complete, the file
was 33KB, there was no error until you ran it, and the error was invisible to a text
diff. Only rendering it and looking at the picture found it.

## What the repair loop did

Attempt 0 was rejected by two independent checks:

- the deterministic console-error gate (346 errors)
- the deterministic frame gate (`stdLuma` 0.0136, below the 0.02 flat-frame threshold)

Attempt 1 fixed the reference and the scene came alive - a Saturn V stage stack, a red
lattice umbilical tower with yellow swing arms, a dawn gradient sky, xenon floodlights
with visible beams, steam venting from the trench, a city skyline and the HUD panels.
Score 6, six issues still open.

Attempt 2 kept improving the lighting and the steam plume (7/10).
Attempt 3 pulled the camera back to the wide cinematic framing the prompt asked for,
softened the spotlight beams, added the emissive sun at the horizon, and reached
8/10 with `verdict: pass`, which is what ended the loop.

## Files

```
results/apollo-A-oneshot/     the one-shot artefact and its history
results/apollo-B-repair/       every attempt: html, png, comparison sheet, review
results/apollo-comparison.png  A | B1 | B2 | B3 side by side
```

Each attempt directory holds the HTML, its render, the comparison sheet the reviewer
actually saw, and `history.json` with every score, issue, fix, token count and the
running cost.
