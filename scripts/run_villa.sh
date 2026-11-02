#!/usr/bin/env bash
# Sinh scene biet thu tu anh tham chieu (vision mode) - chay trong tmux.
set -uo pipefail

REPO="/home/anhuynh/work/threejs-scene-gen"
IMG="/home/anhuynh/.nanobot/media/telegram/AQADmBZrG6g5QVd9.jpg"
TS=$(date +%Y%m%d-%H%M%S)
WORK="$REPO/runs/villa-$TS"

PROMPT='a modern luxury villa seen from a high aerial isometric angle: a two-storey white house with a dark navy blue tiled hip roof, dormer windows and a chimney, white columns and a covered porch, wide stone steps at the front entrance, a long rectangular blue swimming pool in the walled garden next to the house with a small poolside deck, neatly trimmed hedges and flower beds with red and pink blossoms, gravel and stone paving around the house, one white car parked in the driveway and another white car parked on the road outside the metal fence, tall green trees and grass around the property, bright daytime lighting, architectural visualization style'

cd "$REPO"
echo "workdir: $WORK"
python3 make_scene.py \
  --mode repair \
  --repair 3 \
  --threshold 7 \
  --image "$IMG" \
  --workdir "$WORK" \
  --out "$WORK/final.html" \
  "$PROMPT"
echo "EXIT=$?"
