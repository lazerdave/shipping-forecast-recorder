# KiwiSDR Recorder - Installation Guide

Complete installation instructions for the KiwiSDR automated recording system.

## Quick Start

For a fresh Raspberry Pi installation, simply run:

```bash
cd /home/pi/projects/recorder
sudo ./install_kiwi_recorder.sh
```

The installer will guide you through the process.

## What Gets Installed

### System Components

1. **KiwiSDR Client** (`/home/pi/kiwiclient/`)
   - Cloned from official GitHub repository
   - Includes kiwirecorder.py for radio reception
   - Requires: git, python3-numpy, python3-scipy

2. **System Dependencies**
   - `sox` - Audio file manipulation
   - `libsox-fmt-mp3` - MP3 support for sox
   - `python3-requests` - HTTP client library
   - `python3-numpy` - Numerical processing
   - `python3-scipy` - Scientific computing

3. **Recorder Script** (`/home/pi/kiwi_recorder.py`)
   - Main consolidated recording script
   - All-in-one: scan, record, feed, setup commands

### Directory Structure

```
/home/pi/
├── kiwi_recorder.py          # Main script
├── requirements.txt          # Python dependencies
├── kiwiclient/               # KiwiSDR client (git clone)
│   └── kiwirecorder.py
├── share/198k/               # Output directory for recordings
│   ├── *.wav                 # Audio files
│   ├── *.txt                 # Metadata sidecar files
│   ├── feed.xml              # Podcast RSS feed
│   └── latest.wav            # Symlink to most recent
├── kiwi_scans/               # Scan results
│   ├── scan_198_*.json       # Historical scan data
│   └── latest_scan_198.json  # Pointer to latest scan
└── Shipping_Forecast_SDR_Recordings.log  # Main log file
```

## Installation Options

### Interactive Mode (Default)

Prompts for confirmation at each step:

```bash
sudo ./install_kiwi_recorder.sh
```

### Automatic Mode

No prompts, installs everything automatically:

```bash
sudo ./install_kiwi_recorder.sh --auto
```

## Requirements

### Hardware

- Raspberry Pi (any model with network connectivity)
- At least 5GB free disk space for recordings
- Internet connection

### Software

- Raspberry Pi OS (Debian Bookworm or later)
- Python 3.9 or higher
- Root access (sudo)

## Installation Steps (Manual)

If you prefer to install components individually:

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y git python3-pip python3-numpy python3-scipy \
                        python3-requests sox libsox-fmt-mp3
```

### 2. Install KiwiSDR Client

```bash
cd /home/pi
git clone https://github.com/jks-prv/kiwiclient.git
chmod +x kiwiclient/kiwirecorder.py
```

### 3. Create Directories

```bash
mkdir -p /home/pi/share/198k
mkdir -p /home/pi/kiwi_scans
touch /home/pi/Shipping_Forecast_SDR_Recordings.log
```

### 4. Install Recorder Script

```bash
cd /home/pi/projects/recorder
sudo cp kiwi_recorder.py /home/pi/
sudo chmod +x /home/pi/kiwi_recorder.py
sudo cp requirements.txt /home/pi/
```

### 5. Verify Installation

```bash
python3 /home/pi/kiwi_recorder.py --help
python3 /home/pi/kiwiclient/kiwirecorder.py --help
```

## Post-Installation

### Testing

1. **Test feed generation:**
   ```bash
   python3 /home/pi/kiwi_recorder.py feed
   ```

2. **Run a scan** (1-2 minutes):
   ```bash
   python3 /home/pi/kiwi_recorder.py scan
   ```

3. **Test recording** (13 minutes):
   ```bash
   python3 /home/pi/kiwi_recorder.py record
   ```

### Setting Up Automation

Configure cron jobs for automatic recording:

```bash
python3 /home/pi/kiwi_recorder.py setup
```

This creates cron jobs that:
- Scan for best receivers at 00:42 London time
- Record at 00:47 London time (main broadcast)
- Record at 05:19 London time (morning broadcast)
- Trim logs weekly

### Verification

Check that everything is working:

```bash
# View recent log entries
tail -50 /home/pi/Shipping_Forecast_SDR_Recordings.log

# Check cron jobs
crontab -l

# View latest scan results (requires jq)
cat /home/pi/kiwi_scans/latest_scan_198.json | jq '.top20[] | {host, port, avg}'

# List recordings
ls -lh /home/pi/share/198k/*.wav
```

## Troubleshooting

### Common Issues

**Issue: "Python 3.9 or higher is required"**
- Update your system: `sudo apt-get update && sudo apt-get upgrade`
- Raspberry Pi OS Bookworm includes Python 3.11

**Issue: "kiwirecorder.py not found"**
- The kiwiclient installation failed
- Check network connectivity
- Manually clone: `git clone https://github.com/jks-prv/kiwiclient.git /home/pi/kiwiclient`

**Issue: "Low disk space warning"**
- Free up space or use external storage
- Recordings are ~100MB each (13 minutes, WAV format)
- Consider converting to MP3 for space savings

**Issue: "python3-requests not found"**
- Install manually: `sudo apt-get install python3-requests`
- Or check if it's already installed: `python3 -c "import requests; print(requests.__version__)"`

**Issue: Recording fails with timeout**
- Network connectivity to KiwiSDR server may be poor
- Try running another scan to find better receivers
- Check firewall settings

### Getting Help

View comprehensive documentation:
```bash
cat /home/pi/projects/recorder/CLAUDE.md
```

Check system status:
```bash
python3 /home/pi/kiwi_recorder.py --help
python3 /home/pi/kiwiclient/kiwirecorder.py --version
```

## Updating

### Update Recorder Script

```bash
cd /home/pi/projects/recorder
git pull  # If using git
sudo cp kiwi_recorder.py /home/pi/
```

### Update KiwiSDR Client

```bash
cd /home/pi/kiwiclient
git pull
```

### Update System Packages

```bash
sudo apt-get update
sudo apt-get upgrade
```

## Uninstallation

To remove the recorder system:

```bash
# Stop and remove cron jobs
python3 /home/pi/kiwi_recorder.py setup  # Shows current setup
crontab -e  # Remove the managed block

# Remove directories (CAREFUL - deletes recordings!)
rm -rf /home/pi/kiwi_scans
rm -rf /home/pi/share/198k
rm -rf /home/pi/kiwiclient

# Remove scripts
rm /home/pi/kiwi_recorder.py
rm /home/pi/requirements.txt
rm /home/pi/Shipping_Forecast_SDR_Recordings.log
```

## Configuration

### Changing Settings

Edit `/home/pi/kiwi_recorder.py` and modify the `Config` class:

```python
class Config:
    # Paths
    OUT_DIR = "/home/pi/share/198k"      # Change output location

    # Scanning
    SCAN_WORKERS = 15                     # Increase for faster scans
    TARGET_SCAN_COUNT = 100               # Scan more receivers

    # Recording
    DURATION_SEC = 13 * 60                # Change recording length
    FREQ_KHZ = "198"                      # Change frequency
```

### Custom Output Location

To use a different output directory (e.g., external USB drive):

1. Mount your storage
2. Edit `Config.OUT_DIR` in kiwi_recorder.py
3. Create the directory: `mkdir -p /mnt/usb/recordings`
4. Update nginx or web server config if serving files

## Advanced Usage

### Running on Boot

Add to `/etc/rc.local` (before `exit 0`):

```bash
# Start KiwiSDR recorder service
su - pi -c "python3 /home/pi/kiwi_recorder.py scan" &
```

### Custom Scan Schedule

Edit the cron jobs after running setup:

```bash
crontab -e
```

Look for the managed block between:
```
# >>> KIWI-SDR AUTO (managed) >>>
# ... your jobs here ...
# <<< KIWI-SDR AUTO (managed) <<<
```

### Integration with Web Server

To serve recordings via HTTP:

```bash
# Install nginx
sudo apt-get install nginx

# Configure nginx to serve /home/pi/share/198k
sudo nano /etc/nginx/sites-available/kiwi

# Add:
server {
    listen 80;
    server_name cherrypi.local;
    root /home/pi/share/198k;

    location / {
        autoindex on;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/kiwi /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

## Support

For issues or questions:
- Check CLAUDE.md for detailed documentation
- Review logs: `tail -f /home/pi/Shipping_Forecast_SDR_Recordings.log`
- Test components individually using the commands above

## License

This project uses:
- KiwiSDR client: BSD license (https://github.com/jks-prv/kiwiclient)
- Recorder script: Custom implementation
