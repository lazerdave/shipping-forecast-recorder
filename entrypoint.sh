#!/bin/bash
set -e

echo "[entrypoint] Starting Shipping Forecast Recorder container"

# Create python3 symlink if it doesn't exist
if [ ! -e /usr/bin/python3 ]; then
    echo "[entrypoint] Creating /usr/bin/python3 symlink..."
    ln -sf /usr/local/bin/python3 /usr/bin/python3
fi

# Start nginx
echo "[entrypoint] Starting nginx..."
nginx -t && nginx

# Set up cron jobs (run setup command)
echo "[entrypoint] Configuring cron jobs..."
cd /app
python3 kiwi_recorder.py setup

# Start cron
echo "[entrypoint] Starting cron..."
cron

# Create initial log file
touch /data/logs/shipping-forecast.log

echo "[entrypoint] Container ready"

# Execute the CMD
exec "$@"
