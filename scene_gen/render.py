"""Render orchestration.

Python owns the mechanics (launch, capture, measure); the model only ever
looks at the resulting image. Nothing here needs a model token.
"""
import json
import os
import subprocess
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
RENDER_SCRIPT = os.path.join(SCRIPTS_DIR, "render_scene.mjs")
SHEET_SCRIPT = os.path.join(SCRIPTS_DIR, "make_sheet.mjs")

# Deterministic gates on the rendered frame. These are deliberately blunt:
# they only catch frames that are obviously unusable, so the model is never
# asked to review a black frame as if it were a lighting choice.
DARK_MEAN = 0.06  # mean luminance below this reads as "almost black"
BRIGHT_MEAN = 0.97  # mean luminance above this reads as "blown out"
FLAT_STD = 0.02  # standard deviation below this reads as "a flat blank frame"


class RenderError(RuntimeError):
    pass


def _run_node(script, args, timeout=240):
    if not os.path.exists(script):
        raise RenderError(f"khong tim thay script: {script}")
    try:
        proc = subprocess.run(
            ["node", script] + args, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError as exc:
        raise RenderError("khong tim thay `node` tren PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise RenderError(f"render timeout sau {timeout}s") from exc

    payload = {}
    stdout = (proc.stdout or "").strip()
    if stdout:
        start = stdout.find("{")
        if start >= 0:
            try:
                payload = json.loads(stdout[start:])
            except ValueError:
                payload = {}
    if not payload:
        payload = {
            "consoleErrors": ["RENDER_SCRIPT_NO_OUTPUT: " + (proc.stderr or "")[-200:]],
            "image": None,
            "canvas": {"canvas": False},
        }
    payload["exitCode"] = proc.returncode
    return payload


def frame_gates(report):
    """Script-level verdict on the rendered frame. Independent of any model."""
    problems = []
    image = report.get("image")
    if not image:
        problems.append("khong doc duoc anh chup - khong render duoc")
        return problems
    mean = image.get("meanLuma")
    std = image.get("stdLuma")
    if mean is not None:
        if mean < DARK_MEAN:
            problems.append(
                f"anh qua toi (meanLuma={mean:.3f} < {DARK_MEAN}) - canh co the bi den hoac khong co den"
            )
        if mean > BRIGHT_MEAN:
            problems.append(f"anh qua sang (meanLuma={mean:.3f})")
    if std is not None and std < FLAT_STD:
        problems.append(f"anh phang/truong (stdLuma={std:.3f}) - khong co chieu sau")
    return problems


def render(html_path, png_path, settle_ms=6000):
    """Render one HTML scene. Returns the report dict from the node script."""
    os.makedirs(os.path.dirname(os.path.abspath(png_path)) or ".", exist_ok=True)
    report = _run_node(
        RENDER_SCRIPT,
        [os.path.abspath(html_path), os.path.abspath(png_path), "--settle", str(settle_ms)],
    )
    report["gates"] = frame_gates(report)
    report["consoleErrorCount"] = len(report.get("consoleErrors") or [])
    return report


def make_sheet(out_png, labelled_images):
    """Pack (label, path) pairs into one comparison sheet PNG."""
    args = []
    for label, path in labelled_images:
        args.append(f"{label}={os.path.abspath(path)}")
    result = _run_node(SHEET_SCRIPT, [os.path.abspath(out_png)] + args, timeout=120)
    if not os.path.exists(out_png):
        detail = (result.get("consoleErrors") or ["khong ro"])[0]
        raise RenderError("khong tao duoc comparison sheet: " + str(detail)[:200])
    return result


def check_node():
    """Verify the node + playwright prerequisites are present."""
    problems = []
    try:
        proc = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=20)
        if proc.returncode != 0:
            problems.append("`node` khong chay duoc")
    except Exception:
        problems.append("khong tim thay `node` tren PATH")
    if not os.path.exists(RENDER_SCRIPT):
        problems.append(f"thieu {RENDER_SCRIPT}")
    try:
        proc = subprocess.run(
            ["node", "-e", "require.resolve('playwright')"], capture_output=True, text=True, timeout=30
        )
        if proc.returncode != 0:
            problems.append("thieu `playwright` - chay `npm install` trong thu muc du an")
    except Exception:
        problems.append("khong kiem tra duoc playwright")
    return problems
