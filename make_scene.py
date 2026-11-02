#!/usr/bin/env python3
"""make_scene.py - tao scene 3D Three.js tu mo ta bang AI.

Hai che do:
  oneshot   1 lan goi model, ra 1 file HTML, khong kiem chung
  repair    sinh -> render -> model phan bich anh -> sua -> lap lai

Vi du:
    python3 make_scene.py "a Japanese village at dusk with glowing lanterns"
    python3 make_scene.py --mode oneshot "a neon alley" --out scenes/neon.html
    python3 make_scene.py --repair 3 --threshold 7 "an Apollo spacecraft on the launch pad"
    python3 make_scene.py --image ref.png "recreate this scene in low-poly voxels"
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scene_gen import pipeline, report, render  # noqa: E402
from scene_gen.pipeline import DEFAULT_SYSTEM  # noqa: E402


def main():
    ap = argparse.ArgumentParser(
        description="Tao scene 3D Three.js bang MiniMax-M3.1-Flash",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("prompt", help="mo ta scene (tieng Anh khuyen nghi)")
    ap.add_argument("--mode", choices=["oneshot", "repair"], default="repair")
    ap.add_argument("--repair", type=int, default=3, help="so vong repair toi da")
    ap.add_argument("--threshold", type=int, default=7, help="diem toi thieu de accept")
    ap.add_argument("--out", help="file HTML cuoi cung (mac dinh: <workdir>/scene.html)")
    ap.add_argument("--workdir", help="thu muc luu ket qua (mac dinh: runs/<slug>-<timestamp>)")
    ap.add_argument("--image", help="anh tham chieu cho lan sinh dau (base64 gui len API)")
    ap.add_argument(
        "--start-from",
        help="dung mot file HTML co san lam diem bat dau thay vi sinh moi (so sanh A/B chinh xac)",
    )
    ap.add_argument("--system", default=DEFAULT_SYSTEM, help="luat choi gui cho model")
    ap.add_argument("--model", default="MiniMax-M3.1-Flash")
    ap.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--max-tokens", type=int, default=32768)
    ap.add_argument("--settle", type=int, default=6000, help="ms cho phep scene render")
    ap.add_argument("--no-render", action="store_true", help="che do oneshot, khong render")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    log = (lambda *a, **k: None) if args.quiet else print

    if args.mode == "repair":
        problems = render.check_node()
        if problems:
            print("Khong san sang render:", file=sys.stderr)
            for problem in problems:
                print("  -", problem, file=sys.stderr)
            return 3

    result = pipeline.run(
        args.prompt,
        mode="oneshot" if (args.mode == "oneshot" or args.no_render) else "repair",
        repair_rounds=args.repair,
        threshold=args.threshold,
        workdir=args.workdir,
        system=args.system,
        model=args.model,
        effort=args.effort,
        max_tokens=args.max_tokens,
        settle_ms=args.settle,
        image_path=args.image,
        start_html=args.start_from,
        log=log,
    )

    if args.out and result.best and result.best.html:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(result.best.html)

    report.summary(result, log=print if not args.quiet else (lambda *a, **k: None))
    print(json.dumps({
        "final_html": result.best.html_path if result.best else None,
        "final_png": result.best.png_path if result.best else None,
        "stop_reason": result.stop_reason,
        "seconds": round(result.total_seconds, 1),
        "cost_usd": round(result.total_cost, 6),
        "attempts": len(result.attempts),
    }, ensure_ascii=False))

    if result.best and result.best.accepted:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
