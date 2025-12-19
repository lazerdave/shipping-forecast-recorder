#!/bin/bash
# Quick conversion status check

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Legacy Archive Conversion - Status Check              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if process is running
RUNNING=$(ps aux | grep convert_legacy_archive.py | grep -v grep | wc -l)
if [ $RUNNING -gt 0 ]; then
    echo "✓ Conversion process: RUNNING"
    ps aux | grep convert_legacy_archive.py | grep -v grep | awk '{print "  PID: " $2 ", Started: " $9}'
else
    echo "✗ Conversion process: NOT RUNNING"
fi
echo ""

# Count completed files
COMPLETED=$(find /mnt/rack-shipping/2024 -name 'ShippingFCST-*--legacy--*.mp3' 2>/dev/null | wc -l)
echo "Progress: $COMPLETED / 301 files converted"

# Calculate percentage
PERCENT=$(echo "scale=1; $COMPLETED * 100 / 301" | bc)
echo "          $PERCENT% complete"
echo ""

# Show progress bar
FILLED=$(echo "$COMPLETED / 6" | bc)  # 301/50 = ~6 files per bar segment
BAR=""
for i in $(seq 1 50); do
    if [ $i -le $FILLED ]; then
        BAR="${BAR}█"
    else
        BAR="${BAR}░"
    fi
done
echo "[$BAR]"
echo ""

# Estimated completion
if [ $RUNNING -gt 0 ] && [ $COMPLETED -lt 301 ]; then
    REMAINING=$((301 - COMPLETED))
    MINUTES=$((REMAINING * 1))  # ~1 minute per file
    HOURS=$((MINUTES / 60))
    MINS=$((MINUTES % 60))

    COMPLETION=$(date -d "+${MINUTES} minutes" "+%I:%M %p")

    echo "Estimated completion: $COMPLETION (~${HOURS}h ${MINS}m remaining)"
    echo ""
fi

# Show latest log entries
LOG_FILE="/tmp/convert_legacy_full.log"
if [ ! -f "$LOG_FILE" ]; then
    LOG_FILE="/tmp/convert_legacy.log"
fi

if [ -f "$LOG_FILE" ]; then
    echo "Latest activity:"
    echo "───────────────────────────────────────────────────────────────"
    tail -8 "$LOG_FILE" | sed 's/^/  /'
fi

echo ""
echo "Full logs: $LOG_FILE"
echo "Status doc: /home/pi/projects/shipping-forecast-recorder/CONVERSION_STATUS.md"
