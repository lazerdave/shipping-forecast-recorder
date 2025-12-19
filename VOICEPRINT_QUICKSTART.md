# Voiceprint System - Quick Start Guide

This guide gets the voiceprint identification system running from scratch.

## Prerequisites

- [x] Pi (zigbee) with shipping forecast recorder operational
- [x] Rack accessible at 192.168.4.64
- [x] `/mnt/rack-shipping` mounted on Pi
- [x] Archive of recordings exists at `/mnt/rack-shipping/YYYY/MM/`
- [x] SSH key access to Rack configured

## Installation (15-20 minutes)

### Step 1: Install Dependencies on Rack (5 min)

```bash
ssh root@192.168.4.64

# Install Python packages (this may take a few minutes)
pip install pyannote.audio torch torchaudio

# Verify installation
python3 -c "import pyannote.audio; print('✓ pyannote.audio installed')"
python3 -c "import torch; print('✓ torch installed')"

exit
```

### Step 2: Install Speaker Recognition Script on Rack (1 min)

```bash
cd /home/pi/projects/shipping-forecast-recorder

# Copy script to Rack
scp speaker_recognition.py root@192.168.4.64:/usr/local/bin/

# Make executable
ssh root@192.168.4.64 chmod +x /usr/local/bin/speaker_recognition.py

# Test
ssh root@192.168.4.64 "/usr/local/bin/speaker_recognition.py --help"
# Should show help text
```

### Step 3: Analyze Archive (10-30 min depending on archive size)

```bash
cd /home/pi/projects/shipping-forecast-recorder

# Start with a small sample to test
python3 analyze_archive.py --limit 20 --output test_labels.json

# Review results
less test_labels.json
# Press 'q' to quit

# If test looks good, analyze full archive
# (For ~200 recordings, this takes ~15-20 minutes)
python3 analyze_archive.py --output presenter_labels.json
```

**What to look for in results:**
- At least 5-10 recordings per presenter for training
- Reasonable detection rate (> 70% of recordings identified)
- Check "unknowns" - these might be new presenters to add to database

### Step 4: Build Voiceprint Database (5-15 min)

```bash
# Ensure Rack is mounted
mount | grep rack-shipping
# Should show: /mnt/rack-shipping

# Create voiceprints directory
mkdir -p /mnt/rack-shipping/voiceprints

# Build database
# (For ~150 samples, this takes ~8-12 minutes)
python3 build_voiceprint_database.py presenter_labels.json \
    --max-samples 10 \
    --output /mnt/rack-shipping/voiceprints/database.json \
    --metadata-output /mnt/rack-shipping/voiceprints/metadata.json
```

**Expected output:**
```
Extracting embeddings for 15 presenters...
[  1/150] ShippingFCST-251201_AM_004700UTC...
  Copying to Rack...
  Extracting embedding...
  ✓ Extracted 512-dimensional embedding
...

DATABASE VALIDATION
Total presenters: 15
Total embeddings: 147

Within-speaker similarity: mean=0.874 std=0.042
Between-speaker similarity: mean=0.412 std=0.089

✓ Database saved to: /mnt/rack-shipping/voiceprints/database.json
```

**Quality checks:**
- Within-speaker similarity should be > 0.70 (ideally > 0.80)
- Between-speaker similarity should be < 0.50 (ideally < 0.40)
- If these don't look good, you may need more/better training samples

### Step 5: Verify Installation

```bash
# Check database exists and is reasonable size
ls -lh /mnt/rack-shipping/voiceprints/database.json
# Should be ~40-50 KB

# Check voiceprint fallback is enabled in config
grep "USE_VOICEPRINT_FALLBACK" /home/pi/kiwi_recorder.py
# Should show: USE_VOICEPRINT_FALLBACK = True

# Test on a recording
python3 -c "
import sys
sys.path.insert(0, '/home/pi')
from kiwi_recorder import identify_by_voiceprint, setup_logging
import os

logger = setup_logging(None)

# Find most recent recording
recordings = sorted([f for f in os.listdir('/home/pi/share/198k/') if f.endswith('.wav')])
if recordings:
    test_file = f'/home/pi/share/198k/{recordings[-1]}'
    print(f'Testing on: {recordings[-1]}')
    result = identify_by_voiceprint(test_file, logger)
    print(f'Result: {result.get(\"presenter\")} ({result.get(\"confidence\"):.3f})')
"
```

## Done!

The voiceprint system is now active. Future recordings will automatically use voiceprint fallback when name extraction fails.

## What Happens Now

### During Next Recording

1. Recording completes at ~00:47 London time
2. Name extraction attempts to identify presenter from sign-off
3. **If unsuccessful or uncertain → Voiceprint fallback triggers**
4. Audio sent to Rack for voiceprint matching
5. Best match returned with confidence score
6. If high confidence (>0.85): Accept match
7. If uncertain: Flag for review in MQTT notification

### Monitoring Results

**Check MQTT messages:**
```bash
# Subscribe to status topic
mosquitto_sub -h 192.168.4.64 -t "shipping-forecast/status" -v
```

**Check sidecar files:**
```bash
# View latest recording's presenter detection
cat /home/pi/share/198k/*.txt | grep -A 10 "PRESENTER"
```

**Check logs:**
```bash
# Look for voiceprint activity
tail -f /home/pi/Shipping_Forecast_SDR_Recordings.log | grep voiceprint
```

## Typical Results

### Case 1: High Confidence Match (Al Ryan example)

```
[presenter] No presenter sign-off detected
[presenter] Trying voiceprint fallback...
[voiceprint] Copying audio to Rack...
[voiceprint] Comparing against database...
[voiceprint] High confidence: Al Ryan (0.876)
[presenter] Voiceprint identified: Al Ryan (similarity: 0.876)
```

**MQTT notification:**
```json
{
  "event": "presenter",
  "presenter": "Al Ryan",
  "match_type": "voiceprint",
  "confidence": 0.876,
  "voiceprint_used": true,
  "needs_review": false
}
```

### Case 2: Uncertain Match (Too Close to Call)

```
[voiceprint] Too close to call: John Hammond (0.721) vs Al Ryan (0.693)
[presenter] Voiceprint uncertain, flagging for review
```

**MQTT notification:**
```json
{
  "event": "presenter",
  "match_type": "voiceprint_uncertain",
  "needs_review": true,
  "review_reason": "Voiceprint uncertain: John Hammond (0.721) vs Al Ryan (0.693)",
  "voiceprint_candidates": [
    {"name": "John Hammond", "similarity": 0.721},
    {"name": "Al Ryan", "similarity": 0.693}
  ]
}
```

## Maintenance

### When to Retrain

- **New presenter discovered:** Add to database, retrain
- **Every 3-6 months:** Retrain with fresh recordings
- **After 50+ new recordings:** Optional retrain for better accuracy

### How to Retrain

```bash
cd /home/pi/projects/shipping-forecast-recorder

# Re-analyze archive (only recent additions if you want)
python3 analyze_archive.py --year 2025 --month 12 --output labels_dec.json

# Merge with existing labels or use fresh
python3 analyze_archive.py --output presenter_labels_latest.json

# Backup old database
cp /mnt/rack-shipping/voiceprints/database.json \
   /mnt/rack-shipping/voiceprints/database_backup_$(date +%Y%m%d).json

# Build new database
python3 build_voiceprint_database.py presenter_labels_latest.json \
    --max-samples 12 \
    --output /mnt/rack-shipping/voiceprints/database.json
```

## Troubleshooting

### "pyannote.audio not installed" error

**On Rack:**
```bash
ssh root@192.168.4.64
pip install pyannote.audio torch torchaudio
```

### Voiceprint fallback not triggering

**Check:**
1. Config enabled: `grep USE_VOICEPRINT_FALLBACK /home/pi/kiwi_recorder.py`
2. Database exists: `ls /mnt/rack-shipping/voiceprints/database.json`
3. Rack accessible: `ssh root@192.168.4.64 echo OK`

### Low accuracy / many "review" flags

**Possible causes:**
- Insufficient training samples (need 5-10 per presenter)
- Poor quality recordings
- Similar-sounding voices

**Solutions:**
- Re-train with more samples: `--max-samples 15`
- Lower confidence threshold in kiwi_recorder.py config
- Review validation stats when building database

### Database too large

**Normal size:** ~40-60 KB (20 presenters × 10 samples)

If much larger:
- You may have too many samples per presenter
- Reduce: `--max-samples 8`

## Need Help?

1. Check logs: `tail -100 /home/pi/Shipping_Forecast_SDR_Recordings.log`
2. Read full documentation: `less VOICEPRINT_SYSTEM.md`
3. Check shared knowledge: `/home/pi/Documents/claude-shared-knowledge/`

---

**Installation complete!** The voiceprint system is now running and will automatically identify presenters who don't give their standard sign-off.
