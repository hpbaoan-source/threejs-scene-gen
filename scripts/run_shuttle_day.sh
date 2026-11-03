#!/usr/bin/env bash
# Vong 3: tu attempt 1 (co lua + khoi + thap dung), chuyen sang ban ngay.
set -uo pipefail

REPO="/home/anhuynh/work/threejs-scene-gen"
IMG="/home/anhuynh/.nanobot/media/telegram/AQADlhprG6g5SVd-.jpg"
TS=$(date +%Y%m%d-%H%M%S)
WORK="$REPO/runs/shuttle-day-$TS"
START="$REPO/runs/shuttle-ref-20261103-144920/attempt-1.html"

PROMPT='the same shuttle launch scene, but in bright daylight: a deep blue daytime sky with soft wispy white clouds instead of the dark night sky, the whole scene brightly sunlit so the white vehicle, the beige steel launch tower and the smoke are all clearly readable, strong daylight from the upper right with crisp shadows on the tower and on the pad. Keep the vehicle exactly as it is: the white orbiter with black belly tiles and delta wings, the orange-brown external fuel tank with its pointed nose, the two white solid rocket boosters with black bands and orange interstage sections, the two brilliant white-yellow exhaust plumes under the boosters and the bank of billowing white smoke at the base, and the launch tower with its lightning mast and floodlight ring on the left. Do not move, split, detach or resize any part of the vehicle, and keep the HUD panels.'

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
