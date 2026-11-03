#!/usr/bin/env bash
# Sinh scene Space Shuttle phong tu anh tham chieu - chay trong tmux.
set -uo pipefail

REPO="/home/anhuynh/work/threejs-scene-gen"
IMG="/home/anhuynh/.nanobot/media/telegram/AQADlhprG6g5SVd-.jpg"
TS=$(date +%Y%m%d-%H%M%S)
WORK="$REPO/runs/shuttle-$TS"

PROMPT='a NASA Space Shuttle Discovery climbing away from the launch pad, wide landscape frame, low camera angle looking up from the ground: on the RIGHT third of the frame the shuttle stack ascending, with a white orbiter with a black nose cap, black thermal tiles on the belly and wing leading edges and a white vertical tail, attached to a large orange-brown external fuel tank with a pointed nose cone, flanked by TWO white solid rocket boosters with pointed white nose cones, black band markings and orange interstage sections. TWO separate exhaust plumes burning below the boosters, each with a narrow brilliant white-yellow core. On the LEFT third of the frame a tall weathered beige steel lattice launch tower with several levels of white platform walkways and stairs, a tall white cylindrical lightning mast rising high above it, a large round floodlight cluster in a ring pointing forward, a hammerhead crane arm reaching to the right, and thin tension cables in the sky. A huge bank of billowing white and grey smoke clouds fills the bottom of the frame, warmly tinted orange and yellow where the flame lights it, with the cream coloured pad structures and water tank on the left. Deep blue sky with soft wispy clouds, bright daylight, photorealistic'

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
