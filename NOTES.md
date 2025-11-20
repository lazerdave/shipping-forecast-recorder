# Shipping Forecast Recorder - Operations Notes

## Public Podcast Feed Setup

### URLs
- **Public base URL**: https://zigbee.minskin-manta.ts.net/
- **Podcast feed**: https://zigbee.minskin-manta.ts.net/feed.xml
- **Latest recording**: https://zigbee.minskin-manta.ts.net/latest.wav

### Infrastructure

The podcast is served via nginx and Tailscale Funnel:

1. **nginx.service** (system service)
   - Serves /home/pi/share/198k/ on port 8080
   - Supports HTTP Range requests (required for podcast streaming)
   - Proper MIME types for MP3/WAV/XML
   - Configuration: /etc/nginx/sites-available/shipping-forecast
   - Auto-restarts on failure

2. **shipping-forecast-funnel.service** (custom service)
   - Exposes port 8080 to the internet via Tailscale Funnel
   - Runs as root (required for Tailscale funnel)
   - Depends on tailscaled.service and nginx.service
   - Location: /etc/systemd/system/shipping-forecast-funnel.service

### Management Commands

```bash
# View service status
sudo systemctl status nginx.service
sudo systemctl status shipping-forecast-funnel.service

# Restart services
sudo systemctl restart nginx.service
sudo systemctl restart shipping-forecast-funnel.service

# Stop services (will restart on boot)
sudo systemctl stop nginx.service
sudo systemctl stop shipping-forecast-funnel.service

# Disable auto-start on boot
sudo systemctl disable nginx.service
sudo systemctl disable shipping-forecast-funnel.service

# View service logs
sudo journalctl -u nginx.service -f
sudo journalctl -u shipping-forecast-funnel.service -f

# View nginx access/error logs
sudo tail -f /var/log/nginx/shipping-forecast-access.log
sudo tail -f /var/log/nginx/shipping-forecast-error.log

# Test nginx configuration
sudo nginx -t

# Reload nginx configuration (without dropping connections)
sudo systemctl reload nginx
```

### Tailscale Configuration

- Authenticated as user: **zigbee**
- Funnel enabled via: https://login.tailscale.com/f/funnel?node=nz5dt421Gj11CNTRL
- Running without requiring root via: `sudo tailscale set --operator=pi`

### Testing the Feed

You can test the feed is working with:

```bash
# Check HTTP server is responding
curl -I http://localhost:8080/feed.xml

# Check public URL is accessible
curl -I https://zigbee.minskin-manta.ts.net/feed.xml
```

### Adding to Podcast Apps

To subscribe in podcast apps:
1. Copy the feed URL: https://zigbee.minskin-manta.ts.net/feed.xml
2. In your podcast app, select "Add by URL" or "Add custom feed"
3. Paste the URL
4. The feed updates automatically after each recording

## Maintenance Notes

### Feed Updates
- The RSS feed is automatically regenerated after each recording
- Manual regeneration: `python3 /home/pi/kiwi_recorder.py feed`

### Storage Management
- Recordings are stored in /home/pi/share/198k/
- Each recording is ~12 MB (13 minutes of WAV audio)
- Feed includes the 50 most recent recordings
- Consider setting up log rotation if disk space becomes an issue

### Network Requirements
- Tailscale must be running for funnel to work
- Internet access required for:
  - Recording from KiwiSDR receivers
  - Serving the public feed
  - Scanning for receivers

### Troubleshooting

**Feed not updating:**
- Check recording succeeded: `ls -lh /home/pi/share/198k/*.wav`
- Check feed was regenerated: `ls -l /home/pi/share/198k/feed.xml`
- Manually regenerate: `python3 /home/pi/kiwi_recorder.py feed`

**Public URL not accessible:**
- Check services: `sudo systemctl status shipping-forecast-*`
- Check Tailscale: `tailscale status`
- Restart services if needed

**Port 8080 already in use:**
- Check what's using it: `sudo lsof -i :8080`
- Kill conflicting processes or change port in nginx configuration

**Episodes won't play in podcast app:**
- Verify Range request support: `curl -I -H "Range: bytes=0-1023" https://zigbee.minskin-manta.ts.net/latest.mp3`
- Should return HTTP 206 Partial Content
- Check nginx is running: `sudo systemctl status nginx`

## Change Log

### 2025-11-19: MP3 Conversion & HTTP Range Request Fix

**Problem:** Podcast episodes showed "This episode can't be played on this device" error in iOS/mobile apps.

**Root Cause:**
1. WAV files have poor podcast app support (especially iOS)
2. Python's `http.server` doesn't support HTTP Range requests (required for streaming)

**Solution:**
1. **Converted all audio to MP3 format**:
   - Converted 10 existing processed WAV files to MP3 (64 kbps bitrate)
   - File size reduction: ~19 MB → ~5.5-6.3 MB (3x smaller)
   - Added automatic MP3 conversion to `kiwi_recorder.py` after processing
   - Updated feed generation to prefer MP3 over WAV files

2. **Replaced Python HTTP server with nginx**:
   - Configured nginx to serve /home/pi/share/198k/ on port 8080
   - Enabled HTTP Range request support (critical for podcast streaming)
   - Proper MIME types for MP3/WAV/XML files
   - Cache headers for better performance
   - Configuration: /etc/nginx/sites-available/shipping-forecast

3. **Updated infrastructure**:
   - Removed shipping-forecast-http.service (Python http.server)
   - Now using nginx.service (system service)
   - Updated shipping-forecast-funnel.service dependencies
   - All services auto-start on boot

**Files Modified:**
- `/home/pi/kiwi_recorder.py`: Added `convert_to_mp3()` function, updated `list_audio_files()`
- `/etc/nginx/sites-available/shipping-forecast`: New nginx configuration
- `/etc/systemd/system/shipping-forecast-funnel.service`: Updated dependencies
- `NOTES.md`, `CLAUDE.md`: Updated documentation

**Verification:**
```bash
# Test Range request support (should return HTTP 206)
curl -I -H "Range: bytes=0-1023" https://zigbee.minskin-manta.ts.net/latest.mp3

# Should see:
# HTTP/2 206
# accept-ranges: bytes
# content-range: bytes 0-1023/XXXXXX
```

### 2025-11-19: Public Podcast Feed Setup
- Created systemd services for automatic HTTP server and Tailscale funnel
- Configured Tailscale authentication and funnel access
- Set up public URL: https://zigbee.minskin-manta.ts.net/
- Renamed podcast to "Shipping Forecast Tailscale"
- Added "The Great Wave off Kanagawa" artwork
- Added auto-start on boot for both services
- Created this documentation file
