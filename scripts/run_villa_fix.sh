#!/usr/bin/env bash
# Vong 2: tinh chinh tu scene hien tai, nhan manh ho boi + mai ngoi + bac them.
set -uo pipefail

REPO="/home/anhuynh/work/threejs-scene-gen"
TS=$(date +%Y%m%d-%H%M%S)
WORK="$REPO/runs/villa-fix-$TS"
START="$REPO/runs/villa-20261102-220318/scene.html"

PROMPT='a modern luxury villa seen from a high aerial isometric angle: a two-storey white house with a DARK NAVY BLUE tiled hip roof with clearly visible sloped roof planes (not a flat roof), dormer windows and a chimney, white columns and a covered porch, WIDE stone steps at the front entrance. In the walled garden beside the house there is a LARGE LONG RECTANGULAR SWIMMING POOL filled with bright saturated blue water, clearly visible from above, taking about a third of the garden, surrounded by a light stone pool deck. Neatly trimmed hedges, red and pink flower beds, gravel and stone paving, one white car parked in the driveway and another white car parked on the road outside the metal fence, tall green trees and grass around the property, bright daytime lighting, architectural visualization style'

cd "$REPO"
echo "workdir: $WORK"
python3 make_scene.py \
  --mode repair \
  --repair 2 \
  --threshold 8 \
  --start-from "$START" \
  --workdir "$WORK" \
  --out "$WORK/final.html" \
  "$PROMPT"
echo "EXIT=$?"
