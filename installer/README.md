# Shipping Forecast Recorder Installer v0.1

Interactive installer for the BBC Radio 4 Shipping Forecast automated recording system.

## Features

- **Interactive Configuration**: Guided setup with sensible defaults
- **Multi-Distribution Support**: Works on Debian, Ubuntu, Fedora, Arch, and derivatives
- **Professional UI**: 256-color terminal interface with progress indicators
- **Tailscale Integration**: Optional public podcast feed via Tailscale Funnel
- **QR Code Authentication**: Mobile-friendly Tailscale setup
- **Rollback System**: Automatic cleanup on installation failures
- **Multiple Modes**: Interactive, silent, update, dry-run, and diagnostic modes

## Quick Start

### Interactive Installation (Recommended)

```bash
cd /home/pi/projects/shipping-forecast-recorder/installer
./install.sh
```

This will:
1. Run pre-flight system checks
2. Prompt for configuration options
3. Install all dependencies
4. Set up nginx HTTP server
5. Configure Tailscale (optional)
6. Schedule automated recordings via cron

### Silent Installation

For automated setups with default configuration:

```bash
./install.sh --silent
```

### Update Existing Installation

To update an existing installation:

```bash
./install.sh --update
```

### Preview Changes (Dry Run)

To see what would be installed without making changes:

```bash
./install.sh --dry-run
```

### Run Diagnostics Only

To check system compatibility:

```bash
./install.sh --diagnose
```

## Requirements

### Minimum Requirements

- Linux operating system (Debian, Ubuntu, Fedora, Arch, or derivatives)
- Python 3.7 or newer
- 500 MB free disk space
- Internet connectivity
- sudo privileges

### Optional Components

- Git (for KiwiSDR client)
- Nginx (for HTTP server)
- Tailscale (for public access)
- Cron (for automated scheduling)

## Installation Stages

The installer performs the following stages:

1. **Pre-flight Checks**: Validates system compatibility
2. **Configuration**: Interactive or silent configuration
3. **System Dependencies**: Installs required packages
4. **Python Dependencies**: Sets up Python environment
5. **KiwiSDR Client**: Clones and installs KiwiSDR client
6. **Application Setup**: Installs kiwi_recorder.py and assets
7. **Nginx Configuration**: Sets up HTTP server for podcast feed
8. **Tailscale Setup**: Configures public access (optional)
9. **Cron Scheduling**: Schedules automated recordings
10. **Validation**: Verifies installation success

## Configuration Options

During interactive installation, you'll be prompted to configure:

### Paths

- **Installation Directory**: Default `/home/pi`
- **Output Directory**: Default `/home/pi/share/198k`
- **Scan Directory**: Default `/home/pi/kiwi_scans`

### Recording Parameters

- **Frequency**: Default `198` kHz (BBC Radio 4 Longwave)
- **Duration**: Default `780` seconds (13 minutes)
- **Scan Workers**: Default `15` (parallel scan threads)

### Podcast Settings

- **Podcast Title**: Default "Shipping Forecast Tailscale"
- **Podcast Author**: Default "BBC Radio 4"

### Optional Components

- **Enable Tailscale**: Public internet access
- **Enable Nginx**: HTTP server for podcast feed
- **Enable Cron**: Automated scheduling

## Post-Installation

After installation, you can:

### Test Recording

```bash
python3 ~/kiwi_recorder.py record
```

### Generate Podcast Feed

```bash
python3 ~/kiwi_recorder.py feed
```

### Run Network Scan

```bash
python3 ~/kiwi_recorder.py scan
```

### Check Logs

```bash
tail -f ~/Shipping_Forecast_SDR_Recordings.log
```

## Feed URLs

### Local Access

After installation, your podcast feed will be available at:

```
http://<your-local-ip>:8080/feed.xml
```

### Public Access (with Tailscale)

If you enabled Tailscale Funnel, your feed will be publicly accessible at:

```
https://<your-tailscale-hostname>.ts.net/feed.xml
```

The installer will display the exact URLs upon completion.

## Troubleshooting

### Pre-flight Checks Fail

If pre-flight checks fail, review the error messages and ensure:
- You have sudo privileges
- Internet connectivity is working
- Required disk space is available
- Python 3.7+ is installed

### Installation Fails Mid-Process

The installer includes automatic rollback functionality. If prompted, allow rollback to revert changes. Review error messages and try again.

### Port 8080 Already in Use

The installer will detect this and offer to reconfigure. If you need a different port, specify it during configuration.

### Tailscale Authentication Times Out

Authentication requires completing the login process within 5 minutes. If it times out:
1. Run `./install.sh --update` to reconfigure
2. Choose the QR code option for mobile devices
3. Complete authentication promptly

## Advanced Usage

### Configuration File

Installation settings are saved to:

```
~/.shipping-forecast.conf
```

You can edit this file and run `./install.sh --update` to apply changes.

### Rollback System

The installer tracks all changes made during installation. If something goes wrong, rollback is automatic. To manually trigger rollback:

```bash
# View rollback log
cat /tmp/shipping-forecast-rollback.log

# Rollback is triggered automatically on errors
```

### Installation State

Installation progress is tracked in:

```
/tmp/shipping-forecast-install.state
```

This allows resuming failed installations from the last successful stage.

## Architecture

The installer is modular, consisting of:

- **install.sh**: Main orchestration script
- **lib/colors.sh**: Color definitions and output helpers
- **lib/ui.sh**: Interactive UI components
- **lib/checks.sh**: Pre-flight validation functions
- **lib/packages.sh**: Multi-distribution package management
- **lib/config.sh**: Configuration management
- **lib/rollback.sh**: Error handling and rollback
- **lib/tailscale.sh**: Tailscale authentication and setup

## Contributing

To improve the installer:

1. Test on different distributions
2. Report issues with system compatibility
3. Suggest UI improvements
4. Add support for new package managers

## License

Same as the parent Shipping Forecast Recorder project.

## Support

For issues or questions:

1. Review this README
2. Check the main project documentation
3. Review installation logs
4. Run diagnostic mode: `./install.sh --diagnose`

## Version History

### v0.1 (2025-11-28)

- Initial release
- Interactive and silent installation modes
- Multi-distribution support (apt, dnf, pacman, zypper)
- Professional 256-color terminal UI
- Tailscale integration with QR code authentication
- Automatic rollback on failure
- Configuration persistence and update mode
- Dry-run and diagnostic modes
