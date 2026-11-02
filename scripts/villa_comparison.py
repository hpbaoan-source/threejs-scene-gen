#!/usr/bin/env python3
"""Compose side-by-side: reference photo | attempt-0 | attempt-1 | final."""
import sys
from PIL import Image, ImageDraw

W = 560
items = [
    ("Anh goc\nanh tham chieu", "/home/anhuynh/.nanobot/media/telegram/AQADmBZrG6g5QVd9.jpg"),
    ("Vong 0 - 6/10\nthieu ho boi", "/home/anhuynh/work/threejs-scene-gen/runs/villa-20261102-220318/attempt-0.png"),
    ("Vong 1 - 6/10\nco ho boi", "/home/anhuynh/work/threejs-scene-gen/runs/villa-fix-20261102-220813/attempt-1.png"),
    ("Vong 2 - 9/10\nfinal", "/home/anhuynh/work/threejs-scene-gen/runs/villa-fix-20261102-220813/scene.png"),
]
out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/villa-comparison.png"
PAD, HDR = 12, 46

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
