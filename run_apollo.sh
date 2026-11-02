#!/bin/bash
# Apollo test: A = one-shot, B = repair loop starting from A's artefact.
set -u
cd /home/anhuynh/work/threejs-scene-gen
mkdir -p results

PROMPT="an Apollo spacecraft standing on its launch pad at dawn, the tall umbilical service tower beside it, xenon floodlights on the pad, steam venting from the flame trench, a cinematic low-angle wide shot, the sun just rising over a clear sky"

echo "=== A: one-shot ===" > results/apollo-A.log
python3 make_scene.py --mode oneshot "$PROMPT" \
  --workdir /home/anhuynh/work/threejs-scene-gen/results/apollo-A-oneshot \
  >> results/apollo-A.log 2>&1
echo "A_DONE rc=$?" >> results/apollo-A.log

echo "=== B: repair loop, starting from A ===" > results/apollo-B.log
python3 make_scene.py --mode repair --repair 3 --threshold 7 \
  --start-from /home/anhuynh/work/threejs-scene-gen/results/apollo-A-oneshot/scene.html \
  "$PROMPT" \
  --workdir /home/anhuynh/work/threejs-scene-gen/results/apollo-B-repair \
  >> results/apollo-B.log 2>&1
echo "B_DONE rc=$?" >> results/apollo-B.log

echo "ALL_DONE" > results/APOLLO_COMPLETE
