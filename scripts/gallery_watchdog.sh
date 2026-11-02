#!/usr/bin/env bash
# Keep the gallery tunnel alive. Run from OS cron every 15 min.
# - If the current public URL answers 200 -> do nothing.
# - If it is dead -> restart the tunnel and write the new URL to
#   /home/anhuynh/workspace/gallery-url.txt (URL changes on ngrok free tier).
set -uo pipefail

REPO="/home/anhuynh/work/threejs-scene-gen"
STATE="/home/anhuynh/workspace/gallery-url.txt"
PORT=8899

current=$(cat "$STATE" 2>/dev/null | tr -d '[:space:]')
if [ -n "$current" ] && curl -s -o /dev/null -m 15 -w '%{http_code}' "$current/index.html" | grep -q 200; then
  exit 0
fi

# tunnel or server is down -> rebuild both
bash "$REPO/scripts/serve_gallery.sh" > /tmp/gallery-watchdog.log 2>&1
new_url=$(cat /tmp/gallery-public-url.txt 2>/dev/null | tr -d '[:space:]')
if [ -n "$new_url" ] && [ "$new_url" != "$current" ]; then
  printf '%s\n' "$new_url" > "$STATE"
  echo "gallery url changed: $current -> $new_url" >> /tmp/gallery-watchdog.log
fi
