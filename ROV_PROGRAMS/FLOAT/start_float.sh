#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
    echo ""
    echo "Stopping float services..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
    echo "Done."
}
trap cleanup SIGINT SIGTERM

echo "Starting Float backend (port 5000)..."
cd "$SCRIPT_DIR/FloatSource"
python FloatAPI.py &
BACKEND_PID=$!

echo "Starting Float frontend (port 3000)..."
cd "$SCRIPT_DIR/FloatFrontend"
npm run dev -- --host &
FRONTEND_PID=$!

echo "Both services running. Press Ctrl+C to stop."
wait
