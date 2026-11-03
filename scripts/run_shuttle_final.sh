#!/usr/bin/env bash
# Vong cuoi: seed = scene da fix sRGB (troi ngan), repair de them khoi + lua.
set -uo pipefail

REPO="/home/anhuynh/work/threejs-scene-gen"
IMG="/home/anhuynh/.nanobot/media/telegram/AQADlhprG6g5SVd-.jpg"
TS=$(date +%Y%m%d-%H%M%S)
WORK="$REPO/runs/shuttle-final-$TS"
SEED="/tmp/shuttle-dayfix.html"

PROMPT='a NASA Space Shuttle Discovery climbing away from its launch pad on a bright clear day: deep blue daytime sky with soft wispy white clouds, the white shuttle stack on the right third of the frame with the orbiter, the orange-brown external fuel tank and the two white solid rocket boosters, TWO brilliant white-yellow exhaust plumes with narrow bright cores burning under the boosters, a huge bank of billowing white and grey smoke clouds filling the bottom of the frame and lit warm orange by the flame, the weathered beige steel launch tower on the left with white platform walkways, a tall white lightning mast, a round floodlight cluster in a ring and a hammerhead crane arm, thin tension cables across the sky, and the cream coloured pad structures with a water tank at the lower left. Keep the vehicle assembly intact and keep the existing HUD panels.'

cd "$REPO"
echo "workdir: $WORK"
python3 make_scene.py \
  --mode repair \
  --repair 2 \
  --threshold 7 \
  --image "$IMG" \
  --ref-in-review \
  --start-from "$SEED" \
  --workdir "$WORK" \
  --out "$WORK/final.html" \
  "$PROMPT"
echo "EXIT=$?"
