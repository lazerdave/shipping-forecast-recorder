# Voiceprint Identification System

## Overview

The voiceprint identification system provides a fallback method for identifying BBC Radio 4 announcers when they don't give their standard sign-off ("This is..."). It uses speaker recognition technology to match voices against a reference database.

**Use Case Example:** Last night's recording (2025-12-17) where Al Ryan simply said "And that completes the Shipping Forecast" without identifying himself.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Pi (zigbee)                                                  │
│                                                              │
│  1. Record Shipping Forecast                                │
│  2. Try name extraction from sign-off                       │
│  3. If fails/uncertain → Voiceprint fallback                │
│                            ↓                                 │
└────────────────────────────┼────────────────────────────────┘
                             │ (sends audio via SSH)
                             ↓
┌──────────────────────────────────────────────────────────────┐
│ Rack (192.168.4.64)                                          │
│                                                              │
│  4. Extract speaker embedding (pyannote.audio)              │
│  5. Compare against voiceprint database                      │
│  6. Return ranked matches with similarity scores             │
│                            ↓                                 │
└────────────────────────────┼────────────────────────────────┘
                             │ (returns JSON)
                             ↓
┌──────────────────────────────────────────────────────────────┐
│ Pi (zigbee)                                                  │
│                                                              │
│  7. Use voiceprint match if confidence high enough          │
│  8. Flag for review if uncertain                            │
│  9. Continue processing (feed, MQTT, archive)               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Components

### 1. analyze_archive.py (Pi)

Scans existing recordings to identify which have successfully detected presenters (suitable for training).

**Usage:**
```bash
# Analyze all recordings
python3 analyze_archive.py

# Analyze specific year
python3 analyze_archive.py --year 2025

# Test on small sample
python3 analyze_archive.py --limit 10

# Parallel processing (if needed)
python3 analyze_archive.py --workers 4
```

**Output:** `presenter_labels.json`
- Lists all recordings with detection results
- Flags suitable recordings for training (high confidence matches)
- Summary statistics by presenter

### 2. speaker_recognition.py (Rack)

Core speaker recognition service using pyannote.audio.

**Installation (on Rack):**
```bash
ssh root@192.168.4.64
pip install pyannote.audio torch torchaudio

# Copy script to Rack
scp /home/pi/projects/shipping-forecast-recorder/speaker_recognition.py \
    root@192.168.4.64:/usr/local/bin/

# Make executable
ssh root@192.168.4.64 chmod +x /usr/local/bin/speaker_recognition.py
```

**Commands:**
```bash
# Extract embedding from audio file
python3 speaker_recognition.py extract audio.wav

# Compare against database
python3 speaker_recognition.py compare audio.wav database.json

# Batch process (for database building)
python3 speaker_recognition.py batch files.txt embeddings.json

# Build database from embeddings + labels
python3 speaker_recognition.py build-database embeddings.json labels.json --output database.json
```

### 3. build_voiceprint_database.py (Pi)

Orchestrates database building from analyzed archive.

**Usage:**
```bash
# Build database (default: 10 samples per presenter)
python3 build_voiceprint_database.py presenter_labels.json

# Custom sample count
python3 build_voiceprint_database.py presenter_labels.json --max-samples 15

# Custom output location
python3 build_voiceprint_database.py presenter_labels.json \
    --output /mnt/rack-shipping/voiceprints/database.json \
    --metadata-output /mnt/rack-shipping/voiceprints/metadata.json
```

**Output:**
- `database.json` - Voiceprint database (embeddings for each presenter)
- `metadata.json` - Build metadata, validation stats, source files

### 4. kiwi_recorder.py (Modified)

Main recording script now includes voiceprint fallback.

**New Config Options:**
```python
Config.USE_VOICEPRINT_FALLBACK = True  # Enable/disable
Config.VOICEPRINT_DATABASE = "/mnt/rack-shipping/voiceprints/database.json"
Config.VOICEPRINT_HIGH_CONFIDENCE = 0.85  # High confidence threshold
Config.VOICEPRINT_MEDIUM_CONFIDENCE = 0.70  # Medium confidence threshold
Config.VOICEPRINT_CLOSE_CALL_DELTA = 0.10  # Max delta for "too close"
```

**When Voiceprint Fallback Triggers:**
- No presenter detected from sign-off
- Unknown presenter (not in database)
- Low confidence fuzzy match (< 0.85)

**Decision Logic:**
```
Similarity >= 0.85:  Accept match (high confidence)
Similarity 0.70-0.84:
  - If clear winner: Accept match
  - If close call (delta < 0.10): Flag for review
Similarity < 0.70:   Flag for review (low confidence)
```

## Setup Workflow

### Phase 1: Assess Current Dataset

```bash
# Analyze archive to see what we have
cd /home/pi/projects/shipping-forecast-recorder
python3 analyze_archive.py --output presenter_labels.json

# Review summary
less presenter_labels.json
```

**Expected Output:**
```
Recordings by presenter:
  John Hammond:                  42
  Kelsey Bennett:                28
  Zeb Soanes:                    19
  ...
  (No presenter detected):       15

Suitable for training:
  Total: 127
  John Hammond:                  38
  Kelsey Bennett:                25
  ...
```

### Phase 2: Install Speaker Recognition on Rack

```bash
# Install dependencies on Rack
ssh root@192.168.4.64
pip install pyannote.audio torch torchaudio

# Copy script
scp speaker_recognition.py root@192.168.4.64:/usr/local/bin/
ssh root@192.168.4.64 chmod +x /usr/local/bin/speaker_recognition.py

# Test installation
ssh root@192.168.4.64 "python3 /usr/local/bin/speaker_recognition.py --help"
```

### Phase 3: Build Voiceprint Database

```bash
# Ensure Rack is mounted
mount | grep rack-shipping

# Build database (this will take time - ~3-5 seconds per recording)
python3 build_voiceprint_database.py presenter_labels.json \
    --max-samples 10 \
    --output /mnt/rack-shipping/voiceprints/database.json \
    --metadata-output /mnt/rack-shipping/voiceprints/metadata.json

# Expected duration: ~10 min for 150 recordings
```

**Validation Output:**
```
Within-speaker similarity (higher is better, should be > 0.7):
  John Hammond:                 mean=0.874 std=0.042 (n=45)
  Kelsey Bennett:               mean=0.891 std=0.038 (n=28)
  ...

Between-speaker similarity (lower is better, should be < 0.5):
  Overall mean: 0.412
  Overall std:  0.089

Most similar presenter pairs (potential confusion):
  John Hammond vs Al Ryan:      0.523
  Kelsey Bennett vs Sue Nelson: 0.487
  ...
```

### Phase 4: Enable and Test

```bash
# Voiceprint fallback is now enabled by default in kiwi_recorder.py
# Test on a recording without sign-off (if you have one)

# Check config
grep "USE_VOICEPRINT_FALLBACK" /home/pi/kiwi_recorder.py

# Next recording will use voiceprint fallback automatically
```

## Testing

### Manual Test

```bash
# Test voiceprint on a specific recording
cd /home/pi/projects/shipping-forecast-recorder

# Create test script
cat > test_voiceprint.py <<'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/pi')
from kiwi_recorder import identify_by_voiceprint, setup_logging

logger = setup_logging(None)
result = identify_by_voiceprint(sys.argv[1], logger)

print(f"\nResult: {result}")
print(f"\nTop matches:")
for candidate in result.get('candidates', [])[:5]:
    print(f"  {candidate['name']:30s}: {candidate['similarity']:.3f}")
EOF

chmod +x test_voiceprint.py

# Test on a recording
python3 test_voiceprint.py /mnt/rack-shipping/2025/12/ShippingFCST-251217_AM_004700UTC--norfolk.george-smart.co--avg-54_processed.mp3
```

### Test with Al Ryan Example

```bash
# Find last night's recording (2025-12-17)
ls -lh /home/pi/share/198k/ | grep 251217

# Test voiceprint on it
python3 test_voiceprint.py /home/pi/share/198k/ShippingFCST-251217_AM_004700UTC--[...]_processed.wav
```

**Expected Output:**
```
[voiceprint] Copying audio to Rack...
[voiceprint] Comparing against database...
[voiceprint] High confidence: Al Ryan (0.876)

Result: {'presenter': 'Al Ryan', 'confidence': 0.876, 'match_type': 'voiceprint', ...}

Top matches:
  Al Ryan:                      0.876
  John Hammond:                 0.543
  Kelsey Bennett:               0.421
```

## Monitoring

### MQTT Notifications

Voiceprint results are included in MQTT messages:

```json
{
  "event": "presenter",
  "presenter": "Al Ryan",
  "confidence": 0.876,
  "match_type": "voiceprint",
  "voiceprint_used": true,
  "voiceprint_candidates": [
    {"name": "Al Ryan", "similarity": 0.876, "rank": 1},
    {"name": "John Hammond", "similarity": 0.543, "rank": 2}
  ],
  "needs_review": false
}
```

**Review Flag Cases:**
- `match_type: "unknown"` - Name extracted but not in database
- `match_type: "voiceprint_uncertain"` - Too close to call between two presenters

### Sidecar Files

Presenter info is saved in `.txt` sidecar files:

```
======================================================================
PRESENTER
======================================================================

Presenter: Al Ryan
Confidence: 0.88
Match type: voiceprint
Detection method: Voiceprint matching

Voiceprint candidates:
  1. Al Ryan                (similarity: 0.876)
  2. John Hammond           (similarity: 0.543)
  3. Kelsey Bennett         (similarity: 0.421)
```

## Resource Usage

### Storage

- **Embeddings database:** ~45 KB (22 presenters × 10 samples)
- **Metadata + validation:** ~50 KB
- **Total:** < 100 KB

### Processing Time (per recording)

- **Extract embedding:** 2-5 seconds (CPU on Rack)
- **Compare against database:** < 0.1 seconds
- **Network transfer:** ~1 second (350 KB audio upload)
- **Total overhead:** ~3-6 seconds per recording

### Network Bandwidth

- Upload: ~350 KB (45-second audio segment)
- Download: ~2 KB (JSON result)
- Negligible impact on recording workflow

## Maintenance

### Adding New Presenters

When a new presenter is discovered:

1. Manually verify their identity
2. Add to `presenters.json` database
3. Re-run analysis to find their recordings
4. Re-build voiceprint database

```bash
# Re-analyze with updated presenters.json
python3 analyze_archive.py --output presenter_labels_v2.json

# Re-build database
python3 build_voiceprint_database.py presenter_labels_v2.json \
    --output /mnt/rack-shipping/voiceprints/database_v2.json

# Backup old database
mv /mnt/rack-shipping/voiceprints/database.json \
   /mnt/rack-shipping/voiceprints/database_backup_$(date +%Y%m%d).json

# Activate new database
mv /mnt/rack-shipping/voiceprints/database_v2.json \
   /mnt/rack-shipping/voiceprints/database.json
```

### Periodic Retraining

Recommended every 3-6 months or after 50+ new recordings:

```bash
# Re-analyze entire archive
python3 analyze_archive.py --output presenter_labels_latest.json

# Re-build with fresh samples (more recent recordings preferred)
python3 build_voiceprint_database.py presenter_labels_latest.json \
    --max-samples 15 \
    --output /mnt/rack-shipping/voiceprints/database.json
```

### Quality Monitoring

Check validation stats after building:

- **Within-speaker similarity:** Should be > 0.70 (ideally > 0.80)
- **Between-speaker similarity:** Should be < 0.50 (ideally < 0.40)
- **Confusing pairs:** Note pairs with similarity > 0.55 for potential issues

## Troubleshooting

### Voiceprint Fallback Not Working

**Check config:**
```bash
grep "USE_VOICEPRINT_FALLBACK" /home/pi/kiwi_recorder.py
# Should be True
```

**Check database exists:**
```bash
ls -lh /mnt/rack-shipping/voiceprints/database.json
# Should show ~45 KB file
```

**Check Rack connectivity:**
```bash
ssh root@192.168.4.64 "python3 /usr/local/bin/speaker_recognition.py --help"
```

### Low Accuracy

**Causes:**
- Insufficient training samples (need at least 5-10 per presenter)
- Poor quality recordings (noise, interference)
- Similar-sounding voices (check validation stats)

**Solutions:**
- Re-train with more/better samples
- Adjust confidence thresholds
- Review confusing presenter pairs

### Database Out of Date

**Symptoms:**
- New presenters not recognized
- Lower accuracy on recent recordings

**Solution:**
```bash
# Re-analyze and re-train
python3 analyze_archive.py --year 2025 --output labels_2025.json
python3 build_voiceprint_database.py labels_2025.json
```

## Technical Details

### Speaker Embeddings

- **Model:** pyannote/embedding (ResNet-based)
- **Dimension:** 512 floats (2 KB per embedding)
- **Input:** Any audio file (WAV, MP3)
- **Output:** Fixed-size vector representing voice characteristics

### Similarity Metric

- **Method:** Cosine similarity between normalized embeddings
- **Range:** 0.0 (completely different) to 1.0 (identical)
- **Typical values:**
  - Same speaker: 0.80-0.95
  - Different speakers: 0.20-0.50
  - Similar voices: 0.50-0.70

### Database Format

JSON file mapping presenter names to lists of embeddings:

```json
{
  "John Hammond": [
    [0.123, 0.456, 0.789, ...],  // embedding 1 (512 floats)
    [0.234, 0.567, 0.890, ...]   // embedding 2 (512 floats)
  ],
  "Kelsey Bennett": [...]
}
```

## Future Enhancements

### Potential Improvements

1. **Dual Verification:** Cross-check name extraction against voiceprint
   - Warn if name says "John" but voice matches "Kelsey"

2. **Continuous Learning:** Auto-add high-confidence matches to database
   - Grow database over time without manual retraining

3. **GPU Acceleration:** Use GPU on Rack for faster embedding extraction
   - Reduces processing time from 3-5s to <1s

4. **Real-time Detection:** Extract voiceprint during recording
   - No extra processing step, results available immediately

## References

- **pyannote.audio:** https://github.com/pyannote/pyannote-audio
- **Speaker Recognition:** https://en.wikipedia.org/wiki/Speaker_recognition
- **Cosine Similarity:** https://en.wikipedia.org/wiki/Cosine_similarity

---

**Last Updated:** 2025-12-18
**System Version:** 1.0
**Contact:** See `/home/pi/Documents/claude-shared-knowledge/` for system info
