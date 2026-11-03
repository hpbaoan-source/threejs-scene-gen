"""Pipeline: one-shot generation, and the render-review-repair loop.

Two modes:

  oneshot  - one model call, one file. Cheap, fast, no verification.
  repair   - generate, render, let the model judge the render, patch, repeat
             until the render passes (or the budget of rounds runs out).

The repair loop borrows the strongest idea from img2threejs: scripts enforce,
the model judges. Here that means Python owns rendering, measuring and
patching, and the model only ever looks at one image and returns a verdict.
"""
import json
import os
import re
import time

from .api import Client
from .extract import extract_html, looks_like_scene, static_gates
from .render import frame_gates, make_sheet, render
from .review import build_repair_prompt, review_scene

DEFAULT_SYSTEM = (
    "Use only the Three.js core ES module from "
    "https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.module.min.js. "
    "Do not import addons or legacy examples/js paths; "
    "implement any camera controls directly inside the HTML. "
    "Deliver one complete self-contained HTML file: scene, lighting, camera and a "
    "small on-screen HUD. Prefer readable lighting with real shadows over a dark scene. "
    "If you write a custom sky or gradient ShaderMaterial, you MUST end the fragment "
    "shader with '#include <colorspace_fragment>' right after setting gl_FragColor: "
    "Three.js converts colours from linear to sRGB in that chunk, so a hand-written "
    "shader without it renders every colour about one gamma too dark, which turns a "
    "daytime sky into night."
)


def slugify(text, length=48):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:length].rstrip("-") or "scene")


def _write(path, content):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


class Attempt:
    """One generation + render + review cycle."""

    def __init__(self, index):
        self.index = index
        self.html = None
        self.html_path = None
        self.png_path = None
        self.static_problems = []
        self.render_report = {}
        self.review = {}
        self.seconds = 0.0
        self.tokens = {}
        self.accepted = False
        self.reason = ""

    def to_dict(self):
        return {
            "index": self.index,
            "html_path": self.html_path,
            "png_path": self.png_path,
            "seconds": round(self.seconds, 1),
            "static_problems": self.static_problems,
            "console_errors": self.render_report.get("consoleErrorCount", 0),
            "console_errors_detail": self.render_report.get("consoleErrors", []),
            "frame_gates": self.render_report.get("gates", []),
            "image": self.render_report.get("image"),
            "review": self.review,
            "accepted": self.accepted,
            "reason": self.reason,
            "tokens": self.tokens,
        }


class Result:
    def __init__(self, prompt, workdir):
        self.prompt = prompt
        self.workdir = workdir
        self.attempts = []
        self.best = None
        self.total_seconds = 0.0
        self.total_cost = 0.0
        self.stop_reason = ""

    def to_dict(self):
        return {
            "prompt": self.prompt,
            "workdir": self.workdir,
            "stop_reason": self.stop_reason,
            "total_seconds": round(self.total_seconds, 1),
            "total_cost_usd": round(self.total_cost, 6),
            "attempts": [a.to_dict() for a in self.attempts],
            "best_attempt": self.best.index if self.best else None,
            "final_html": self.best.html_path if self.best else None,
            "final_png": self.best.png_path if self.best else None,
        }


def _generate(client, prompt, system, effort, image_bytes=None, image_list=None):
    if image_list:
        response = client.complete_with_images(image_list, prompt, system=system, effort=effort)
    elif image_bytes:
        response = client.complete_with_image(image_bytes, prompt, system=system, effort=effort)
    else:
        response = client.complete(prompt, system=system, effort=effort)
    html = extract_html(response.text)
    return html, response


def _decide(attempt, threshold, mode="repair"):
    """Script-level verdict. A frame that fails a deterministic gate never passes."""
    if attempt.static_problems:
        attempt.accepted = False
        attempt.reason = "static gates: " + "; ".join(attempt.static_problems)
        return False
    if mode == "oneshot":
        # no render, no review - structural checks are all we have
        attempt.accepted = True
        attempt.reason = "one-shot: qua static gates"
        return True
    if attempt.render_report.get("consoleErrorCount", 0) > 0:
        attempt.accepted = False
        attempt.reason = "co loi trong console"
        return False
    gates = attempt.render_report.get("gates") or []
    if gates:
        attempt.accepted = False
        attempt.reason = "frame gates: " + "; ".join(gates)
        return False
    review = attempt.review or {}
    if review.get("verdict") == "needs_input":
        attempt.accepted = False
        attempt.reason = "review: yeu cau khong the render duoc - can xac nhan lai"
        return False
    if review.get("verdict") != "pass":
        attempt.accepted = False
        attempt.reason = "review: verdict=%s score=%s" % (
            review.get("verdict"),
            review.get("score"),
        )
        return False
    if review.get("score", 0) < threshold:
        attempt.accepted = False
        attempt.reason = "review: score %s < %s" % (review.get("score"), threshold)
        return False
    attempt.accepted = True
    attempt.reason = "pass"
    return True


def run(
    prompt,
    mode="repair",
    repair_rounds=3,
    threshold=7,
    workdir=None,
    system=DEFAULT_SYSTEM,
    model="MiniMax-M3.1-Flash",
    effort="medium",
    max_tokens=32768,
    settle_ms=6000,
    image_path=None,
    start_html=None,
    ref_in_review=None,
    log=print,
):
    """Run the pipeline. Returns a Result."""
    client = Client(model=model, effort=effort, max_tokens=max_tokens)
    started = time.time()
    image_bytes = _read_bytes(image_path) if image_path else None

    # When a reference photo is given, the review and the repair step should see
    # it too - otherwise "fidelity" is judged against the text prompt only and
    # elements that are simply missing from the render go unnoticed.
    if ref_in_review is None:
        ref_in_review = bool(image_bytes)
    reference_bytes = image_bytes if ref_in_review else None
    if reference_bytes:
        log("reference photo is included in every review and repair call")

    if not workdir:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        workdir = os.path.join("runs", f"{slugify(prompt)}-{stamp}")
    os.makedirs(workdir, exist_ok=True)

    result = Result(prompt, workdir)

    previous_html = None
    previous_png = None
    best_score = -1

    # one-shot means exactly one generation; repair mode gets 1 + N rounds.
    max_cycles = 1 if mode == "oneshot" else max(1, repair_rounds + 1)

    # A pre-existing HTML can be used as the starting point, so a repair run
    # can refine an artefact that was already produced instead of starting
    # over. That makes an A/B comparison exact: B is A plus the repair loop.
    seed_html = None
    if start_html:
        with open(start_html, encoding="utf-8") as fh:
            seed_html = fh.read()

    for index in range(max_cycles):
        attempt = Attempt(index)
        cycle_start = time.time()

        if index == 0:
            if seed_html:
                log(f"[{index}] starting from existing HTML: {start_html}")
                html = seed_html
                attempt.tokens = {"output_tokens": 0, "input_tokens": 0, "thinking_tokens": 0}
            else:
                log(f"[{index}] generating (one-shot)...")
                html, response = _generate(client, prompt, system, effort, image_bytes)
                attempt.tokens = {
                    "output_tokens": response.output_tokens,
                    "input_tokens": response.input_tokens,
                    "thinking_tokens": response.thinking_tokens,
                }
        else:
            log(f"[{index}] patching from review of attempt {index - 1}...")
            previous = result.attempts[index - 1]
            review_payload = dict(previous.review or {})
            # Runtime errors are just as actionable as visual issues, and they
            # are often the real cause of a blank render. Hand them to the
            # model together with the review.
            console_errors = previous.render_report.get("consoleErrors") or []
            if console_errors:
                review_payload["runtimeErrors"] = console_errors
            frame_gates = previous.render_report.get("gates") or []
            if frame_gates:
                review_payload["frameGates"] = frame_gates
            if previous.static_problems:
                review_payload["staticProblems"] = previous.static_problems
            repair_prompt = build_repair_prompt(
                prompt,
                review_payload,
                previous_html,
                render_note=f"Previous render: {previous.png_path}",
                has_reference=bool(reference_bytes),
            )
            # The patcher sees the reference photo and the previous render next
            # to the HTML, so it can tell "this element is missing" apart from
            # "this element looks wrong".
            patch_images = None
            if reference_bytes:
                prev_render = _read_bytes(previous.png_path)
                if prev_render:
                    patch_images = [reference_bytes, prev_render]
            html, response = _generate(client, repair_prompt, system, effort, image_list=patch_images)
            attempt.tokens = {
                "output_tokens": response.output_tokens,
                "input_tokens": response.input_tokens,
                "thinking_tokens": response.thinking_tokens,
            }

        if not html or not looks_like_scene(html):
            attempt.static_problems = ["model khong tra ve mot file HTML scene hop le"]
            attempt.seconds = time.time() - cycle_start
            result.attempts.append(attempt)
            if index == 0:
                result.stop_reason = "generation that la - khong co HTML scene"
                break
            # keep the previous attempt, try one more round
            previous_html = previous_html
            log(f"[{index}] patch khong hop le, giu ban truoc")
            continue

        attempt.html = html
        attempt.html_path = os.path.join(workdir, f"attempt-{index}.html")
        attempt.png_path = os.path.join(workdir, f"attempt-{index}.png")
        _write(attempt.html_path, html)
        attempt.static_problems = static_gates(html)

        if mode == "repair":
            log(f"[{index}] rendering...")
            attempt.render_report = render(attempt.html_path, attempt.png_path, settle_ms)
            log(
                "[%d] render: %d loi console, meanLuma=%s"
                % (
                    index,
                    attempt.render_report.get("consoleErrorCount", 0),
                    (attempt.render_report.get("image") or {}).get("meanLuma"),
                )
            )

            sheet_items = []
            if previous_png:
                sheet_items.append((f"attempt-{index - 1}", previous_png))
            sheet_items.append((f"attempt-{index}", attempt.png_path))
            sheet_path = os.path.join(workdir, f"sheet-{index}.png")
            try:
                make_sheet(sheet_path, sheet_items)
            except Exception as exc:  # sheet is a convenience, never fatal
                log(f"[{index}] khong dong duoc sheet: {exc}")
                sheet_path = attempt.png_path

            log(f"[{index}] reviewing...")
            attempt.review = review_scene(
                client,
                prompt,
                _read_bytes(sheet_path),
                threshold=threshold,
                render_note=f"Render attempt {index} of {slugify(prompt)}.",
                reference_bytes=reference_bytes,
            )
            log(
                "[%d] review: %s score=%s issues=%d"
                % (
                    index,
                    attempt.review.get("verdict"),
                    attempt.review.get("score"),
                    len(attempt.review.get("issues") or []),
                )
            )

        _decide(attempt, threshold, mode)
        attempt.seconds = time.time() - cycle_start
        result.attempts.append(attempt)

        score = attempt.review.get("score", 0) if attempt.review else 0
        if attempt.accepted or score > best_score:
            if attempt.accepted or best_score < 0:
                best_score = score
                result.best = attempt
        if attempt.accepted:
            result.stop_reason = "accepted at attempt %d" % index
            break
        if attempt.review.get("verdict") == "needs_input":
            result.stop_reason = "review yeu cau xac nhan lai truoc khi tiep tuc"
            break
        if index == max_cycles - 1:
            result.stop_reason = (
                "one-shot xong" if mode == "oneshot" else "het so vong repair"
            )
        previous_html = html
        previous_png = attempt.png_path

    if result.best is None and result.attempts:
        # nothing passed: keep the attempt with the best review score
        scored = [a for a in result.attempts if a.review]
        result.best = max(scored, key=lambda a: a.review.get("score", 0)) if scored else result.attempts[-1]
        result.stop_reason = result.stop_reason or "khong vong nao dat chuan - giu ban tot nhat"

    final_html = os.path.join(workdir, "scene.html")
    final_png = os.path.join(workdir, "scene.png")
    if result.best and result.best.html:
        _write(final_html, result.best.html)
        if os.path.exists(result.best.png_path):
            with open(final_png, "wb") as dst:
                dst.write(_read_bytes(result.best.png_path))
            result.best.png_path = final_png
        result.best.html_path = final_html

    result.total_seconds = time.time() - started
    result.total_cost = client.cost
    with open(os.path.join(workdir, "history.json"), "w", encoding="utf-8") as fh:
        json.dump(result.to_dict(), fh, indent=2, ensure_ascii=False)
    return result
