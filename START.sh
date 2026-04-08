#!/bin/bash
# START.sh — double-click this in your file manager to launch GetPackets.
# Right-click → Run as Program  (if double-click doesn't work)

cd "$(dirname "$0")"

# Check setup has been run
if [ ! -d "venv" ]; then
    echo "Running first-time setup..."
    bash setup.sh
fi

source venv/bin/activate

# Kill any existing dashboard on port 8080
fuser -k 8080/tcp 2>/dev/null || true
sleep 1

# Start dashboard in background
python dashboard/app.py &
DASH_PID=$!

# Wait then open browser
sleep 2
xdg-open http://localhost:8080 2>/dev/null || \
  python3 -m webbrowser http://localhost:8080

echo ""
echo "  GetPackets is running at http://localhost:8080"
echo "  Close this window to stop."
echo ""

# Keep alive until window closed
wait $DASH_PID
