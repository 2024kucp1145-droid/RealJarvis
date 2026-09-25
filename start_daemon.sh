#!/bin/bash
# ============================================================
# RealJarvis 24/7 Always-On Daemon (Linux / Cloud Launcher)
# ============================================================
cd "$(dirname "$0")"

if [ -f "venv/bin/python" ]; then
    PYTHON_BIN="venv/bin/python"
else
    PYTHON_BIN="python3"
fi

echo "============================================================"
echo "  Starting RealJarvis 24/7 Always-On Daemon (Linux/Cloud)"
echo "============================================================"

while true; do
    echo "[$(date)] Launching RealJarvis Daemon Gateway..."
    $PYTHON_BIN daemon_api_server.py
    echo "[$(date)] Daemon exited. Restarting in 5 seconds... (Press Ctrl+C to abort)"
    sleep 5
done
