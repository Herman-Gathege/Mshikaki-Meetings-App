#!/usr/bin/env bash
# Keyboard focus, contrast and answer-card sizes for a running Mshikaki.
#
#   ./scripts/ux-contrast-audit.sh
#
# Contrast is measured from the pixels the browser paints, with translucent card
# backgrounds composited over their real parents.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_URL="${APP_URL:-http://172.16.1.36:8090}"
PORT="${CDP_PORT:-9334}"
NODE="${NODE:-node}"
PROFILE="$(mktemp -d)"

if [[ ! -f /tmp/mshikaki-ux.json ]]; then
  echo "Missing /tmp/mshikaki-ux.json: see scripts/ux-audit.sh." >&2
  exit 1
fi

google-chrome --headless=new --disable-gpu --no-sandbox --no-first-run \
  --disable-background-networking --disable-component-update --disable-sync \
  --mute-audio --remote-debugging-port="$PORT" --user-data-dir="$PROFILE" \
  about:blank >/tmp/mshikaki-contrast-chrome.log 2>&1 &
CHROME_PID=$!
trap 'kill "$CHROME_PID" 2>/dev/null || true' EXIT

sleep 5
CDP="$(curl -s --max-time 5 "http://localhost:${PORT}/json/list" \
  | python3 -c "import sys,json; ts=[t for t in json.load(sys.stdin) if t['type']=='page']; print(ts[0]['webSocketDebuggerUrl'] if ts else '')")"

if [[ -z "$CDP" ]]; then
  echo "Could not reach the browser debugging port on ${PORT}." >&2
  exit 1
fi

APP_URL="$APP_URL" CDP_ENDPOINT="$CDP" "$NODE" "$HERE/ux-contrast-audit.mjs"
