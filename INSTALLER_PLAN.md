# Shipping Forecast Tailscale Podcast - Interactive Installer Plan

## Executive Summary

This plan outlines the design for a world-class interactive installer for the Shipping Forecast Tailscale podcast system. The installer will provide a polished, user-friendly experience with Tailscale authentication, customizable paths, comprehensive dependency management, and a refined visual interface.

---

## Design Philosophy

### Core Principles
1. **Zero Assumptions** - Check everything, install only what's missing
2. **User Empowerment** - Sensible defaults, easy customization
3. **Visual Excellence** - Professional UI with progress indicators, color coding, and clear feedback
4. **Bulletproof Execution** - Comprehensive error handling, rollback capability
5. **One-Click to Production** - From fresh system to running podcast in minutes

### User Experience Goals
- **Welcoming**: Professional branding, clear explanations
- **Transparent**: Show what's happening at each step
- **Flexible**: Allow customization without overwhelming
- **Informative**: Educational explanations for each component
- **Reassuring**: Validation, progress tracking, success confirmation

---

## Visual Design System

### Color Palette
```bash
# Semantic colors for terminal output
BRAND_BLUE='\033[38;5;33m'     # Primary brand (titles, headers)
ACCENT_CYAN='\033[38;5;51m'    # Secondary accent (highlights)
SUCCESS_GREEN='\033[38;5;46m'  # Success states, checkmarks
WARNING_YELLOW='\033[38;5;226m' # Warnings, important notes
ERROR_RED='\033[38;5;196m'      # Errors, failures
MUTED_GRAY='\033[38;5;245m'    # Secondary text, comments
BOLD='\033[1m'                  # Emphasis
DIM='\033[2m'                   # De-emphasis
NC='\033[0m'                    # Reset
```

### Visual Components

#### 1. Welcome Screen
```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                   🌊  SHIPPING FORECAST TAILSCALE PODCAST  🌊                 ║
║                                                                              ║
║           Automated BBC Shipping Forecast Recorder & Podcast Feed            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

  Version: 1.0.0
  Platform: Detected automatically
  Required Space: ~5GB for recordings
  Est. Install Time: 5-10 minutes

  This installer will set up a complete automated recording system that:

    • 📡 Discovers the best KiwiSDR receivers automatically
    • 🎵 Records the Shipping Forecast every night at 00:48 UTC
    • ✂️  Detects and removes the national anthem using AI
    • 🎙️  Converts to MP3 and generates a podcast feed
    • 🌐 Publishes via Tailscale Funnel for worldwide access

  ──────────────────────────────────────────────────────────────────────────────

  Press ENTER to begin installation, or Ctrl+C to exit
```

#### 2. Progress Indicators

**Step Headers:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 1/8: System Prerequisites                                   [●○○○○○○○] ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Task Progress:**
```
  ✓ Checking Python version... Python 3.11.2 (OK)
  ✓ Checking disk space... 23.4 GB available (OK)
  ○ Checking git installation... Installing...
  ⊙ Installing system packages... [████████░░░░░░░░] 55%
```

**Status Symbols:**
- `✓` Success (green)
- `✗` Failure (red)
- `○` Pending (gray)
- `⊙` In progress (cyan, animated)
- `⚠` Warning (yellow)
- `ℹ` Information (blue)

#### 3. Configuration Screens

**Path Configuration:**
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  PATH CONFIGURATION                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

  Configure installation paths (press ENTER to accept default):

  ┌────────────────────────────────────────────────────────────────────────────┐
  │ Install Directory:                                                         │
  │ > /home/pi/shipping-forecast                                                │
  │   (Application files, scripts, and configuration)                          │
  └────────────────────────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────────────────────────┐
  │ Recording Output Directory:                                                │
  │ > /home/pi/share/198k                                                       │
  │   (Audio files, feed, and artwork - needs ~5GB)                            │
  └────────────────────────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────────────────────────┐
  │ Scan Results Directory:                                                    │
  │ > /home/pi/kiwi_scans                                                       │
  │   (Receiver scan data and logs)                                            │
  └────────────────────────────────────────────────────────────────────────────┘

  ✓ All paths validated and available
```

**Tailscale Configuration:**
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  TAILSCALE AUTHENTICATION                                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

  Tailscale enables secure, worldwide access to your podcast feed without
  port forwarding or firewall configuration.

  ┌────────────────────────────────────────────────────────────────────────────┐
  │                                                                            │
  │  To authenticate, please visit:                                            │
  │                                                                            │
  │  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
  │  ┃                                                                        ┃  │
  │  ┃   https://login.tailscale.com/a/1234abcd                              ┃  │
  │  ┃                                                                        ┃  │
  │  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
  │                                                                            │
  │  [QR Code displayed here for mobile scanning]                             │
  │                                                                            │
  └────────────────────────────────────────────────────────────────────────────┘

  ⊙ Waiting for authentication... (30s timeout)
```

#### 4. Summary Screen
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  ✓ INSTALLATION COMPLETE                                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

  Your Shipping Forecast podcast is now running!

  ┌─ System Status ────────────────────────────────────────────────────────────┐
  │ ✓ All services running                                                     │
  │ ✓ Tailscale authenticated: zigbee.minskin-manta.ts.net                     │
  │ ✓ Nginx server active on port 8080                                         │
  │ ✓ Cron jobs configured for daily recording at 00:47 London                 │
  └────────────────────────────────────────────────────────────────────────────┘

  ┌─ Your Podcast Feed ────────────────────────────────────────────────────────┐
  │                                                                            │
  │  📻 Feed URL:                                                               │
  │     https://zigbee.minskin-manta.ts.net/feed.xml                            │
  │                                                                            │
  │  📱 Subscribe in your podcast app using the URL above                       │
  │                                                                            │
  └────────────────────────────────────────────────────────────────────────────┘

  ┌─ Useful Commands ──────────────────────────────────────────────────────────┐
  │                                                                            │
  │  Test a scan:       /home/pi/shipping-forecast/kiwi_recorder.py scan       │
  │  Manual recording:  /home/pi/shipping-forecast/kiwi_recorder.py record     │
  │  Rebuild feed:      /home/pi/shipping-forecast/kiwi_recorder.py feed       │
  │  View logs:         tail -f ~/Shipping_Forecast_SDR_Recordings.log         │
  │  Service status:    systemctl status shipping-forecast-funnel              │
  │                                                                            │
  └────────────────────────────────────────────────────────────────────────────┘

  Next recording scheduled for: Tonight at 00:47 London time (17:47 local)

  ──────────────────────────────────────────────────────────────────────────────

  Thank you for using Shipping Forecast Tailscale!
  For support and documentation, visit: /home/pi/shipping-forecast/README.md
```

---

## Installation Architecture

### Stage Overview
```
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   PRE-FLIGHT  │──▶│  SYSTEM DEPS  │──▶│   APP SETUP   │──▶│  SERVICE CFG  │
└───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘
      │                    │                    │                    │
      ▼                    ▼                    ▼                    ▼
  • Platform         • Packages         • KiwiClient       • Nginx
  • Python           • Python libs      • Main script      • Tailscale
  • Disk space       • FFmpeg           • Directories      • Cron
  • Permissions      • Git              • Assets           • Funnel
                                        • Config
```

### Detailed Stages

#### Stage 1: Pre-flight Checks
**Purpose**: Validate environment before any modifications

**Checks:**
1. **Platform Detection**
   - OS: Debian/Ubuntu/Raspbian/Arch/Fedora
   - Architecture: ARM64/ARMv7/x86_64
   - Special case: Raspberry Pi model detection

2. **Python Version**
   - Required: 3.9+
   - Check: `python3 --version`
   - Fallback: Offer to install via package manager

3. **Disk Space**
   - Required: 5GB minimum for recordings
   - Recommended: 10GB+ for long-term operation
   - Show available space in human-readable format

4. **User Permissions**
   - Check if running as root/sudo
   - Detect actual user (`$SUDO_USER` or `whoami`)
   - Validate write permissions to target directories

5. **Network Connectivity**
   - Test internet connection (ping 8.8.8.8)
   - Check DNS resolution
   - Validate access to required URLs:
     - github.com (for kiwiclient)
     - kiwisdr.com (for receiver discovery)
     - login.tailscale.com (for authentication)

**Output Format:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 1/8: Pre-flight Checks                                   [●○○○○○○○] ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  Platform Information:
  ✓ OS: Raspberry Pi OS (Debian Bookworm)
  ✓ Architecture: ARM64 (aarch64)
  ✓ Model: Raspberry Pi 4 Model B Rev 1.4

  System Requirements:
  ✓ Python version: 3.11.2 (meets 3.9+ requirement)
  ✓ Disk space: 23.4 GB available (5GB required)
  ✓ Memory: 3.8 GB total
  ✓ User: pi (sudo available)

  Network Connectivity:
  ✓ Internet connection: Active
  ✓ DNS resolution: Working
  ✓ GitHub access: Reachable
  ✓ KiwiSDR network: Accessible
  ✓ Tailscale services: Available

  ✓ All pre-flight checks passed!
```

#### Stage 2: User Configuration
**Purpose**: Gather user preferences before installation

**Configuration Items:**

1. **Installation Paths**
   ```python
   DEFAULT_PATHS = {
       'install_dir': '/home/{user}/shipping-forecast',
       'output_dir': '/home/{user}/share/198k',
       'scan_dir': '/home/{user}/kiwi_scans',
       'log_file': '/home/{user}/Shipping_Forecast_SDR_Recordings.log'
   }
   ```

   - Show defaults
   - Allow customization
   - Validate paths (writable, sufficient space)
   - Create preview of directory structure

2. **Podcast Metadata**
   - Title: "Shipping Forecast Tailscale" (editable)
   - Author: Auto-detected from hostname
   - Description: Default provided, editable

3. **Recording Schedule**
   - Default: 00:47 London time
   - Alternative options:
     - 05:19 London (morning broadcast)
     - Both broadcasts
     - Custom time
   - Show converted local time

4. **Tailscale Setup**
   - Option 1: Use existing Tailscale installation
   - Option 2: Fresh Tailscale setup
   - Option 3: Skip Tailscale (local-only mode)

**Interactive Flow:**
```
  Would you like to customize installation paths? [y/N]: y

  Install Directory [/home/pi/shipping-forecast]:
  ▶ /home/pi/custom-location

  ✓ Path validated: Writable, 45GB available

  Recording Output [/home/pi/share/198k]: [ENTER]
  ✓ Using default: /home/pi/share/198k
```

#### Stage 3: System Dependencies
**Purpose**: Install required system packages

**Package Lists by Distribution:**

**Debian/Ubuntu/Raspbian:**
```python
DEBIAN_PACKAGES = [
    'git',              # Clone kiwiclient repository
    'python3-pip',      # Python package manager
    'python3-numpy',    # Numerical processing
    'python3-scipy',    # Signal processing (anthem detection)
    'python3-requests', # HTTP client
    'sox',              # Audio manipulation (optional, for legacy support)
    'ffmpeg',           # MP3 conversion
    'nginx',            # HTTP server for feed
    'curl',             # Healthchecks and testing
    'jq'                # JSON parsing (for debugging)
]
```

**Arch Linux:**
```python
ARCH_PACKAGES = [
    'git', 'python-pip', 'python-numpy', 'python-scipy',
    'python-requests', 'sox', 'ffmpeg', 'nginx', 'curl', 'jq'
]
```

**Fedora/RHEL:**
```python
FEDORA_PACKAGES = [
    'git', 'python3-pip', 'python3-numpy', 'python3-scipy',
    'python3-requests', 'sox', 'ffmpeg', 'nginx', 'curl', 'jq'
]
```

**Installation Strategy:**
1. Detect package manager (apt/dnf/pacman/zypper)
2. Check each package individually
3. Install only missing packages
4. Show progress bar for each installation
5. Handle failures gracefully (retry, skip non-critical)

**Output Format:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 2/8: System Dependencies                                 [●●○○○○○○] ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  Installing system packages via apt...

  ✓ git.................. Already installed (2.39.2)
  ⊙ python3-numpy........ Installing [████████████░░░░] 75%
  ○ python3-scipy........ Queued
  ○ python3-requests..... Queued
  ○ ffmpeg............... Queued
  ○ nginx................ Queued
```

#### Stage 4: Python Environment
**Purpose**: Set up Python dependencies

**Dependencies:**
```python
PYTHON_DEPS = [
    'requests>=2.28.0',  # HTTP client
    'numpy',             # Usually from system packages
    'scipy',             # Usually from system packages
]
```

**Installation Options:**
1. **System Packages** (preferred for numpy/scipy)
   - Faster installation
   - Better ARM optimization
   - More reliable on Raspberry Pi

2. **pip** (fallback or when system packages unavailable)
   - Latest versions
   - Virtual environment support option

**Validation:**
```python
# Test imports after installation
import requests
import numpy as np
import scipy
from scipy import signal
```

#### Stage 5: KiwiSDR Client
**Purpose**: Install official KiwiSDR receiver software

**Source:** https://github.com/jks-prv/kiwiclient

**Installation:**
```bash
git clone https://github.com/jks-prv/kiwiclient.git {install_dir}/kiwiclient
chmod +x {install_dir}/kiwiclient/kiwirecorder.py
```

**Verification:**
```bash
python3 {install_dir}/kiwiclient/kiwirecorder.py --help
```

**Output Format:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 3/8: KiwiSDR Client                                      [●●●○○○○○] ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  Installing KiwiSDR client software...

  ⊙ Cloning repository...
  ✓ Repository cloned (3.2 MB)
  ✓ Executable permissions set
  ✓ Client verified and working

  Location: /home/pi/shipping-forecast/kiwiclient/
```

#### Stage 6: Application Setup
**Purpose**: Deploy main application and assets

**Components:**

1. **Main Script** (`kiwi_recorder.py`)
   - Copy from source or download from repo
   - Set executable permissions
   - Validate syntax

2. **Assets**
   - `anthem_template.wav` - 10s sonic fingerprint
   - `artwork.jpg` - Podcast artwork (The Great Wave)
   - `requirements.txt` - Python dependencies list

3. **Directory Structure**
   ```
   {install_dir}/
   ├── kiwi_recorder.py         # Main application
   ├── kiwiclient/              # KiwiSDR client (git repo)
   ├── anthem_template.wav      # Sonic fingerprint
   ├── requirements.txt         # Python deps
   ├── README.md               # Documentation
   ├── INSTALL.md              # Install guide
   └── CLAUDE.md               # System documentation

   {output_dir}/
   ├── anthem_template.wav      # Symlink to main
   ├── artwork.jpg             # Podcast artwork
   ├── feed.xml                # RSS feed (generated)
   ├── *.mp3                   # Recordings (generated)
   ├── *.txt                   # Metadata (generated)
   └── latest.wav              # Symlink (generated)

   {scan_dir}/
   ├── scan_198_*.json         # Scan results (generated)
   └── latest_scan_198.json    # Latest scan pointer (generated)
   ```

4. **Configuration**
   - Update Config class in kiwi_recorder.py with user paths
   - Set BASE_URL to Tailscale hostname
   - Configure FEED_TITLE, FEED_AUTHOR from user input

**Output Format:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 4/8: Application Setup                                   [●●●●○○○○] ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  Deploying application files...

  ✓ Main script installed: kiwi_recorder.py
  ✓ Anthem template deployed: anthem_template.wav (240 KB)
  ✓ Podcast artwork installed: artwork.jpg (127 KB)
  ✓ Documentation copied: README.md, INSTALL.md, CLAUDE.md

  Creating directory structure...

  ✓ Install directory: /home/pi/shipping-forecast/
  ✓ Output directory: /home/pi/share/198k/
  ✓ Scan directory: /home/pi/kiwi_scans/
  ✓ Log file: /home/pi/Shipping_Forecast_SDR_Recordings.log
```

#### Stage 7: Nginx Configuration
**Purpose**: Set up HTTP server for podcast feed

**Configuration File:** `/etc/nginx/sites-available/shipping-forecast`

```nginx
server {
    listen 8080;
    server_name _;

    root {output_dir};

    # Enable directory listing
    autoindex on;
    autoindex_exact_size off;
    autoindex_localtime on;

    # Enable Range requests (critical for podcast streaming)
    max_ranges 1;

    # Proper MIME types
    types {
        audio/mpeg mp3;
        audio/wav wav;
        application/rss+xml xml;
        image/jpeg jpg jpeg;
    }

    # Cache control
    location ~* \.(mp3|wav)$ {
        add_header Cache-Control "public, max-age=3600";
        add_header Accept-Ranges bytes;
    }

    location ~* \.(xml)$ {
        add_header Cache-Control "public, max-age=300";
    }

    # Logging
    access_log /var/log/nginx/shipping-forecast-access.log;
    error_log /var/log/nginx/shipping-forecast-error.log;
}
```

**Actions:**
1. Write config file
2. Create symlink: `sites-enabled/shipping-forecast`
3. Test config: `nginx -t`
4. Reload nginx: `systemctl reload nginx`
5. Verify server responds on port 8080

**Output Format:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 5/8: Web Server Setup                                    [●●●●●○○○] ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  Configuring nginx...

  ✓ Configuration written: /etc/nginx/sites-available/shipping-forecast
  ✓ Site enabled: /etc/nginx/sites-enabled/shipping-forecast
  ✓ Configuration test: PASSED
  ✓ Nginx reloaded successfully
  ✓ Server responding on http://localhost:8080
```

#### Stage 8: Tailscale Setup
**Purpose**: Authenticate and configure Tailscale for public access

**Substeps:**

1. **Install Tailscale** (if not present)
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   ```

2. **Authentication**
   - Generate auth URL: `tailscale up --auth-key=... --hostname=...`
   - Display QR code for mobile
   - Wait for authentication (with timeout)
   - Verify connection

3. **Funnel Setup**
   - Enable Tailscale Funnel on port 8080
   - Create systemd service for persistence

**Systemd Service:** `/etc/systemd/system/shipping-forecast-funnel.service`

```ini
[Unit]
Description=Shipping Forecast Tailscale Funnel
After=network.target tailscaled.service nginx.service
Requires=tailscaled.service nginx.service

[Service]
Type=simple
ExecStart=/usr/bin/tailscale funnel 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

4. **Service Management**
   ```bash
   systemctl daemon-reload
   systemctl enable shipping-forecast-funnel
   systemctl start shipping-forecast-funnel
   ```

5. **Verification**
   - Get Tailscale hostname
   - Test HTTPS access to feed
   - Validate SSL certificate

**Interactive Flow:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 6/8: Tailscale Configuration                             [●●●●●●○○] ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  Setting up Tailscale for public access...

  ✓ Tailscale installed: Version 1.56.1

  Please authenticate your device:

  ┌────────────────────────────────────────────────────────────────────────────┐
  │                                                                            │
  │  Visit: https://login.tailscale.com/a/abc123def456                         │
  │                                                                            │
  │  Or scan this QR code:                                                     │
  │                                                                            │
  │  ████ ▄▄▄▄▄ █▀█ █▄█▀▀▀▄█ ▄▄▄▄▄ ████                                         │
  │  ████ █   █ █▀▀▀█ ▀ ▄▀▀█ █   █ ████                                         │
  │  ████ █▄▄▄█ █▀ █▀▀██▄ ▄█ █▄▄▄█ ████                                         │
  │  ████▄▄▄▄▄▄▄█▄▀ █ ▀ █ █ ▄▄▄▄▄▄▄████                                         │
  │                                                                            │
  └────────────────────────────────────────────────────────────────────────────┘

  ⊙ Waiting for authentication... (timeout in 60s)

  ✓ Authentication successful!
  ✓ Hostname assigned: zigbee.minskin-manta.ts.net
  ✓ Funnel enabled on port 8080
  ✓ Public URL: https://zigbee.minskin-manta.ts.net
```

#### Stage 9: Cron Automation
**Purpose**: Schedule automated recordings

**Cron Jobs:**
```cron
# Managed by Shipping Forecast Installer - DO NOT EDIT MANUALLY
# >>> SHIPPING-FORECAST-AUTO (managed) >>>

# Recompute schedule daily at 00:02 local
2 0 * * * /usr/bin/python3 {install_dir}/kiwi_recorder.py setup >> {log_file} 2>&1

# Scan 5 min before 00:47 London time
42 0 * * * /usr/bin/python3 {install_dir}/kiwi_recorder.py scan >> {log_file} 2>&1

# Record at 00:47 London time (00:48 UTC broadcast)
47 0 * * * /usr/bin/python3 {install_dir}/kiwi_recorder.py record >> {log_file} 2>&1

# Weekly log rotation (Sunday 00:20 local)
20 0 * * 0 /bin/bash -c 'tail -n 20000 "{log_file}" > "{log_file}.tmp" && mv "{log_file}.tmp" "{log_file}"'

# <<< SHIPPING-FORECAST-AUTO (managed) <<<
```

**Actions:**
1. Convert London time to local timezone
2. Generate cron expressions
3. Back up existing crontab
4. Install new crontab with managed block
5. Verify crontab installed

**Output Format:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 7/8: Automation Setup                                    [●●●●●●●○] ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  Configuring automated recording schedule...

  ✓ Timezone detected: America/Denver (MST)
  ✓ Converting London time to local...

  Schedule Summary:
  • Scan:   00:42 London → 17:42 MST (5 min before recording)
  • Record: 00:47 London → 17:47 MST (daily)

  ✓ Existing crontab backed up: /home/pi/.crontab.backup
  ✓ Cron jobs installed
  ✓ Schedule verified

  Next recording: Tonight at 17:47 MST (00:47 London)
```

#### Stage 10: Validation & Testing
**Purpose**: Verify complete installation

**Tests:**

1. **Component Tests**
   ```bash
   # Test Python script
   python3 {install_dir}/kiwi_recorder.py --help

   # Test KiwiSDR client
   python3 {install_dir}/kiwiclient/kiwirecorder.py --help

   # Test nginx
   curl -I http://localhost:8080/

   # Test Tailscale
   curl -I https://{hostname}.ts.net/
   ```

2. **Quick Scan Test**
   ```bash
   # Run a short scan (5 receivers, 3 seconds each)
   python3 {install_dir}/kiwi_recorder.py scan --quick
   ```

3. **Feed Generation Test**
   ```bash
   python3 {install_dir}/kiwi_recorder.py feed
   ```

4. **Service Status**
   ```bash
   systemctl status nginx
   systemctl status shipping-forecast-funnel
   tailscale status
   ```

5. **File Verification**
   - All paths exist
   - Permissions correct
   - Anthem template present
   - Artwork present

**Output Format:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 8/8: Validation & Testing                                [●●●●●●●●] ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  Running installation tests...

  Component Tests:
  ✓ Python script: Executable and working
  ✓ KiwiSDR client: Version 1.0, operational
  ✓ Nginx server: Running on port 8080
  ✓ Tailscale Funnel: Public URL accessible

  Functionality Tests:
  ✓ Quick scan: Found 5 receivers in 15s
  ✓ Feed generation: feed.xml created successfully
  ✓ Cron schedule: Jobs installed and active

  File Structure:
  ✓ All directories created
  ✓ Assets deployed correctly
  ✓ Permissions verified
  ✓ Symlinks functional

  Service Status:
  ✓ nginx.service: active (running)
  ✓ shipping-forecast-funnel.service: active (running)
  ✓ tailscaled.service: active (running)

  ✓ All validation tests passed!
```

---

## Error Handling & Recovery

### Error Categories

1. **Recoverable Errors**
   - Missing package: Retry installation
   - Network timeout: Retry with backoff
   - Permission denied: Suggest sudo

2. **Skippable Errors**
   - Optional package unavailable: Continue without
   - Tailscale auth timeout: Offer manual setup
   - Artwork download failed: Use placeholder

3. **Fatal Errors**
   - Python version too old: Exit with instructions
   - No disk space: Exit, cannot continue
   - Cannot write to install directory: Exit

### Rollback Strategy

**Rollback Scenarios:**
- User cancels during installation
- Fatal error encountered
- Validation tests fail

**Rollback Actions:**
1. Stop and remove systemd services
2. Remove nginx configuration
3. Uninstall packages (if installed by us)
4. Remove created directories
5. Restore crontab backup
6. Log all rollback actions

**Output Format:**
```
⚠ Installation interrupted!

Rolling back changes...

✓ Stopped services: nginx, shipping-forecast-funnel
✓ Removed nginx configuration
✓ Removed created directories
✓ Restored original crontab
✓ Cleaned up partial installation

System restored to pre-installation state.
```

---

## Advanced Features

### 1. Silent/Unattended Mode

**Usage:**
```bash
./install.sh --silent --config=config.json
```

**config.json:**
```json
{
  "paths": {
    "install_dir": "/opt/shipping-forecast",
    "output_dir": "/var/podcast/shipping",
    "scan_dir": "/var/cache/kiwi-scans"
  },
  "podcast": {
    "title": "Custom Podcast Name",
    "author": "Custom Author",
    "schedule": ["00:47"]
  },
  "tailscale": {
    "skip": false,
    "auth_key": "tskey-auth-..."
  }
}
```

### 2. Update Mode

**Usage:**
```bash
./install.sh --update
```

**Actions:**
- Detect existing installation
- Backup current configuration
- Update application files only
- Preserve user data and recordings
- Restart services

### 3. Dry-Run Mode

**Usage:**
```bash
./install.sh --dry-run
```

**Actions:**
- Run all checks
- Show what would be installed
- Don't make any changes
- Output installation plan

### 4. Diagnostics Mode

**Usage:**
```bash
./install.sh --diagnose
```

**Actions:**
- Check all components
- Test connectivity
- Verify configuration
- Generate diagnostic report

---

## Implementation Details

### File Structure

```
shipping-forecast-recorder/
├── install.sh                  # Main installer script (THIS FILE)
├── lib/
│   ├── colors.sh              # Color definitions and output helpers
│   ├── ui.sh                  # UI components (progress bars, boxes)
│   ├── checks.sh              # Pre-flight and validation functions
│   ├── packages.sh            # Package management (multi-distro)
│   ├── tailscale.sh           # Tailscale setup and authentication
│   ├── config.sh              # Configuration management
│   └── rollback.sh            # Rollback and cleanup functions
├── assets/
│   ├── anthem_template.wav    # Sonic fingerprint
│   ├── artwork.jpg            # Podcast artwork
│   └── banner.txt             # ASCII art banner
├── templates/
│   ├── nginx.conf.template    # Nginx configuration
│   ├── funnel.service.template # Systemd service
│   └── config.py.template     # Application config
├── kiwi_recorder.py           # Main application
├── requirements.txt           # Python dependencies
├── README.md
├── INSTALL.md
└── CLAUDE.md
```

### Technology Stack

**Core:**
- Bash 4.3+ for installer
- Python 3.9+ for application

**Libraries Used:**
- `qrencode` for QR code generation (optional)
- `dialog` or `whiptail` for TUI (optional)
- `tput` for terminal control

**Testing:**
- shellcheck for bash linting
- Unit tests for critical functions
- Integration tests for full flow

### Platform Compatibility

**Tested Platforms:**
- Raspberry Pi OS (Debian Bookworm)
- Ubuntu 22.04 LTS
- Debian 12 (Bookworm)
- Arch Linux
- Fedora 38+

**Architecture Support:**
- ARM64 (aarch64)
- ARMv7 (32-bit)
- x86_64

---

## Security Considerations

### Permissions
- Run as non-root user where possible
- Use `sudo` only for system operations:
  - Package installation
  - Systemd service management
  - Nginx configuration

### Network
- HTTPS only for Tailscale Funnel
- No exposed ports except via Tailscale
- Certificate management handled by Tailscale

### Secrets
- No hardcoded credentials
- Tailscale auth keys ephemeral
- Log files readable only by user

---

## Success Metrics

**Installation Success:**
- [ ] All pre-flight checks pass
- [ ] All dependencies installed
- [ ] Application deployed and configured
- [ ] Services running
- [ ] Tailscale authenticated
- [ ] First scan completes successfully
- [ ] Feed accessible via HTTPS
- [ ] Cron jobs scheduled

**User Experience:**
- Visual clarity: 10/10
- Error messages: Helpful and actionable
- Time to complete: < 10 minutes
- Success rate: > 95% on supported platforms

---

## Future Enhancements

### Phase 2 Features
1. **Web-based Installer**
   - Browser interface for configuration
   - Real-time progress updates via WebSocket
   - Mobile-friendly UI

2. **Docker Support**
   - Containerized deployment
   - Docker Compose orchestration
   - Volume management

3. **Multi-recording Support**
   - Multiple broadcasts per day
   - Different frequencies
   - Custom schedules per frequency

4. **Analytics Dashboard**
   - Recording success rate
   - Receiver quality over time
   - Listener statistics
   - Feed health metrics

5. **Backup & Restore**
   - Automated backups to cloud storage
   - One-click restore
   - Migration tools

---

## Conclusion

This installer will provide a world-class user experience that transforms a complex, multi-component installation into a guided, foolproof process. The combination of:

- **Professional visual design**
- **Comprehensive error handling**
- **Platform flexibility**
- **Tailscale authentication**
- **Validation and testing**

...ensures that users can go from zero to a fully operational podcast system in minutes, with confidence that everything is configured correctly.

The installer embodies the principle: **"Make the simple easy, and the complex possible."**

---

**End of Plan**
