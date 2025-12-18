#!/bin/bash
# Watchdog script for Shipping Forecast Recorder
# Verifies pi user's crontab is intact and restores if needed
# Run from system crontab (root) for independence

BACKUP_CRONTAB="/home/pi/projects/shipping-forecast-recorder/crontab.backup"
MQTT_BROKER="192.168.4.64"
MQTT_TOPIC="shipping-forecast/status"
LOG="/home/pi/Shipping_Forecast_SDR_Recordings.log"
MARKER="KIWI-SDR AUTO"

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - WATCHDOG - $1" >> "$LOG"
}

send_mqtt() {
    local message="$1"
    local payload=$(cat <<EOF
{
    "event": "watchdog_alert",
    "message": "$message",
    "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
    "hostname": "$(hostname)"
}
EOF
)
    mosquitto_pub -h "$MQTT_BROKER" -t "$MQTT_TOPIC" -m "$payload" 2>/dev/null
}

# Check if backup exists
if [[ ! -f "$BACKUP_CRONTAB" ]]; then
    log_msg "ERROR: Backup crontab not found at $BACKUP_CRONTAB"
    send_mqtt "Backup crontab file missing!"
    exit 1
fi

# Get current crontab for pi user
CURRENT_CRONTAB=$(sudo -u pi crontab -l 2>/dev/null)

# Check if marker exists in current crontab
if echo "$CURRENT_CRONTAB" | grep -q "$MARKER"; then
    # Crontab looks good
    exit 0
else
    # Crontab is missing or corrupted - restore it
    log_msg "WARNING: Crontab missing KIWI-SDR entries! Restoring from backup..."

    if sudo -u pi crontab "$BACKUP_CRONTAB"; then
        log_msg "SUCCESS: Crontab restored from backup"
        send_mqtt "Crontab was empty/corrupted and has been restored from backup"
    else
        log_msg "ERROR: Failed to restore crontab!"
        send_mqtt "CRITICAL: Failed to restore crontab - manual intervention required"
        exit 1
    fi
fi
