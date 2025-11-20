#!/usr/bin/env python3
"""
KiwiSDR Recorder - Automated radio recording and podcast generation

Commands:
  scan      Scan KiwiSDR network for best receivers
  record    Record from best receiver and update feed
  feed      Rebuild RSS/podcast feed
  setup     Configure cron jobs for automated operation

Features:
- Parallel scanning for 10x speed improvement
- Automatic receiver selection based on signal strength
- RSS/podcast feed generation
- Automated cron scheduling with timezone handling
"""

import argparse
import email.utils
import html
import json
import logging
import os
import pathlib
import random
import re
import socket
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import numpy as np
import requests
import wave
from scipy import signal


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Centralized configuration for all KiwiSDR operations"""

    # Paths (platform-agnostic using home directory)
    HOME = Path.home()
    KIWI_REC_PATH = str(HOME / "kiwiclient" / "kiwirecorder.py")
    OUT_DIR = str(HOME / "share" / "198k")
    SCAN_DIR = str(HOME / "kiwi_scans")
    SCAN_POINTER = str(HOME / "kiwi_scans" / "latest_scan_198.json")
    LOG_FILE = str(HOME / "Shipping_Forecast_SDR_Recordings.log")
    FEED_PATH = HOME / "share" / "198k" / "feed.xml"
    ART_NAME = "artwork.jpg"
    ANTHEM_TEMPLATE = str(HOME / "share" / "198k" / "anthem_template.wav")

    # Recording settings
    FREQ_KHZ = "198"
    MODE = "am"
    DURATION_SEC = 15 * 60  # 15 minutes (captures full forecast + anthem + handoff)

    # Scanning settings
    PROBE_SEC = 8
    DEEP_SEC = 20
    RSSI_FLOOR = -65.0
    TARGET_SCAN_COUNT = 100
    RSSI_REFRESH_SEC = 6
    SCAN_WORKERS = 15  # Parallel workers for scanning

    # Network timeouts
    CONNECT_TIMEOUT = 7
    DISCOVERY_TIMEOUT = 8
    RECORDING_TIMEOUT_MARGIN = 60  # Extra seconds beyond duration

    # Feed settings
    MAX_FEED_ITEMS = 50
    AUDIO_EXTS = (".mp3", ".wav", ".m4a")
    FEED_TITLE = "Shipping Forecast Tailscale"
    FEED_DESC = "Automated 198 kHz Shipping Forecast recordings via KiwiSDR, delivered via Tailscale."
    FEED_LANG = "en-gb"

    # Configurable via environment variables
    HOSTNAME = socket.gethostname()
    FEED_AUTHOR = os.getenv("FEED_AUTHOR", f"KiwiSDR capture on {HOSTNAME}")
    BASE_URL = os.getenv("BASE_URL", "https://zigbee.minskin-manta.ts.net")

    # Fallback receiver
    FALLBACK_HOST = "norfolk.george-smart.co.uk"
    FALLBACK_PORT = 8073

    # KiwiSDR discovery
    PUBLIC_LIST_URLS = [
        "https://kiwisdr.com/public/",
        "https://kiwisdr.com/.public/",
    ]

    COUNTRY_KEYS = [
        "United Kingdom", "England", "Scotland", "Wales", "Northern Ireland",
        "Isle of Man", "Jersey", "Guernsey", "Channel Islands",
        "Ireland", "Belgium", "Netherlands", "France", "Luxembourg", "GB", "UK"
    ]

    HOST_HINTS = (".uk", ".ie", ".je", ".gg", ".im", ".nl", ".be", ".fr")

    SEED_HOSTS = [
        "norfolk.george-smart.co.uk:8073",
        "fordham.george-smart.co.uk:8073",
        "ixworthsdr.hopto.org:8073",
        "21785.proxy.kiwisdr.com:8073",
        "kernow.hopto.org:8073",
        "21246.proxy.kiwisdr.com:8073",
        "21247.proxy.kiwisdr.com:8073",
        "g4wim.proxy.kiwisdr.com:8073",
        "193.237.203.108:8074",
        "kiwisdr.g0dub.uk:8073",
        "g8gporx.proxy.kiwisdr.com:8073",
        "websdr.uk:8073",
        "21182.proxy.kiwisdr.com:8073",
        "21181.proxy.kiwisdr.com:8073",
        "antskiwisdr.zapto.org:8077",
        "antskiwisdr.zapto.org:8078",
        "185.128.57.240:8073",
        "21826.proxy.kiwisdr.com:8073",
        "uk-kiwisdr2.proxy.kiwisdr.com:8073",
    ]


# ============================================================================
# SHARED UTILITIES
# ============================================================================

# Compiled regex patterns for RSSI parsing
HTTP_URL_RE = re.compile(r"https?://([A-Za-z0-9\-\.\:]+)", re.I)
RSSI_NUM_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*dB(?:FS)?", re.I)
RSSI_RSSI_RE = re.compile(r"RSSI[=:]\s*(-?\d+(?:\.\d+)?)", re.I)
FILENAME_PATTERN = re.compile(
    r"ShippingFCST-(\d{6})_(AM|PM)_(\d{6})UTC--(.+?)--avg-(\d+)\.[^\.]+$",
    re.IGNORECASE
)

# Met Office Shipping Forecast URL
METOFFICE_FORECAST_URL = "https://weather.metoffice.gov.uk/specialist-forecasts/coast-and-sea/print/shipping-forecast"


def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """Configure logging for the application"""
    logger = logging.getLogger("kiwi_recorder")
    logger.setLevel(logging.INFO)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(file_handler)

    return logger


def parse_rssi_output(output: str) -> Optional[List[float]]:
    """Extract RSSI values from kiwirecorder output"""
    vals = [float(x) for x in RSSI_NUM_RE.findall(output)]
    if not vals:
        vals = [float(x) for x in RSSI_RSSI_RE.findall(output)]
    return vals if vals else None


def probe_smeter(
    host: str,
    port: int,
    seconds: int,
    logger: logging.Logger
) -> Tuple[Optional[List[float]], Optional[str]]:
    """
    Probe a KiwiSDR receiver's S-meter readings

    Returns:
        (values_list, error_string) - values if successful, error description if failed
    """
    cmd = [
        "python3", Config.KIWI_REC_PATH,
        "-s", host, "-p", str(port),
        "-f", Config.FREQ_KHZ,
        "--S-meter=1",
        "--time-limit", str(seconds),
        "--quiet"
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=seconds + Config.CONNECT_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:
        return None, f"error: {e}"

    output = (proc.stdout or "") + (proc.stderr or "")
    vals = parse_rssi_output(output)

    if not vals:
        return None, "no-RSSI"

    return vals, None


def hostname_short(host: str) -> str:
    """Shorten hostname: g8gporx.proxy.kiwisdr.com -> g8gporx.proxy.kiwisdr"""
    h = host.split(":")[0]
    parts = h.split(".")
    if len(parts) >= 3:
        return ".".join(parts[:3])
    elif len(parts) == 2:
        return parts[0]
    return h


def signal_strength_bar(rssi: float) -> str:
    """
    Create visual signal strength bar

    Args:
        rssi: Signal strength in dBFS (typically -90 to -20)

    Returns:
        Visual bar with label, e.g., "████████░░░░ -45.2dB (GOOD)"
    """
    # Normalize RSSI to 0-100 scale
    # Typical range: -90 (weak) to -20 (strong)
    min_dbfs = -90.0
    max_dbfs = -20.0

    # Clamp and normalize
    normalized = max(0, min(100, (rssi - min_dbfs) / (max_dbfs - min_dbfs) * 100))

    # Create bar (12 blocks total)
    bar_length = 12
    filled = int(normalized / 100 * bar_length)
    empty = bar_length - filled
    bar = "█" * filled + "░" * empty

    # Quality label
    if rssi >= -30:
        quality = "EXCELLENT"
    elif rssi >= -40:
        quality = "VERY GOOD"
    elif rssi >= -50:
        quality = "GOOD"
    elif rssi >= -60:
        quality = "FAIR"
    elif rssi >= -70:
        quality = "WEAK"
    else:
        quality = "POOR"

    return f"{bar} {rssi:>6.1f}dB ({quality})"


def now_parts_with_ampm() -> Tuple[str, str, str]:
    """Return tuple (utc_date, ampm, utc_time)"""
    now_utc = datetime.now(timezone.utc)
    ampm = now_utc.strftime("%p")  # AM or PM
    utc_date = now_utc.strftime("%y%m%d")
    utc_time = now_utc.strftime("%H%M%S")
    return utc_date, ampm, utc_time


def ensure_dir(path: str) -> None:
    """Ensure directory exists"""
    os.makedirs(path, exist_ok=True)


def fetch_shipping_forecast(logger: logging.Logger) -> Optional[str]:
    """
    Fetch the current Shipping Forecast from Met Office

    Returns:
        HTML content of the forecast, or None if fetch fails
    """
    try:
        logger.info(f"Fetching shipping forecast from {METOFFICE_FORECAST_URL}")
        response = requests.get(
            METOFFICE_FORECAST_URL,
            timeout=Config.DISCOVERY_TIMEOUT,
            headers={"User-Agent": "KiwiSDR-Recorder/1.0"}
        )
        response.raise_for_status()

        # Extract the body content (everything between <body> and </body>)
        content = response.text
        body_start = content.find('<body')
        body_end = content.find('</body>')

        if body_start != -1 and body_end != -1:
            # Find the end of the opening <body> tag
            body_start = content.find('>', body_start) + 1
            forecast_html = content[body_start:body_end].strip()
            logger.info(f"Successfully fetched shipping forecast ({len(forecast_html)} chars)")
            return forecast_html
        else:
            logger.warning("Could not find <body> tags in forecast page")
            return content  # Return full content as fallback

    except requests.Timeout:
        logger.warning(f"Timeout fetching shipping forecast after {Config.DISCOVERY_TIMEOUT}s")
        return None
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch shipping forecast: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error fetching shipping forecast: {e}")
        return None


def detect_anthem_start(wav_path: str, logger: logging.Logger) -> Optional[Tuple[float, int]]:
    """
    Detect where the national anthem starts using cross-correlation with a template

    Uses a pre-recorded anthem sample (drumroll + opening notes) to find the
    anthem in the recording via cross-correlation pattern matching.

    Scans from 10 minutes onwards to avoid false positives.

    Returns:
        Tuple of (time_in_seconds, sample_index) or None if not found
    """
    try:
        # Check if template exists
        if not os.path.exists(Config.ANTHEM_TEMPLATE):
            logger.warning(f"Anthem template not found: {Config.ANTHEM_TEMPLATE}")
            return None

        # Load template
        with wave.open(Config.ANTHEM_TEMPLATE, 'r') as wav:
            frames = wav.readframes(wav.getnframes())
            template_rate = wav.getframerate()
            template = np.frombuffer(frames, dtype=np.int16).astype(np.float32)

        # Load recording
        with wave.open(wav_path, 'r') as wav:
            frames = wav.readframes(wav.getnframes())
            rec_rate = wav.getframerate()
            recording = np.frombuffer(frames, dtype=np.int16).astype(np.float32)

        # Verify sample rates match
        if template_rate != rec_rate:
            logger.warning(f"Sample rate mismatch! Template: {template_rate}, Recording: {rec_rate}")
            return None

        # Start search from 10 minutes
        start_search_time = 10 * 60
        start_sample = int(start_search_time * rec_rate)

        if start_sample >= len(recording):
            logger.warning("Recording too short for anthem detection")
            return None

        search_region = recording[start_sample:]

        # Normalize both signals
        template_norm = (template - np.mean(template)) / np.std(template)
        search_norm = (search_region - np.mean(search_region)) / np.std(search_region)

        # Compute cross-correlation
        correlation = signal.correlate(search_norm, template_norm, mode='valid')

        # Find peak
        peak_idx = np.argmax(correlation)
        peak_value = correlation[peak_idx]

        # Convert to time in original recording
        detection_sample = start_sample + peak_idx
        detection_time = detection_sample / rec_rate

        logger.info(f"Anthem detected at {int(detection_time // 60)}:{int(detection_time % 60):02d} (correlation: {peak_value:.1f})")

        return detection_time, detection_sample

    except Exception as e:
        logger.warning(f"Error detecting anthem: {e}")
        return None


def process_recording(
    wav_path: str,
    fade_duration: float,
    logger: logging.Logger,
    insert_test_beep: bool = True
) -> Optional[str]:
    """
    Process a recording by detecting the anthem and fading out

    Args:
        wav_path: Path to the WAV file to process
        fade_duration: Duration of fade in seconds
        logger: Logger instance
        insert_test_beep: If True, insert a test tone at the cut point

    Returns:
        Path to processed file, or None if processing failed
    """
    try:
        # Detect where to cut
        result = detect_anthem_start(wav_path, logger)
        if not result:
            logger.warning("Skipping post-processing - no anthem detected")
            return None

        cut_time, cut_sample = result

        with wave.open(wav_path, 'r') as wav_in:
            params = wav_in.getparams()
            frames = wav_in.readframes(wav_in.getnframes())
            sample_rate = wav_in.getframerate()
            samples = np.frombuffer(frames, dtype=np.int16).copy()

            # Insert test beep if requested
            if insert_test_beep:
                tone_duration = 0.125
                tone_freq = 1000
                tone_samples = int(tone_duration * sample_rate)

                # Create sine wave
                t = np.arange(tone_samples) / sample_rate
                tone = np.sin(2 * np.pi * tone_freq * t)

                # Scale to 12.5% volume
                tone = (tone * 4096).astype(np.int16)

                # Insert tone
                tone_end = cut_sample + tone_samples
                if tone_end < len(samples):
                    samples[cut_sample:tone_end] = tone
                    fade_start = tone_end
                else:
                    fade_start = cut_sample
            else:
                fade_start = cut_sample

            # Apply fade
            fade_samples = int(fade_duration * sample_rate)
            fade_end = fade_start + fade_samples

            for i in range(fade_start, min(fade_end, len(samples))):
                fade_factor = 1.0 - ((i - fade_start) / fade_samples)
                samples[i] = int(samples[i] * fade_factor)

            # Truncate after fade
            samples = samples[:fade_end]

            # Write processed file
            processed_path = wav_path.replace('.wav', '_processed.wav')
            with wave.open(processed_path, 'w') as wav_out:
                wav_out.setparams(params)
                wav_out.writeframes(samples.tobytes())

            output_duration = len(samples) / sample_rate
            logger.info(f"Processed: {processed_path}")
            logger.info(f"  Original duration: 13:00")
            logger.info(f"  Processed duration: {int(output_duration // 60)}:{int(output_duration % 60):02d}")
            logger.info(f"  Cut at: {int(cut_time // 60)}:{int(cut_time % 60):02d}")
            logger.info(f"  Fade: {fade_duration}s")

            # Convert to MP3
            mp3_path = convert_to_mp3(processed_path, logger)
            if mp3_path:
                logger.info(f"Converted to MP3: {mp3_path}")

            return processed_path

    except Exception as e:
        logger.error(f"Post-processing failed: {e}")
        return None


def convert_to_mp3(wav_path: str, logger: logging.Logger, bitrate: str = "64k") -> Optional[str]:
    """
    Convert WAV file to MP3 using ffmpeg.

    Args:
        wav_path: Path to WAV file
        logger: Logger instance
        bitrate: MP3 bitrate (default: 64k for speech)

    Returns:
        Path to MP3 file, or None if conversion failed
    """
    try:
        mp3_path = wav_path.replace('.wav', '.mp3')

        cmd = [
            'ffmpeg', '-i', wav_path,
            '-codec:a', 'libmp3lame',
            '-b:a', bitrate,
            '-y',  # Overwrite output file
            mp3_path
        ]

        # Run conversion with suppressed output
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0 and os.path.exists(mp3_path):
            return mp3_path
        else:
            logger.warning(f"MP3 conversion failed for {wav_path}")
            return None

    except Exception as e:
        logger.warning(f"MP3 conversion error: {e}")
        return None


# ============================================================================
# SCAN COMMAND
# ============================================================================

def fetch_candidates(logger: logging.Logger) -> List[str]:
    """Fetch candidate KiwiSDR hosts from public listings"""
    found = []

    for url in Config.PUBLIC_LIST_URLS:
        try:
            r = requests.get(url, timeout=Config.DISCOVERY_TIMEOUT)
            r.raise_for_status()
            text = r.text
        except Exception:
            # Public list unavailable, will use seeds
            continue

        for line in text.splitlines():
            if not line.strip():
                continue

            country_hit = any(k in line for k in Config.COUNTRY_KEYS)

            for m in HTTP_URL_RE.finditer(line):
                hp = m.group(1)
                if ":" not in hp:
                    continue

                host, port = hp.rsplit(":", 1)
                if port not in ("8073", "8074"):
                    continue

                hint_hit = any(h in host.lower() for h in Config.HOST_HINTS)

                if country_hit or hint_hit:
                    found.append(f"{host}:{port}")

    # Merge with seeds, dedupe, shuffle
    candidates = list(dict.fromkeys(found + Config.SEED_HOSTS))
    random.shuffle(candidates)
    return candidates


def scan_single_host(
    host_port: str,
    index: int,
    total: int,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Scan a single host (for parallel execution)

    Returns dict with 'status': 'kept'|'skipped' and relevant data
    """
    host, port_str = host_port.rsplit(":", 1)
    port = int(port_str)
    tag = f"{host}:{port}"

    # Shorten hostname for cleaner display
    short_host = hostname_short(host)
    display_tag = f"{short_host}:{port}"

    logger.info(f"[{index:3d}/{total}] {display_tag:35s} ", extra={'end': ''})

    vals, err = probe_smeter(host, port, Config.PROBE_SEC, logger)

    if err:
        logger.info(f"✗ SKIP - {err}")
        return {
            "status": "skipped",
            "host": host,
            "port": port,
            "reason": err
        }

    avg = statistics.mean(vals)

    if avg < Config.RSSI_FLOOR:
        logger.info(f"✗ TOO WEAK - {signal_strength_bar(avg)}")
        return {
            "status": "skipped",
            "host": host,
            "port": port,
            "reason": f"weak {avg:.1f}"
        }

    mn, mx = min(vals), max(vals)
    logger.info(f"✓ {signal_strength_bar(avg)} (n={len(vals)})")

    return {
        "status": "kept",
        "host": host,
        "port": port,
        "avg": round(avg, 1),
        "min": round(mn, 1),
        "max": round(mx, 1),
        "n": len(vals)
    }


def deep_probe_host(
    row: Dict[str, Any],
    index: int,
    logger: logging.Logger
) -> Optional[Dict[str, Any]]:
    """Perform deep probe on a single host"""
    short_host = hostname_short(row["host"])
    display_tag = f'{short_host}:{row["port"]}'
    logger.info(f"[Deep {index:2d}/20] {display_tag:35s} ", extra={'end': ''})

    vals, err = probe_smeter(row["host"], row["port"], Config.DEEP_SEC, logger)

    if err:
        logger.info(f"✗ FAILED - {err}")
        return None

    avg = statistics.mean(vals)
    med = statistics.median(vals)
    mn, mx = min(vals), max(vals)
    stdev = statistics.pstdev(vals) if len(vals) > 1 else 0.0

    logger.info(
        f'✓ {signal_strength_bar(avg)} | med={med:.1f} σ={stdev:.1f} n={len(vals)}'
    )

    return {
        "host": row["host"],
        "port": row["port"],
        "avg": round(avg, 1),
        "median": round(med, 1),
        "stdev": round(stdev, 2),
        "min": round(mn, 1),
        "max": round(mx, 1),
        "n": len(vals)
    }


def cmd_scan(args, logger: logging.Logger) -> int:
    """Execute scan command - find best KiwiSDR receivers"""
    logger.info("=" * 80)
    logger.info("  KiwiSDR Network Scanner - Finding Best 198 kHz Receivers")
    logger.info("=" * 80)
    logger.info(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info("")
    logger.info("Discovering receivers...")

    discovered = fetch_candidates(logger)

    if not discovered:
        logger.warning("No candidates from public list(s). Using seeds only.")
        discovered = Config.SEED_HOSTS[:]

    logger.info(
        f"Found {len(discovered)} candidates, "
        f"screening up to {Config.TARGET_SCAN_COUNT} with "
        f"{Config.SCAN_WORKERS} parallel workers..."
    )
    logger.info("─" * 80)

    t0 = time.perf_counter()

    # Parallel scanning
    to_scan = discovered[:Config.TARGET_SCAN_COUNT]
    kept_rows = []
    skipped_rows = []

    with ThreadPoolExecutor(max_workers=Config.SCAN_WORKERS) as executor:
        futures = {
            executor.submit(scan_single_host, hp, i+1, len(to_scan), logger): hp
            for i, hp in enumerate(to_scan)
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                if result["status"] == "kept":
                    kept_rows.append({k: v for k, v in result.items() if k != "status"})
                else:
                    skipped_rows.append({k: v for k, v in result.items() if k != "status"})
            except Exception as e:
                logger.error(f"Scan error: {e}")

    screen_s = time.perf_counter() - t0
    kept_rows.sort(key=lambda r: r["avg"], reverse=True)
    top20 = kept_rows[:20]

    logger.info("─" * 80)
    logger.info(
        f"✓ Initial screening complete: {len(kept_rows)} receivers passed, "
        f"{len(skipped_rows)} rejected ({screen_s:.1f}s)"
    )

    # Deep probe top 20 (sequential is fine here, only 20 hosts)
    deep = []
    logger.info("")
    logger.info("━" * 80)
    logger.info(f"  Phase 2: Deep Analysis (20-second probe on top {len(top20)} receivers)")
    logger.info("━" * 80)

    for i, row in enumerate(top20, 1):
        result = deep_probe_host(row, i, logger)
        if result:
            deep.append(result)

    deep.sort(key=lambda r: r["avg"], reverse=True)
    total_s = time.perf_counter() - t0

    # Save results
    payload = {
        "stamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z",
        "freq_khz": int(Config.FREQ_KHZ),
        "probe_sec": Config.PROBE_SEC,
        "deep_sec": Config.DEEP_SEC,
        "rssi_floor": Config.RSSI_FLOOR,
        "tested": len(to_scan),
        "kept": len(kept_rows),
        "screen_seconds": round(screen_s, 1),
        "total_seconds": round(total_s, 1),
        "top20": deep,
        "kept_initial": kept_rows,
        "skipped": skipped_rows
    }

    ensure_dir(Config.SCAN_DIR)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    scan_path = os.path.join(Config.SCAN_DIR, f"scan_198_{ts}.json")

    with open(scan_path, "w") as f:
        json.dump(payload, f, indent=2)

    # Update pointer atomically
    tmp = Config.SCAN_POINTER + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, Config.SCAN_POINTER)

    # Final summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("  ✓ SCAN COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Duration:         {total_s:.1f}s ({total_s/60:.1f} minutes)")
    logger.info(f"Tested:           {len(to_scan)} receivers")
    logger.info(f"Passed initial:   {len(kept_rows)} receivers")
    logger.info(f"Deep analyzed:    {len(deep)} receivers")
    if deep:
        logger.info("")
        logger.info("┌─ TOP 5 RECEIVERS " + "─" * 61)
        for i, r in enumerate(deep[:5], 1):
            short_host = hostname_short(r['host'])
            display_tag = f"{short_host}:{r['port']}"
            logger.info(f"│ {i}. {display_tag:35s} {signal_strength_bar(r['avg'])}")
        logger.info("└" + "─" * 79)
    logger.info("")
    logger.info(f"Results saved: {scan_path}")
    logger.info("=" * 80)

    return 0


# ============================================================================
# RECORD COMMAND
# ============================================================================

def pick_site_from_scan(
    ptr_path: str,
    logger: logging.Logger
) -> Tuple[str, int, Optional[float], Optional[str]]:
    """
    Pick best recording site from scan results

    Returns: (host, port, scan_avg, warning_message)
    """
    if not os.path.exists(ptr_path):
        logger.warning(f"No scan file at {ptr_path}, using fallback")
        return (Config.FALLBACK_HOST, Config.FALLBACK_PORT, None, "no-scan-file")

    try:
        with open(ptr_path) as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read scan file: {e}")
        return (Config.FALLBACK_HOST, Config.FALLBACK_PORT, None, f"scan-read-error: {e}")

    top = data.get("top20") or []
    kept = data.get("kept_initial") or []

    if top:
        r = top[0]
        return (r["host"], int(r["port"]), r.get("avg"), None)

    if kept:
        kept.sort(key=lambda r: r["avg"], reverse=True)
        r = kept[0]
        return (r["host"], int(r["port"]), r.get("avg"), "fallback-kept-initial")

    return (Config.FALLBACK_HOST, Config.FALLBACK_PORT, None, "empty-scan")


def make_base_name(
    utc_date: str,
    ampm: str,
    utc_time: str,
    host_short: str,
    rssi: float
) -> str:
    """Generate base filename for recording"""
    rssi_int = int(round(abs(rssi))) if isinstance(rssi, (int, float)) else 999
    return f"ShippingFCST-{utc_date}_{ampm}_{utc_time}UTC--{host_short}--avg-{rssi_int}"


def write_sidecar(
    path_wav: str,
    host: str,
    port: int,
    rssi_label: float,
    ampm: str,
    logger: logging.Logger,
    forecast_html: Optional[str] = None
) -> str:
    """Write sidecar text file with recording metadata and shipping forecast"""
    txt = path_wav.replace(".wav", ".txt")
    now_utc = datetime.now(timezone.utc)
    now_lon = now_utc.astimezone(ZoneInfo("Europe/London"))

    body = (
        "Station recording summary\n"
        f"File : {os.path.basename(path_wav)}\n"
        f"Host : {host}:{port}\n"
        f"Freq : {Config.FREQ_KHZ} kHz, Mode: {Config.MODE}\n"
        f"RSSI : {rssi_label} dBFS (fresh at start)\n"
        f"UTC  : {now_utc.strftime('%Y-%m-%d %H:%M:%S')}Z ({ampm})\n"
        f"LON  : {now_lon.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
        "\n"
        "CREDIT / ORIGIN:\n"
        "  Received via KiwiSDR network (https://kiwisdr.com)\n"
        f"  Receiver host: {host}:{port}\n"
        "Use non-commercially and credit the receiver operator where possible.\n"
    )

    # Add shipping forecast if available
    if forecast_html:
        body += "\n\n" + "="*70 + "\n"
        body += "SHIPPING FORECAST (Met Office)\n"
        body += "="*70 + "\n\n"
        body += forecast_html

    with open(txt, "w", encoding="utf-8") as f:
        f.write(body)

    return txt


def record_audio(
    host: str,
    port: int,
    out_base_no_ext: str,
    logger: logging.Logger
) -> str:
    """
    Record audio from KiwiSDR receiver

    Returns: path to recorded .wav file
    """
    pathlib.Path(Config.OUT_DIR).mkdir(parents=True, exist_ok=True)

    cmd = [
        "python3", Config.KIWI_REC_PATH,
        "-s", host, "-p", str(port),
        "-f", Config.FREQ_KHZ, "-m", Config.MODE,
        "--time-limit", str(Config.DURATION_SEC),
        "--filename", out_base_no_ext
    ]

    logger.info("Recording: " + " ".join(cmd))

    try:
        subprocess.run(
            cmd,
            check=True,
            timeout=Config.DURATION_SEC + Config.RECORDING_TIMEOUT_MARGIN
        )
    except subprocess.TimeoutExpired:
        logger.error("Recording timed out!")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Recording failed: {e}")
        raise

    return out_base_no_ext + ".wav"


def update_latest_symlink(wav_path: str, logger: logging.Logger) -> None:
    """Update latest.wav symlink to point to newest recording"""
    latest = os.path.join(Config.OUT_DIR, "latest.wav")

    try:
        if os.path.lexists(latest):  # lexists catches broken symlinks too
            os.remove(latest)
        os.symlink(os.path.basename(wav_path), latest)
    except Exception as e:
        logger.warning(f"latest.wav symlink not updated: {e}")


def cmd_record(args, logger: logging.Logger) -> int:
    """Execute record command - record from best receiver"""
    logger.info(f"[start] Record @ {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    utc_d, ampm, utc_t = now_parts_with_ampm()
    host, port, scan_avg, why = pick_site_from_scan(Config.SCAN_POINTER, logger)

    if why:
        logger.info(f"Scan note: {why}")

    logger.info(f"Chosen site: {host}:{port} (scan avg: {scan_avg})")

    # Fetch shipping forecast (don't block recording if it fails)
    forecast_html = fetch_shipping_forecast(logger)
    if forecast_html:
        logger.info("Shipping forecast fetched successfully")
    else:
        logger.warning("Recording will proceed without shipping forecast")

    # Get fresh RSSI reading
    fresh_vals, err = probe_smeter(host, port, Config.RSSI_REFRESH_SEC, logger)
    fresh = statistics.mean(fresh_vals) if fresh_vals else None

    rssi_for_label = fresh if fresh is not None else (
        scan_avg if scan_avg is not None else -999.0
    )

    logger.info(f"Fresh RSSI: {fresh} dBFS  |  Using in label: {rssi_for_label} dBFS")

    # Generate filename
    host_short = hostname_short(host)
    base_name = make_base_name(utc_d, ampm, utc_t, host_short, rssi_for_label)
    out_base = os.path.join(Config.OUT_DIR, base_name)

    # Record
    try:
        wav_path = record_audio(host, port, out_base, logger)
        write_sidecar(wav_path, host, port, rssi_for_label, ampm, logger, forecast_html)
        update_latest_symlink(wav_path, logger)
        logger.info(f"Saved: {wav_path}")
    except Exception as e:
        logger.error(f"Recording failed: {e}")
        return 1

    # Post-process recording (fade out anthem)
    try:
        logger.info("[post-process] Detecting and fading out anthem...")
        processed_path = process_recording(
            wav_path,
            fade_duration=3.0,
            logger=logger,
            insert_test_beep=False
        )
        if processed_path:
            logger.info(f"[post-process] Created {processed_path}")
        else:
            logger.warning("[post-process] Processing skipped or failed")
    except Exception as e:
        logger.warning(f"[post-process] Failed: {e}")

    # Rebuild feed
    try:
        cmd_feed(args, logger)
    except Exception as e:
        logger.warning(f"Feed rebuild failed: {e}")

    # Log health info
    now = datetime.now(timezone.utc)
    logger.info(
        f"Health: {now.isoformat(timespec='seconds')}Z | "
        f"London: {now.astimezone(ZoneInfo('Europe/London')).strftime('%Y-%m-%d %H:%M:%S %Z')}"
    )

    return 0


# ============================================================================
# FEED COMMAND
# ============================================================================

def rfc2822(t: float) -> str:
    """Convert Unix timestamp to RFC 2822 format"""
    return email.utils.formatdate(t, usegmt=True)


def list_audio_files() -> List[Tuple[float, str, int]]:
    """Return [(mtime, filename, size)] newest first, limited to MAX_ITEMS.

    Prefers MP3 files over WAV files when both exist with the same basename.
    """
    base_dir = Path(Config.OUT_DIR)
    items = []

    if not base_dir.exists():
        return items

    # First pass: collect all files
    all_files = {}
    for p in base_dir.iterdir():
        if not p.is_file():
            continue
        if not p.name.lower().endswith(Config.AUDIO_EXTS):
            continue

        try:
            st = p.stat()
        except Exception:
            continue

        # Get basename without extension
        basename = p.stem
        ext = p.suffix.lower()

        # Store file info keyed by basename
        if basename not in all_files:
            all_files[basename] = {}

        all_files[basename][ext] = (st.st_mtime, p.name, st.st_size)

    # Second pass: prefer MP3 over WAV for each basename
    for basename, files_dict in all_files.items():
        if '.mp3' in files_dict:
            # Prefer MP3 if it exists
            items.append(files_dict['.mp3'])
        elif '.wav' in files_dict:
            # Fall back to WAV
            items.append(files_dict['.wav'])
        elif '.m4a' in files_dict:
            # Fall back to M4A
            items.append(files_dict['.m4a'])

    items.sort(reverse=True)
    return items[:Config.MAX_FEED_ITEMS]


def guess_mime_type(name: str) -> str:
    """Guess MIME type from filename extension"""
    n = name.lower()
    if n.endswith(".mp3"):
        return "audio/mpeg"
    if n.endswith(".m4a"):
        return "audio/mp4"
    return "audio/wav"


def parse_filename_metadata(name: str) -> Dict[str, Any]:
    """Extract metadata from filename"""
    m = FILENAME_PATTERN.search(name)
    if not m:
        return {}

    yymmdd, ampm, hhmmss, host_short, avg_int = m.groups()
    return {
        "yymmdd": yymmdd,
        "ampm": ampm,
        "hhmmss": hhmmss,
        "host_short": host_short,
        "avg_int": int(avg_int),
    }


def parse_ampm_time_str(name: str) -> str:
    """Return 'AM 05:19 UTC' for titles"""
    d = parse_filename_metadata(name)
    if not d:
        return ""
    hhmm = f"{d['hhmmss'][:2]}:{d['hhmmss'][2:4]}"
    return f"{d['ampm']} {hhmm} UTC"


def read_sidecar_text(audio_name: str) -> Optional[str]:
    """Read sidecar .txt file if present"""
    audio_path = Path(Config.OUT_DIR) / audio_name
    txt_path = audio_path.with_suffix(".txt")

    try:
        if txt_path.exists() and txt_path.is_file():
            return txt_path.read_text(encoding="utf-8")
    except Exception:
        pass

    return None


def make_description(name: str, mtime: float, metadata: Dict[str, Any]) -> str:
    """Build description/summary for feed item"""
    side = read_sidecar_text(name)
    if side:
        return side.strip()

    # Fallback: synthesize from metadata
    ampm_str = parse_ampm_time_str(name) or ""
    host = metadata.get("host_short", "unknown")
    avg = metadata.get("avg_int", "??")

    lines = [
        f"Shipping Forecast – {ampm_str}".strip(),
        f"Receiver host: {host}",
        f"Freq: {Config.FREQ_KHZ} kHz, Mode: {Config.MODE}",
        f"Average RSSI (label): -{avg} dBFS",
        "",
        "CREDIT / ORIGIN:",
        "  Received via KiwiSDR network (https://kiwisdr.com)",
        "  Please credit the receiver operator where possible.",
    ]
    return "\n".join(lines)


def make_feed_item(name: str, size: int, mtime: float) -> str:
    """Generate RSS item XML for a single audio file"""
    url = f"{Config.BASE_URL}/{quote(name)}"
    ctype = guess_mime_type(name)
    guid = html.escape(name)
    pub = rfc2822(mtime)

    # Title
    time_str = parse_ampm_time_str(name)
    base_title = os.path.splitext(name)[0]
    title = f"Shipping Forecast – {time_str}" if time_str else base_title

    # Description
    metadata = parse_filename_metadata(name)
    desc = make_description(name, mtime, metadata)
    desc_xml = html.escape(desc)

    return f"""  <item>
    <title>{html.escape(title)}</title>
    <pubDate>{pub}</pubDate>
    <enclosure url="{url}" length="{size}" type="{ctype}"/>
    <guid isPermaLink="false">{guid}</guid>
    <description>{desc_xml}</description>
    <itunes:summary>{desc_xml}</itunes:summary>
  </item>"""


def cmd_feed(args, logger: logging.Logger) -> int:
    """Execute feed command - rebuild RSS/podcast feed"""
    items = list_audio_files()

    logger.info(f"[make_feed] found {len(items)} audio files")

    if not items:
        logger.warning("[make_feed] no audio files — not writing feed")
        return 1

    art_path = Path(Config.OUT_DIR) / Config.ART_NAME
    art_url = f"{Config.BASE_URL}/{quote(Config.ART_NAME)}" if art_path.exists() else None

    channel_items = "\n".join(make_feed_item(n, s, t) for t, n, s in items)
    now = rfc2822(time.time())

    head = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{html.escape(Config.FEED_TITLE)}</title>
  <link>{Config.BASE_URL}/</link>
  <description>{html.escape(Config.FEED_DESC)}</description>
  <language>{html.escape(Config.FEED_LANG)}</language>
  <lastBuildDate>{now}</lastBuildDate>
  <atom:link rel="self" type="application/rss+xml" href="{Config.BASE_URL}/feed.xml"/>
  <itunes:author>{html.escape(Config.FEED_AUTHOR)}</itunes:author>
  <itunes:summary>{html.escape(Config.FEED_DESC)}</itunes:summary>
  <itunes:category text="News">
    <itunes:category text="Weather"/>
  </itunes:category>
'''

    if art_url:
        head += f"""  <image>
    <url>{art_url}</url>
    <title>{html.escape(Config.FEED_TITLE)}</title>
    <link>{Config.BASE_URL}/</link>
  </image>
  <itunes:image href="{art_url}" />
"""

    tail = "\n</channel>\n</rss>\n"

    xml = head + "\n" + channel_items + tail

    ensure_dir(Config.OUT_DIR)
    Config.FEED_PATH.write_text(xml, encoding="utf-8")

    logger.info(f"[make_feed] wrote {Config.FEED_PATH}")
    return 0


# ============================================================================
# SETUP COMMAND (Cron Configuration)
# ============================================================================

def to_local_hm(lon_time: str) -> Tuple[str, str]:
    """
    Convert London time to local time

    Args:
        lon_time: Time string like "05:19"

    Returns:
        Tuple of (hour, minute) in local time
    """
    import subprocess

    cmd = f'TZ=Europe/London date -d "today {lon_time}" +%s'
    ts = subprocess.check_output(cmd, shell=True, text=True).strip()

    cmd2 = f'date -d "@{ts}" "+%H %M"'
    result = subprocess.check_output(cmd2, shell=True, text=True).strip()

    hour, minute = result.split()
    return hour, minute


def cmd_setup(args, logger: logging.Logger) -> int:
    """Execute setup command - configure cron jobs"""
    logger.info("Setting up cron jobs for automated recording...")

    # Get this script's absolute path
    script_path = os.path.abspath(__file__)

    # Calculate local times for London targets
    lh_rec0, lm_rec0 = to_local_hm("00:47")
    lh_scan0, lm_scan0 = to_local_hm("00:42")  # 5 min before 00:47

    block_start = "# >>> KIWI-SDR AUTO (managed) >>>"
    block_end = "# <<< KIWI-SDR AUTO (managed) <<<"

    # Build managed cron block
    managed_block = f"""{block_start}
# Recompute this block daily just after midnight local:
2 0 * * * /usr/bin/python3 {script_path} setup >> {Config.LOG_FILE} 2>&1

# Scan ~5 min before 00:47 London
{lm_scan0} {lh_scan0} * * * /usr/bin/python3 {script_path} scan >> {Config.LOG_FILE} 2>&1

# Record at 00:47 London
{lm_rec0} {lh_rec0} * * * /usr/bin/python3 {script_path} record >> {Config.LOG_FILE} 2>&1

# Weekly log trim (keep last 20000 lines), Sunday 00:20 local
20 0 * * 0 /bin/bash -c 'tail -n 20000 "{Config.LOG_FILE}" > "{Config.LOG_FILE}.tmp" && mv "{Config.LOG_FILE}.tmp" "{Config.LOG_FILE}"'
{block_end}
"""

    # Get existing crontab
    try:
        existing = subprocess.check_output(
            ["crontab", "-l"],
            stderr=subprocess.DEVNULL,
            text=True
        )
    except subprocess.CalledProcessError:
        existing = ""

    # Remove old managed block
    lines = []
    in_block = False

    for line in existing.splitlines():
        if line.strip() == block_start:
            in_block = True
            continue
        if line.strip() == block_end:
            in_block = False
            continue
        if not in_block:
            lines.append(line)

    # Add new managed block
    new_crontab = "\n".join(lines).strip() + "\n" + managed_block

    # Install new crontab
    proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
    proc.communicate(new_crontab)

    if proc.returncode != 0:
        logger.error("Failed to install crontab")
        return 1

    logger.info(
        f"Crontab updated for London target 00:47. "
        f"Local times -> scan {lh_scan0}:{lm_scan0}, record {lh_rec0}:{lm_rec0}"
    )

    return 0


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point with command dispatch"""
    parser = argparse.ArgumentParser(
        description="KiwiSDR Recorder - Automated radio recording and podcast generation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--log-file',
        default=Config.LOG_FILE,
        help=f'Log file path (default: {Config.LOG_FILE})'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Scan command
    parser_scan = subparsers.add_parser(
        'scan',
        help='Scan KiwiSDR network for best receivers'
    )

    # Record command
    parser_record = subparsers.add_parser(
        'record',
        help='Record from best receiver and update feed'
    )

    # Feed command
    parser_feed = subparsers.add_parser(
        'feed',
        help='Rebuild RSS/podcast feed'
    )

    # Setup command
    parser_setup = subparsers.add_parser(
        'setup',
        help='Configure cron jobs for automated operation'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Setup logging
    logger = setup_logging(args.log_file if args.command != 'setup' else None)

    # Dispatch to appropriate command
    commands = {
        'scan': cmd_scan,
        'record': cmd_record,
        'feed': cmd_feed,
        'setup': cmd_setup,
    }

    try:
        return commands[args.command](args, logger)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
