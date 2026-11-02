#!/usr/bin/env bash
# Serve the scene gallery locally (durable) and expose it via an ngrok tunnel.
# Usage: scripts/serve_gallery.sh [--no-tunnel]
set -euo pipefail

REPO="/home/anhuynh/work/threejs-scene-gen"
DOCS="$REPO/docs"
PORT=8899
LOG="/tmp/gallery-server.log"

# --- static server -------------------------------------------------------
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then
  echo "server: already listening on :$PORT"
else
  pkill -f "http.server $PORT" 2>/dev/null || true
  sleep 1
  cd "$REPO"
  setsid nohup python3 -m http.server "$PORT" --bind 0.0.0.0 --directory "$DOCS" \
    > "$LOG" 2>&1 < /dev/null &
  sleep 2
  if ss -ltn 2>/dev/null | grep -q ":$PORT "; then
    echo "server: started on :$PORT (log $LOG)"
  else
    echo "server: FAILED to start (see $LOG)"; exit 1
  fi
fi

# --- ngrok tunnel --------------------------------------------------------
if [ "${1:-}" = "--no-tunnel" ]; then
  echo "tunnel: skipped"
  exit 0
fi

NGROK_BIN="/usr/local/bin/ngrok"
[ -x "$NGROK_BIN" ] || NGROK_BIN="$(command -v ngrok || echo ngrok)"

pkill -f "ngrok http $PORT" 2>/dev/null || true
sleep 1
setsid nohup "$NGROK_BIN" http "$PORT" --log=stdout \
  > /tmp/ngrok-gallery.log 2>&1 < /dev/null &
sleep 6

URL=$(grep -hoE 'https://[a-z0-9.-]+\.(ngrok\.app|ngrok-free\.app|ngrok\.io)' /tmp/ngrok-gallery.log 2>/dev/null | head -1 || true)
if [ -n "$URL" ]; then
  echo "tunnel: $URL"
  echo "$URL" > /tmp/gallery-public-url.txt
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "$URL/index.html")
  echo "verify: GET $URL/index.html -> $code"
else
  echo "tunnel: FAILED to get URL (see /tmp/ngrok-gallery.log)"
  tail -20 /tmp/ngrok-gallery.log
  exit 1
fi
