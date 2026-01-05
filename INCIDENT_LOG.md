# Shipping Forecast Recorder - Incident Log

This log tracks recording failures, root causes, and fixes for the Shipping Forecast Recorder project.

---

## 2026-01-05: Rack Primary Recording Failed (Threshold Too Strict)

### Summary
- **Most Recent Recording:** zigbee (backup) at 18:03 MST
- **Rack (primary) Status:** FAILED - partial recordings discarded
- **Public Feed:** Stale (showing Jan 4 as latest)

### What Happened
Rack attempted parallel recording from two receivers:
- **r0 (g8gporx.proxy.kiwisdr.com):** 12.62 MB - rejected (below 13 MB threshold)
- **r1 (websdr.uk):** 4.8 MB - failed ("Too busy now" errors throughout recording)

Both recordings were rejected because neither met the MIN_VALID_SIZE_MB threshold of 13 MB. The r0 recording was only 0.38 MB (2.9%) under the threshold and likely contains complete broadcast audio.

### Root Cause
1. **Threshold too aggressive:** 13 MB = 60% of expected 21 MB WAV, but actual broadcast duration varies
2. **websdr.uk unreliable:** Chronically returns "Too busy" during peak times (00:47 UTC)
3. **Cleanup didn't run:** Orphan partial files remain in Rack's share directory

### Orphan Files (Need Cleanup)
**Rack container (/root/share/198k/):**
- ShippingFCST-260105_AM_004702UTC--parallel--avg-0_r0.wav (12.62 MB) ← **RECOVERABLE**
- ShippingFCST-260105_AM_004702UTC--parallel--avg-0_r1.wav (4.8 MB)
- ShippingFCST-251222_AM_004706UTC--parallel--avg-0_r1.wav (2.0 MB)
- ShippingFCST-251223_AM_043740UTC--parallel--avg-0_r{0,1}.wav
- ShippingFCST-251230_AM_004702UTC--parallel--avg-0_r0.wav (0.2 MB)
- ShippingFCST-260101_AM_004702UTC--parallel--avg-0_r1.wav (0.2 MB)

**zigbee (/home/pi/share/198k/):**
- ShippingFCST-251222_AM_004706UTC--parallel--avg-0_r1.wav (2.0 MB)
- ShippingFCST-260105_AM_004705UTC--parallel--avg-0_r1.wav (1.1 MB)

### Repair Steps
1. [ ] Lower MIN_VALID_SIZE_MB from 13 to 11 MB in kiwi_recorder.py Config
2. [ ] Add websdr.uk to receiver blocklist (EXCLUDED_HOSTS)
3. [ ] Recover Rack's Jan 5 r0.wav: rename to final filename, run post-processing
4. [ ] Clean up orphan parallel files on both systems
5. [ ] Rebuild Rack feed to include recovered recording

### Why This Fix Will Work
- **11 MB threshold** is ~52% of expected 21 MB - still ensures majority of broadcast captured
- A 12.62 MB recording is ~10 minutes of audio at 12 kHz/16-bit - more than enough for a complete forecast
- Blocking websdr.uk forces selection of more reliable backup receivers (ixworthsdr, norfolk, etc.)
- Previous threshold was based on 60% of 13-minute recording, but actual broadcast is ~12 minutes

---

## 2025-12-28/29: zigbee VPN Namespace Connectivity Failures

### Summary
- **Recordings:** FAILED on both days
- **Error:** "File not created" for both receivers

### What Happened
Both days attempted parallel recording from g8gporx and websdr.uk, but kiwirecorder couldn't connect to either receiver.

### Root Cause
VPN namespace (vpn-ns) had connectivity issues. The namespace service was running but WireGuard tunnel may have been down or DNS resolution failed.

### Fix Applied
- VPN namespace service was restarted
- Connectivity verified with `sudo ip netns exec vpn-ns curl ifconfig.me`
- No code changes required

### Why It Recurred
The vpn-namespace.service is a oneshot that sets up the namespace at boot. If WireGuard loses connection (ISP hiccup, NordVPN server issue), the namespace stays "active" but traffic doesn't route. Need periodic health checks.

### Potential Improvement
Add VPN health check before recording:
```bash
# In crontab, before record command:
45 17 * * * sudo ip netns exec vpn-ns curl -s --connect-timeout 5 ifconfig.me || sudo systemctl restart vpn-namespace
```

---

## 2025-12-20: Parallel Recording System Implemented

### Context
Two recording failures in one week (Dec 18, Dec 20) due to receiver overload. With BBC R4 longwave shutdown confirmed for September 26, 2026, these recordings are irreplaceable historical artifacts.

### Solution
Implemented parallel recording from top N receivers (default: 2):
1. Selects top N receivers from scan results
2. Records simultaneously from all N
3. Evaluates recordings by size and RSSI
4. Promotes best recording, deletes others

### Configuration
```python
Config.PARALLEL_RECORDINGS = 2
Config.MIN_VALID_SIZE_MB = 13  # ← ISSUE: too strict, needs lowering
```

---

## Recording Gap Summary

| Date | System | Status | Cause |
|------|--------|--------|-------|
| 2025-12-17 | zigbee | MISSED | Crontab cleared by `crontab -` |
| 2025-12-20 | zigbee | MISSED | Receiver overload (pre-parallel) |
| 2025-12-28 | zigbee | MISSED | VPN namespace connectivity |
| 2025-12-29 | zigbee | MISSED | VPN namespace connectivity |
| 2026-01-04 | zigbee | MISSED | Unknown (need investigation) |
| 2026-01-05 | Rack | FAILED | Threshold too strict (12.62 MB < 13 MB) |

---

## Monitoring Commands

```bash
# Check most recent recording
ls -la /home/pi/share/198k/*.mp3 | tail -1

# Check Rack container status
ssh root@192.168.4.64 "docker exec shipping-forecast ls -la /root/share/198k/*.mp3 | tail -1"

# Check VPN namespace
sudo ip netns exec vpn-ns curl -s ifconfig.me

# Check for orphan parallel files
ls /home/pi/share/198k/*parallel* 2>/dev/null
ssh root@192.168.4.64 "docker exec shipping-forecast ls /root/share/198k/*parallel* 2>/dev/null"

# Rebuild feed
python3 /home/pi/kiwi_recorder.py feed
```
