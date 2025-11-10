# Shipping Forecast Recorder

> Automated BBC Shipping Forecast recorder for 198 kHz longwave with intelligent anthem detection

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

Shipping Forecast Recorder is a specialized tool for automatically recording the BBC Shipping Forecast from 198 kHz longwave via the global [KiwiSDR network](http://kiwisdr.com/). It intelligently processes recordings to cut before the national anthem using sonic fingerprinting, fetches official forecasts from the Met Office, and generates a podcast feed.

**This is a specialized fork of [Frequency Harvester](https://github.com/lazerdave/frequencyharvester)** - while Frequency Harvester is designed as a general-purpose KiwiSDR recorder for any frequency, this project is specifically tailored for the BBC Shipping Forecast broadcast structure.

### Key Features

- **🎵 Sonic Fingerprint Detection** - Uses cross-correlation with anthem template to accurately detect and cut before "God Save the King"
- **⚡ 10x Faster Scanning** - Parallel processing finds best UK receivers in 1-2 minutes
- **📡 Smart Receiver Selection** - Automatically picks the best 198 kHz receiver based on signal strength
- **🌊 Met Office Integration** - Fetches official shipping forecast text and includes it in recording metadata
- **🎙️ Automated Processing** - Hands-free recording with fade-out before anthem
- **📻 Single Daily Recording** - Records at 00:47 London time (00:48 UTC broadcast)
- **🔄 RSS/Podcast Feed** - Automatic generation with iTunes-compatible metadata

## What Makes This Different

Unlike general KiwiSDR recorders, this project includes:

- **Hardcoded anthem sonic fingerprint** (`anthem_template.wav`) for accurate cut detection
- **Shipping Forecast-specific scheduling** (single daily recording at midnight)
- **Met Office forecast fetching** with HTML parsing
- **Broadcast structure awareness** (knows when/where anthem occurs)
- **Cross-correlation detection** replacing generic silence detection

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/lazerdave/shipping-forecast-recorder.git
cd shipping-forecast-recorder

# Run the automated installer
sudo bash install_kiwi_recorder.sh
```

The installer handles:
- System dependencies (sox, numpy, scipy, requests)
- KiwiSDR client software
- Directory structure
- Anthem template deployment
- Python dependencies
- Verification tests

### Basic Usage

```bash
# Find the best receivers (1-2 minutes)
python3 kiwi_recorder.py scan

# Record the shipping forecast (auto-selects best receiver, processes, updates feed)
python3 kiwi_recorder.py record

# Generate/update RSS podcast feed
python3 kiwi_recorder.py feed

# Set up automated cron job for daily recording
python3 kiwi_recorder.py setup
```

### Automated Operation

After running `setup`, the system will:
- **17:42 local** (00:42 London): Scan for best receivers
- **17:47 local** (00:47 London): Record shipping forecast, process, and update feed

(Times shown are for MST timezone, automatically adjusted to your local timezone)

## How Anthem Detection Works

The recorder uses **cross-correlation** with a pre-recorded anthem template to find the exact moment the national anthem begins:

1. Template (`anthem_template.wav`): 10-second sample of the drumroll and opening notes
2. Scanning: Searches recordings from 10 minutes onwards
3. Matching: Finds the best correlation match (typically 12:03 into the recording)
4. Processing: Cuts recording at the detected point with a 2-second fade-out

This is far more accurate than silence detection, which was prone to false positives from pauses in the forecast.

## Architecture

**Single-file design** - All functionality in one Python script with four subcommands:

- `scan` - Parallel network scanning with signal strength measurement
- `record` - Recording with anthem detection, processing, and feed updates
- `feed` - RSS/podcast feed generation
- `setup` - Cron automation configuration

## Visual Output

The scanner provides professional signal analysis:

```
════════════════════════════════════════════════════════════════════════════════
  KiwiSDR Network Scanner - Finding Best 198 kHz Receivers
════════════════════════════════════════════════════════════════════════════════
[  1/100] receiver.name:8073        ✓ ████████░░░░  -45.2dB (GOOD) (n=5)
[  2/100] another.host:8073         ✗ TOO WEAK - ██░░░░░░░░░░  -72.1dB (WEAK)
...

┌─ TOP 5 RECEIVERS ─────────────────────────────────────────────────────────────
│ 1. best.receiver:8073              █████████░░░  -42.3dB (VERY GOOD)
│ 2. second.best:8073                ████████░░░░  -45.1dB (GOOD)
└───────────────────────────────────────────────────────────────────────────────
```

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Scan (parallel) | 1-2 min | ~100 UK/nearby receivers, 15 workers |
| Recording | 15 min | Full broadcast + anthem + handoff |
| Processing | <1 sec | Anthem detection + fade-out |
| Feed rebuild | <1 sec | Up to 50 recordings |

## Requirements

- **Python:** 3.9 or higher
- **Platform:** Linux (tested on Raspberry Pi, Debian, Ubuntu, Fedora)
- **Architecture:** x86_64, ARM64, ARMv7
- **Network:** Internet connection for KiwiSDR access and Met Office fetching
- **Storage:** ~5GB recommended for recordings

## Files Included

- `kiwi_recorder.py` - Main recorder script
- `anthem_template.wav` - 10-second sonic fingerprint of the national anthem
- `test_anthem_detection.py` - Testing utility for anthem detection
- `make_feed.py` - RSS feed generator helper
- `requirements.txt` - Python dependencies
- `install_kiwi_recorder.sh` - Automated installer

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Architecture, configuration, and usage guide
- **[INSTALL.md](INSTALL.md)** - Detailed installation and troubleshooting
- **[DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)** - Complete deployment record

## Code Quality

- ✅ Type hints throughout
- ✅ Comprehensive error handling
- ✅ Modern Python practices (no deprecated APIs)
- ✅ PEP 8 compliant
- ✅ Atomic file operations
- ✅ Proper logging framework

## Related Projects

- **[Frequency Harvester](https://github.com/lazerdave/frequencyharvester)** - General-purpose KiwiSDR recorder for any frequency/broadcast

## License

MIT License - See [LICENSE](LICENSE) for details

## Acknowledgments

- Built with [Claude Code](https://claude.com/claude-code)
- Uses [KiwiSDR client](https://github.com/jks-prv/kiwiclient) by John Seamons
- Inspired by the global KiwiSDR community
- Forked from [Frequency Harvester](https://github.com/lazerdave/frequencyharvester)

---

**🤖 Generated with Claude Code**
