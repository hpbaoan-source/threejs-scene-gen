#!/usr/bin/env python3
"""Build docs/ - the GitHub Pages gallery of generated scenes.

Static only: one index.html, the scene files, and their renders.
"""
import html
import os
import shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs")

SCENES = [
    {
        "file": "apollo-final.html",
        "src": "results/apollo-B-repair/scene.html",
        "shot": "results/apollo-B-repair/scene.png",
        "shot_name": "apollo-repair.png",
        "title": "Apollo — repair loop (8/10)",
        "tag": "vòng repair",
        "meta": "391.8s · $0.0313 · 0 lỗi console · 4 vòng",
        "note": "Cùng prompt với bản one-shot, đã qua vòng tự sửa 3 lần. Chấm nhận.",
    },
    {
        "file": "apollo-oneshot.html",
        "src": "results/apollo-A-oneshot/scene.html",
        "shot": "results/apollo-A-oneshot/scene.png",
        "shot_name": "apollo-oneshot.png",
        "title": "Apollo — one-shot (1/10)",
        "tag": "one-shot",
        "meta": "139.8s · $0.0082 · 346 lỗi console · 1 vòng",
        "note": "Bản one-shot hỏng: scene không bao giờ được vẽ. Đây là lý do cần vòng repair.",
        "warn": True,
    },
    {
        "file": "village.html",
        "src": "examples/village.html",
        "shot": "examples/shot-village.png",
        "title": "Làng Nhật lúc hoàng hôn",
        "tag": "one-shot",
        "meta": "33 KB · 0 lỗi console",
        "note": "Đèn lồng, sương mù, đường đá, HUD.",
    },
    {
        "file": "sakura.html",
        "src": "examples/sakura.html",
        "shot": "examples/shot-sakura.png",
        "title": "Vườn anh đào",
        "tag": "one-shot + fix",
        "meta": "33 KB · 0 lỗi console",
        "note": "Bản gốc có cụm hoa đen (vertexColors không có attribute color). Đã fix 1 dòng.",
    },
    {
        "file": "workshop.html",
        "src": "examples/workshop.html",
        "shot": "examples/shot-workshop.png",
        "title": "Xưởng cơ khí",
        "tag": "one-shot",
        "meta": "33 KB · 0 lỗi console",
        "note": "Tiện lathe, bánh răng, bảng dụng cụ, đèn vàng ấm.",
    },
    {
        "file": "vision-from-image.html",
        "src": "examples/vision-from-image.html",
        "shot": "examples/shot-vision.png",
        "title": "Dựng từ ảnh voxel",
        "tag": "vision",
        "meta": "25 KB · 0 lỗi console",
        "note": "Đưa ảnh tham chiếu vào, model dựng lại bằng voxel.",
    },
    {
        "file": "neon-alley.html",
        "src": "examples/neon-alley.html",
        "shot": "examples/shot-neon-alley.png",
        "title": "Hẻm neon mưa",
        "tag": "one-shot",
        "meta": "29 KB · 0 lỗi console",
        "note": "Chạy thử khi dựng tool: scene bị tối quá. Cổng chất lượng tự động đã bắt được trường hợp này.",
    },
    {
        "file": "villa.html",
        "src": "examples/villa.html",
        "shot": "examples/shot-villa.png",
        "title": "Biệt thự + hồ bơi",
        "tag": "vision",
        "meta": "9/10 · 0 lỗi console · 9.2 phút · $0.042",
        "note": "Dựng từ ảnh phối cảnh: mái ngói xanh, hồ bơi dài, vườn tiểu cảnh, 2 xe, góc nhìn aerial. Có nút Aerial/Front/Plan để xoay.",
    },
]

PAGE = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>threejs-scene-gen · gallery</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; background: #0d1117; color: #e6edf3;
    font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  }
  .wrap { max-width: 1180px; margin: 0 auto; padding: 40px 20px 80px; }
  header { border-bottom: 1px solid #21262d; padding-bottom: 22px; margin-bottom: 34px; }
  h1 { margin: 0 0 8px; font-size: 27px; letter-spacing: -0.02em; }
  .sub { color: #8b949e; max-width: 760px; }
  .sub a { color: #58a6ff; }
  .grid { display: grid; gap: 22px; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); }
  .card {
    background: #161b22; border: 1px solid #21262d; border-radius: 12px;
    overflow: hidden; display: flex; flex-direction: column;
  }
  .card:hover { border-color: #30363d; }
  .thumb { display: block; background: #010409; }
  .thumb img { width: 100%; display: block; aspect-ratio: 16/9; object-fit: cover; }
  .body { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 7px; flex: 1; }
  .title-row { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
  .title { font-weight: 650; font-size: 16px; }
  .tag {
    font-size: 11px; padding: 2px 8px; border-radius: 20px; white-space: nowrap;
    background: #1f6feb22; color: #58a6ff; border: 1px solid #1f6feb44;
  }
  .tag.warn { background: #f8514922; color: #ff7b72; border-color: #f8514944; }
  .meta { font-size: 12.5px; color: #8b949e; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  .note { font-size: 13.5px; color: #b1bac4; }
  .open {
    margin-top: auto; padding-top: 10px;
    font-size: 13px; font-weight: 600; color: #58a6ff; text-decoration: none;
  }
  .open:hover { text-decoration: underline; }
  footer { margin-top: 48px; padding-top: 20px; border-top: 1px solid #21262d; color: #8b949e; font-size: 13.5px; }
  footer a { color: #58a6ff; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; background: #21262d; padding: 1px 6px; border-radius: 4px; font-size: 13px; }
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>threejs-scene-gen</h1>
  <p class="sub">
    Mỗi scene dưới đây là <b>một file HTML tự chứa</b> — AI viết ra JavaScript dựng hình,
    trình duyệt của bạn tự vẽ lại 3D lúc 60 khung hình/giây. Không có file mesh, không phải tải texture.
    Mở bằng trình duyệt là chạy (cần mạng để lấy three.js từ CDN).
  </p>
</header>
<div class="grid">
{cards}
</div>
<footer>
  Mã nguồn: <a href="https://github.com/hpbaoan-source/threejs-scene-gen">github.com/hpbaoan-source/threejs-scene-gen</a>
  · Sinh bằng <code>MiniMax-M3.1-Flash</code>
  · Chế độ <code>oneshot</code> và <code>repair</code> (model tự nhìn ảnh render rồi sửa code).
</footer>
</div>
</body>
</html>
"""


def main():
    if os.path.isdir(DOCS):
        shutil.rmtree(DOCS)
    os.makedirs(os.path.join(DOCS, "scenes"))
    os.makedirs(os.path.join(DOCS, "shots"))

    cards = []
    for scene in SCENES:
        src = os.path.join(REPO, scene["src"])
        shot = os.path.join(REPO, scene["shot"])
        if not os.path.exists(src) or not os.path.exists(shot):
            print(f"  skip (missing): {scene['file']}")
            continue
        shutil.copy2(src, os.path.join(DOCS, "scenes", scene["file"]))
        shot_name = scene.get("shot_name") or os.path.basename(scene["shot"])
        shutil.copy2(shot, os.path.join(DOCS, "shots", shot_name))
        cards.append(
            f"""  <div class="card">
    <a class="thumb" href="scenes/{html.escape(scene['file'])}" target="_blank" rel="noopener">
      <img src="shots/{html.escape(shot_name)}" alt="{html.escape(scene['title'])}" loading="lazy">
    </a>
    <div class="body">
      <div class="title-row">
        <span class="title">{html.escape(scene['title'])}</span>
        <span class="tag{' warn' if scene.get('warn') else ''}">{html.escape(scene['tag'])}</span>
      </div>
      <div class="meta">{html.escape(scene['meta'])}</div>
      <div class="note">{html.escape(scene['note'])}</div>
      <a class="open" href="scenes/{html.escape(scene['file'])}" target="_blank" rel="noopener">Mở scene ↗</a>
    </div>
  </div>"""
        )

    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(PAGE.replace("{cards}", "\n".join(cards)))

    total = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, fs in os.walk(DOCS)
        for f in fs
    )
    print(f"docs/ built: {len(cards)} cards, {total / 1024:.0f} KB")
    for dp, _, fs in sorted(os.walk(DOCS)):
        for f in sorted(fs):
            p = os.path.join(dp, f)
            print(f"  {os.path.relpath(p, DOCS):42s} {os.path.getsize(p) / 1024:8.1f} KB")


if __name__ == "__main__":
    main()
