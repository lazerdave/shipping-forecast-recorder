# Legacy Archive Conversion - Status & Recovery

## Current Operation

**Task:** Converting 301 legacy MP4 files to ShippingFCST format
**Started:** Wed Dec 18, 2025 6:45 PM MST (restarted with anthem detection fix)
**Expected completion:** ~11:45 PM MST (~5 hours total)
**Background process:** Running via `convert_legacy_archive.py` (PID 713154)
**Status:** ✓ Anthem detection now working (sample rate resampling fix applied)

## Check Status

### Is conversion still running?
```bash
ps aux | grep convert_legacy_archive.py | grep -v grep
# If you see output, it's still running
```

### Check current progress
```bash
# View latest log entries
tail -50 /tmp/convert_legacy.log

# Watch in real-time
tail -f /tmp/convert_legacy.log

# Count completed conversions
find /mnt/rack-shipping/2024 -name "ShippingFCST-*--legacy--*.mp3" | wc -l
# Should increase over time, max is 301
```

### Check for errors
```bash
grep -i "failed\|error" /tmp/convert_legacy.log | tail -20
```

## Recovery (If Process Stopped)

The conversion script **automatically skips already-converted files**, so you can safely re-run it:

```bash
cd /home/pi/projects/shipping-forecast-recorder

# Resume conversion (will skip completed files)
python3 convert_legacy_archive.py > /tmp/convert_legacy_resume.log 2>&1 &

# Monitor resumed conversion
tail -f /tmp/convert_legacy_resume.log
```

## When Conversion Completes

You'll have:
- **301 legacy recordings** (Sept-Dec 2024)
- **36 new recordings** (Nov-Dec 2025)
- **Total: ~337 recordings**

### Next Steps

1. **Re-run archive analysis:**
   ```bash
   cd /home/pi/projects/shipping-forecast-recorder

   # Analyze full archive (will take ~3-4 hours)
   python3 analyze_archive.py --archive-path /mnt/rack-shipping \
       --output presenter_labels_full.json
   ```

2. **Build voiceprint database:**
   ```bash
   # Build with expanded dataset
   python3 build_voiceprint_database.py presenter_labels_full.json \
       --max-samples 15 \
       --output /mnt/rack-shipping/voiceprints/database.json \
       --metadata-output /mnt/rack-shipping/voiceprints/metadata.json
   ```

3. **Install speaker recognition on Rack** (if not done yet):
   ```bash
   # Copy script to Rack
   scp speaker_recognition.py root@192.168.4.64:/usr/local/bin/
   ssh root@192.168.4.64 chmod +x /usr/local/bin/speaker_recognition.py

   # Install dependencies (if not done)
   ssh root@192.168.4.64 "pip install pyannote.audio torch torchaudio"
   ```

## Quick Status Check (Copy/Paste)

```bash
echo "=== Conversion Status ==="
echo "Started: Wed Dec 18, 2025 ~11:19 MST"
echo "Current time: $(date)"
echo ""
echo "Running: $(ps aux | grep convert_legacy_archive.py | grep -v grep | wc -l) process(es)"
echo "Completed: $(find /mnt/rack-shipping/2024 -name 'ShippingFCST-*--legacy--*.mp3' 2>/dev/null | wc -l) / 301 files"
echo ""
echo "Latest log entries:"
tail -5 /tmp/convert_legacy.log
```

## Files & Logs

- **Main log:** `/tmp/convert_legacy.log`
- **Script:** `/home/pi/projects/shipping-forecast-recorder/convert_legacy_archive.py`
- **Output:** `/mnt/rack-shipping/2024/{MM}/ShippingFCST-*--legacy--*.{wav,mp3,txt}`

## Troubleshooting

### Conversion appears stuck
```bash
# Check if ffmpeg processes are running
ps aux | grep ffmpeg

# Check disk space
df -h /mnt/rack-shipping

# Check last modified files
ls -lt /mnt/rack-shipping/2024/*/ | head -20
```

### Need to stop conversion
```bash
# Find and kill process
pkill -f convert_legacy_archive.py

# Or find PID and kill specifically
ps aux | grep convert_legacy_archive.py
kill <PID>
```

### Restart fresh (delete partial conversions)
```bash
# WARNING: This deletes all legacy conversions!
find /mnt/rack-shipping/2024 -name "ShippingFCST-*--legacy--*" -delete

# Then re-run conversion
python3 convert_legacy_archive.py > /tmp/convert_legacy.log 2>&1 &
```

---

**Last Updated:** Wed Dec 18, 2025 6:50 PM MST
**Status:** Conversion in progress with anthem detection working
**Session Details:** See SESSION_2025-12-18.md for complete fix documentation
