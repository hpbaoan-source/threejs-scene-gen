"""Vision review.

The model is asked for exactly one job: look at one image and decide pass or
fail. Everything mechanical (rendering, measuring, patching) stays in Python.

The review prompt is deliberately strict about JSON shape so the result can be
parsed without a repair round-trip.
"""
import json

REVIEW_SYSTEM = (
    "You are a strict visual quality reviewer for procedurally generated Three.js scenes. "
    "You judge only what is visible in the screenshot. You never invent problems to look "
    "thorough, and you never reward a scene for features you cannot see."
)

REVIEW_TEMPLATE = """\
ORIGINAL REQUEST:
{prompt}

{render_note}

Look at the attached screenshot and judge it against the request.

Score every criterion from 0 to 10:
- composition: is the subject clearly visible and well framed, nothing important clipped?
- lighting: is there readable light and shadow? not too dark, not blown out, not flat?
- materials: do materials read correctly (no black blobs, no missing colours, no invisible surfaces)?
- detail: is there enough shape and scene dressing for the subject?
- fidelity: does the image actually show what was asked for?
- integrity: 10 = clean render, 0 = visibly broken geometry, floating parts, or UI glitches.

Return STRICT JSON, nothing else, no markdown fence:
{{
  "verdict": "pass" | "needs_work" | "needs_input",
  "score": <integer 0-10>,
  "scores": {{"composition": <int>, "lighting": <int>, "materials": <int>,
              "detail": <int>, "fidelity": <int>, "integrity": <int>}},
  "issues": ["<what is visibly wrong, in the image>"],
  "fixes": ["<one concrete edit to the HTML/CSS/JS>"]
}}

Rules:
- verdict "pass" only if score >= {threshold} and nothing is visibly broken.
- verdict "needs_input" only if the request itself cannot be rendered as described.
- issues: at most 6, each one line, only about what is visible.
- fixes: at most 6, each one line, must be a concrete code edit such as
  "raise hemisphereLight intensity from 0.4 to 1.4" or "give the blossom material
  a non-black base colour". Do NOT propose new features or new subjects.
- if nothing is wrong, return an empty issues and fixes list and verdict "pass".
"""

REPAIR_TEMPLATE = """\
You are fixing a procedurally generated Three.js scene that failed a visual review.

ORIGINAL REQUEST:
{prompt}

REVIEW RESULT:
{review}

{render_note}

Here is the current HTML file:
{html}

Apply the fixes. Rules:
- Keep the scene recognisably the same subject and composition.
- Change only what the fixes require; do not add new subjects or features.
- Fix the root cause, not the symptom (for example, if geometry renders black,
  fix the material and the lighting, not just the colour of one object).
- Return the COMPLETE corrected HTML file and nothing else, starting with <!DOCTYPE html>
  and ending with </html>. No commentary, no markdown fence.
"""


def build_review_prompt(prompt, threshold=7, render_note=None):
    return REVIEW_TEMPLATE.format(
        prompt=prompt.strip(),
        threshold=threshold,
        render_note=render_note or "",
    )


def build_repair_prompt(prompt, review, html, render_note=None):
    review_text = json.dumps(review, ensure_ascii=False, indent=2)
    return REPAIR_TEMPLATE.format(
        prompt=prompt.strip(),
        review=review_text,
        html=html,
        render_note=render_note or "",
    )


def parse_review(payload):
    """Normalise a parsed review payload into a stable shape."""
    if not isinstance(payload, dict):
        return {
            "verdict": "needs_work",
            "score": 0,
            "scores": {},
            "issues": ["review khong phai JSON hop le"],
            "fixes": [],
            "raw": payload,
        }
    verdict = str(payload.get("verdict", "needs_work")).lower()
    if verdict not in ("pass", "needs_work", "needs_input"):
        verdict = "needs_work"
    try:
        score = int(payload.get("score", 0))
    except (TypeError, ValueError):
        score = 0
    scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}

    def _list(key):
        value = payload.get(key)
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()][:6]
        if isinstance(value, str) and value.strip():
            return [value.strip()][:6]
        return []

    return {
        "verdict": verdict,
        "score": max(0, min(10, score)),
        "scores": scores,
        "issues": _list("issues"),
        "fixes": _list("fixes"),
    }


def review_scene(client, prompt, image_bytes, threshold=7, render_note=None):
    """Send one screenshot to the model and return the parsed review."""
    text = build_review_prompt(prompt, threshold, render_note)
    response = client.complete_with_image(image_bytes, text, system=REVIEW_SYSTEM, effort="low")
    try:
        payload = response.json()
    except ValueError:
        payload = {"verdict": "needs_work", "score": 0, "issues": ["review khong phai JSON"], "fixes": []}
    result = parse_review(payload)
    result["usage"] = {
        "output_tokens": response.output_tokens,
        "input_tokens": response.input_tokens,
        "thinking_tokens": response.thinking_tokens,
    }
    result["raw_text"] = response.text[:4000]
    return result
