#!/bin/bash
# Recording Monitor for Shipping Forecast Recorder
# Checks if today's recording was successfully created
# Run ~30 min after expected recording time (e.g., 18:15 local if recording at 17:47)

SHARE_DIR="/home/pi/share/198k"
MQTT_BROKER="192.168.4.64"
MQTT_TOPIC="shipping-forecast/status"
LOG="/home/pi/Shipping_Forecast_SDR_Recordings.log"

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - MONITOR - $1" >> "$LOG"
}

send_mqtt() {
    local status="$1"
    local message="$2"
    local payload=$(cat <<EOF
{
    "event": "recording_monitor",
    "status": "$status",
    "message": "$message",
    "expected_date": "$EXPECTED_DATE",
    "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
    "hostname": "$(hostname)"
}
EOF
)
    mosquitto_pub -h "$MQTT_BROKER" -t "$MQTT_TOPIC" -m "$payload" 2>/dev/null
}

# Calculate expected recording date (UTC)
# The recording at 00:47 UTC gets a filename with that UTC date
# If local time is before 00:47 UTC, we're still waiting for today's recording
# If local time is after 00:47 UTC, we should have today's recording

# Get current UTC date in the format used by filenames (YYMMDD)
EXPECTED_DATE=$(date -u '+%y%m%d')

# Look for today's processed MP3 file
PATTERN="ShippingFCST-${EXPECTED_DATE}_AM_*_processed.mp3"
FOUND_FILE=$(find "$SHARE_DIR" -name "$PATTERN" -type f 2>/dev/null | head -1)

if [[ -n "$FOUND_FILE" ]]; then
    # Recording exists
    FILE_SIZE=$(stat -c%s "$FOUND_FILE" 2>/dev/null)
    if [[ "$FILE_SIZE" -gt 1000000 ]]; then
        # File is larger than 1MB - looks good
        log_msg "OK: Today's recording found: $(basename "$FOUND_FILE") (${FILE_SIZE} bytes)"
        exit 0
    else
        # File exists but is suspiciously small
        log_msg "WARNING: Recording exists but is only ${FILE_SIZE} bytes: $FOUND_FILE"
        send_mqtt "warning" "Recording file is suspiciously small (${FILE_SIZE} bytes)"
        exit 1
    fi
else
    # No recording found for today
    log_msg "ALERT: No recording found for $EXPECTED_DATE!"
    send_mqtt "missing" "No recording found for today ($EXPECTED_DATE). Check crontab and logs."

    # Also check if crontab is intact
    if ! crontab -l 2>/dev/null | grep -q "KIWI-SDR AUTO"; then
        log_msg "CRITICAL: Crontab is also missing!"
        send_mqtt "critical" "Recording missing AND crontab is empty!"
    fi

    exit 1
fi
