#!/usr/bin/env python3
"""Compose side-by-side for the shuttle scene: reference | baseline | with-flame | best."""
import sys
from PIL import Image, ImageDraw

W = 520
items = [
    ("Anh goc\nanh NASA", "/home/anhuynh/.nanobot/media/telegram/AQADlhprG6g5SVd-.jpg"),
    ("Run 1 - 6/10\nreview chi thay anh render\nkhong lua, khong khoi",
     "/home/anhuynh/work/threejs-scene-gen/runs/shuttle-20261103-144414/scene.png"),
    ("Run 2 - 6/10\nco anh tham chieu trong review\nco lua + khoi, troi dem",
     "/home/anhuynh/work/threejs-scene-gen/runs/shuttle-ref-20261103-144920/attempt-1.png"),
    ("Final - 6/10\nfix gamma sRGB + khoi lon\ntroi ngan, 2 lua",
     "/home/anhuynh/work/threejs-scene-gen/runs/shuttle-smoke-20261103-151517/attempt-1.png"),
]
out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/shuttle-comparison.png"
PAD, HDR = 12, 64

tiles = []
for label, path in items:
    im = Image.open(path).convert("RGB")
    h = int(im.height * W / im.width)
    tiles.append((label, im.resize((W, h), Image.LANCZOS)))

row_h = max(t.height for _, t in tiles)
canvas = Image.new("RGB", (PAD + len(tiles) * (W + PAD), HDR + row_h + PAD), (13, 17, 23))
draw = ImageDraw.Draw(canvas)
for i, (label, t) in enumerate(tiles):
    x = PAD + i * (W + PAD)
    canvas.paste(t, (x, HDR))
    for j, line in enumerate(label.split("\n")):
        draw.text((x + 4, 8 + j * 16), line, fill=(230, 237, 243))
canvas.save(out)
print(out, canvas.size)
