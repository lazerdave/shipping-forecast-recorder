# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Shipping Forecast Recorder - Specialized automated recorder for BBC Shipping Forecast at 198 kHz longwave. Uses sonic fingerprinting to detect and cut before the national anthem, fetches Met Office forecasts, and generates podcast feeds. Forked from Frequency Harvester for Shipping Forecast-specific features.

## Recent Changes

### 2025-12-15: Automatic Presenter Detection

**What Changed:**
- Added automatic detection of which BBC Radio 4 announcer read each Shipping Forecast
- Uses Whisper speech-to-text (offloaded to Rack) on the final 45 seconds before anthem
- Extracts presenter name from sign-off ("This is [Name]", "I'm [Name]", etc.)
- Validates against database of 22 known BBC Radio 4 announcers
- Optional LLM validation for uncertain matches (requires ANTHROPIC_API_KEY)

**New Components:**
- `presenters.json` - Database of known BBC Radio 4 announcers with name variations
- `test_presenter_extraction.py` - Test suite for name extraction patterns
- `/usr/local/bin/transcribe_audio.py` on Rack - Whisper transcription service
- `detect_presenter()`, `validate_presenter_with_llm()` functions in kiwi_recorder.py
- `notify_presenter_status()` - MQTT notification for presenter detection

**Configuration:**
```python
Config.DETECT_PRESENTER = True  # Enable/disable
Config.LLM_VALIDATE_PRESENTER = True  # Use LLM for uncertain matches
Config.UNKNOWN_PRESENTER_LABEL = "Unknown Announcer"  # Fallback label
```

**Impact:**
- Presenter name appears in podcast feed titles: "Shipping Forecast – AM 00:47 UTC (John Hammond)"
- Presenter included in Internet Archive metadata (title, description, contributor)
- Sidecar .txt files include PRESENTER section with confidence scores
- MQTT notifications include presenter info and `needs_review` flag for unknowns

**Graceful Degradation:**
- If Whisper fails: presenter detection skipped, recording continues
- If name unknown: uses "Unknown Announcer", flags for manual review via MQTT
- If LLM unavailable: falls back to database matching only
- Never blocks the feed from going out

### 2025-11-19: MP3 Conversion & HTTP Range Request Fix

**What Changed:**
- Converted all audio files from WAV to MP3 format (64 kbps bitrate)
- Replaced Python's http.server with nginx for HTTP Range request support
- Updated feed generation to prefer MP3 files
- Automatic MP3 conversion after each recording

**Why:**
- WAV files don't play in most podcast apps (especially iOS)
- Python's http.server doesn't support HTTP Range requests (required for streaming)
- MP3 files are 3x smaller and universally supported

**New Components:**
- `/etc/nginx/sites-available/shipping-forecast` - nginx configuration with Range support
- `convert_to_mp3()` function in kiwi_recorder.py (lines 493-532)
- Updated `list_audio_files()` to prefer MP3 over WAV (lines 1025-1072)

**Impact:**
- Episodes now play correctly in all podcast apps
- File sizes reduced from ~19 MB to ~5.5 MB per episode
- Proper streaming support with seek/resume functionality
- nginx serves files instead of Python's http.server

### 2025-11-19: Public Podcast Feed via Tailscale Funnel

**What Changed:**
- Set up systemd services for automatic HTTP server and Tailscale funnel
- Public podcast feed now available at: https://zigbee.minskin-manta.ts.net/feed.xml
- Renamed podcast to "Shipping Forecast Tailscale"
- Added "The Great Wave off Kanagawa" artwork
- Services auto-start on boot

**New Components:**
- `/etc/systemd/system/shipping-forecast-funnel.service` - Tailscale funnel exposing port 8080
- `NOTES.md` - Operational documentation for the public feed setup

**Impact:**
- Podcast is now publicly accessible on the internet
- No manual intervention needed; services start automatically on boot
- Feed updates automatically after each recording

**Related Documentation:**
- See `NOTES.md` for detailed setup, management commands, and troubleshooting

## Environment

- Platform: Raspberry Pi (ARM64 architecture)
- OS: Linux 6.12.25+rpt-rpi-v8
- Python: 3.11.2
- Base directory: /home/pi/projects/shipping-forecast-recorder
- Production script: /home/pi/kiwi_recorder.py
- Anthem template: anthem_template.wav (10s sonic fingerprint)

## Project Structure

The project has been consolidated into a single Python script with multiple commands:

- **kiwi_recorder.py** - Main consolidated script with anthem detection
- **anthem_template.wav** - 10-second sonic fingerprint for cross-correlation detection
- **test_anthem_detection.py** - Testing utility for anthem detection
- **make_feed.py** - RSS feed generator helper
- **requirements.txt** - Python dependencies (requests>=2.28.0, scipy, numpy)

## Commands

The system operates via subcommands:

```bash
python3 /home/pi/kiwi_recorder.py scan       # Scan KiwiSDR network for best receivers
python3 /home/pi/kiwi_recorder.py record     # Record from best receiver + rebuild feed
python3 /home/pi/kiwi_recorder.py feed       # Rebuild RSS/podcast feed only
python3 /home/pi/kiwi_recorder.py setup      # Configure cron jobs for automation
```

## Architecture

### Key Components

1. **Scanning System** (cmd_scan)
   - Discovers KiwiSDR receivers via public listings
   - Parallel scanning with 15 concurrent workers (10x faster than sequential)
   - Filters for UK/nearby receivers
   - Two-phase: quick screen (8s) + deep probe (20s) on top 20
   - Saves results to /home/pi/kiwi_scans/

2. **Recording System** (cmd_record)
   - Selects best receiver from latest scan
   - Fresh RSSI check before recording
   - Records 13-minute broadcasts
   - Generates sidecar .txt files with metadata
   - Updates latest.wav symlink
   - Automatically rebuilds RSS feed

3. **Feed Generation** (cmd_feed)
   - Scans /home/pi/share/198k/ for audio files
   - Generates iTunes-compatible podcast RSS
   - Includes metadata from filenames and sidecar files
   - Limits to 50 most recent items

4. **Cron Setup** (cmd_setup)
   - Handles timezone conversion (London → local)
   - Manages automated block in crontab
   - Schedules: scan at 00:42, record at 00:47 London time (single daily recording)
   - Automatic log rotation

5. **Anthem Detection** (detect_anthem_start)
   - Uses cross-correlation with anthem_template.wav
   - Scans from 10 minutes onwards in recordings
   - Finds exact moment of national anthem (typically 12:03)
   - Much more accurate than silence detection (no false positives from forecast pauses)

6. **Archiving System** (automatic after recording)
   - Backs up WAV and MP3 to Rack at `/mnt/rack-shipping/YYYY/MM/`
   - Uploads MP3 to Internet Archive with metadata
   - Sends MQTT notifications to `shipping-forecast/status` topic
   - Manual catch-up utility: `sync_archive.py`

### Configuration

All settings centralized in `Config` class at top of kiwi_recorder.py:
- Paths: /home/pi/kiwiclient/, /home/pi/share/198k/, /home/pi/kiwi_scans/
- Frequency: 198 kHz AM
- Duration: 13 minutes
- Timeouts: connect=7s, discovery=8s, recording margin=60s
- Parallel workers: 15
- RSSI floor: -65.0 dBFS
- MQTT broker: 192.168.4.64:1883 (topic: `shipping-forecast/status`)
- Rack backup: /mnt/rack-shipping

**Important:** Always use local IPs (e.g., `192.168.4.64`), not hostnames (e.g., `rack`) in configs. Hostname resolution fails in cron/service contexts.

### Key Improvements Over Original

1. **Performance**: 10x faster scanning via parallelization (13 min → 1-2 min)
2. **Reliability**: Proper timeouts, error handling, atomic operations
3. **Maintainability**: Single file, centralized config, shared utilities
4. **Code Quality**: Type hints, proper logging, fixed deprecated APIs

## Dependencies

System packages (already installed):
- python3-requests (2.28.1)

Python stdlib (no install needed):
- argparse, concurrent.futures, datetime, email.utils, html, json
- logging, pathlib, re, statistics, subprocess, urllib.parse, zoneinfo

## Directory Structure

```
/home/pi/
├── kiwi_recorder.py          # Production script
├── requirements.txt          # Dependency list
├── kiwiclient/               # KiwiSDR client (external dependency)
│   └── kiwirecorder.py
├── share/198k/               # Output directory
│   ├── *.wav                 # Audio recordings
│   ├── *.txt                 # Sidecar metadata files
│   ├── feed.xml              # RSS/podcast feed
│   ├── latest.wav            # Symlink to most recent
│   └── artwork.jpg           # Optional podcast artwork
├── kiwi_scans/               # Scan results
│   ├── scan_198_*.json       # Historical scans
│   └── latest_scan_198.json  # Pointer to latest
├── old_scripts/              # Backup of original scripts
└── Shipping_Forecast_SDR_Recordings.log  # Main log file
```

## Common Tasks

### Manual Operations

```bash
# Test feed generation
python3 /home/pi/kiwi_recorder.py feed

# Run a scan manually
python3 /home/pi/kiwi_recorder.py scan

# Record manually
python3 /home/pi/kiwi_recorder.py record

# Set up automated cron jobs
python3 /home/pi/kiwi_recorder.py setup
```

### Modifying Configuration

Edit the `Config` class in /home/pi/kiwi_recorder.py:
- Change paths
- Adjust scan workers (increase for faster scanning, decrease for less load)
- Modify timeouts
- Update receiver seeds

### Debugging

Check logs:
```bash
tail -f /home/pi/Shipping_Forecast_SDR_Recordings.log
```

Check cron jobs:
```bash
crontab -l
```

View latest scan results:
```bash
cat /home/pi/kiwi_scans/latest_scan_198.json | jq '.top20[] | {host, port, avg}'
```

## Notes

- The script requires kiwiclient to be installed at /home/pi/kiwiclient/
- Network access required for scanning and recording
- Timezone handling converts London times to local automatically
- Scans are parallelized for efficiency; adjust SCAN_WORKERS if needed
- Feed generation happens automatically after recording
- Always use local IPs, not hostnames, in configs (hostname resolution unreliable in cron/services)