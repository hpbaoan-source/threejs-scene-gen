#!/usr/bin/env bash
# Vong cuoi: 4 sua doi cu the - scale, khoi, lua, thap.
set -uo pipefail

REPO="/home/anhuynh/work/threejs-scene-gen"
IMG="/home/anhuynh/.nanobot/media/telegram/AQADlhprG6g5SVd-.jpg"
TS=$(date +%Y%m%d-%H%M%S)
WORK="$REPO/runs/shuttle-smoke-$TS"
START="$REPO/runs/shuttle-final-20261103-150941/scene.html"

PROMPT='same camera angle and same blue daylight sky, same HUD panels, but fix these four things: 1) make the whole shuttle stack about 1.6 times bigger in frame so it dominates the shot and the pointed nose of the external tank sits close to the top edge; 2) delete the flat white fog layer and build a huge bank of billowing smoke instead, out of at least 40 overlapping low-poly spheres of radius 6 to 16 in white and light grey, clustered in a wide mass around the base of the exhaust plumes and across the pad, rising to about a third of the frame height, with soft edges and varied sizes; 3) make both exhaust plumes brilliant - a white-hot narrow core inside a wider orange-yellow cone, and add an orange PointLight at the base of each plume so the smoke around it is lit warm from below; 4) rebuild the launch tower denser - beige weathered steel lattice with more levels of white platform walkways and stairs, keeping the tall white lightning mast, the round floodlight ring in a ring shape and the tension cables. Do not move the orbiter, the external tank or the two boosters away from each other.'

cd "$REPO"
echo "workdir: $WORK"
python3 make_scene.py \
  --mode repair \
  --repair 2 \
  --threshold 7 \
  --image "$IMG" \
  --ref-in-review \
  --start-from "$START" \
  --workdir "$WORK" \
  --out "$WORK/final.html" \
  "$PROMPT"
echo "EXIT=$?"
