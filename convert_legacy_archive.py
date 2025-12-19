#!/usr/bin/env python3
"""
Convert Legacy Archive - Migrate old MP4 files to new ShippingFCST format

This script:
1. Finds all old Shipping_Forecast_*.mp4 files
2. Extracts audio to WAV
3. Renames to ShippingFCST format
4. Runs anthem detection and processing
5. Converts to MP3
6. Generates metadata sidecar files

Usage:
    python3 convert_legacy_archive.py [--dry-run] [--limit N]

Options:
    --dry-run   Show what would be done without actually doing it
    --limit N   Process only N files (for testing)
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

# Import processing functions from kiwi_recorder
sys.path.insert(0, '/home/pi')
from kiwi_recorder import (
    Config,
    detect_anthem_start,
    process_recording,
    convert_to_mp3,
    detect_presenter,
    update_sidecar_with_presenter,
    setup_logging
)

# Patterns for old filenames
# Format 1: Shipping_Forecast_2024-09-15_18-19-53.mp4 (has seconds)
OLD_FILENAME_PATTERN_1 = re.compile(
    r'Shipping_Forecast_(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})\.mp4'
)
# Format 2: Shipping_Forecast_2025-01-06__19-00_m0026nkv.mp4 (double underscore, no seconds, BBC ID)
OLD_FILENAME_PATTERN_2 = re.compile(
    r'Shipping_Forecast_(\d{4})-(\d{2})-(\d{2})__(\d{2})-(\d{2})_m[a-z0-9]+\.mp4'
)


def parse_old_filename(filename: str) -> Optional[dict]:
    """
    Parse old MP4 filename to extract timestamp.

    Args:
        filename: e.g., "Shipping_Forecast_2024-09-15_18-19-53.mp4"
                  or   "Shipping_Forecast_2025-01-06__19-00_m0026nkv.mp4"

    Returns:
        Dict with parsed fields or None if doesn't match
    """
    # Try format 1 (with seconds)
    match = OLD_FILENAME_PATTERN_1.match(filename)
    if match:
        year, month, day, hour, minute, second = match.groups()
        return {
            'year': year,
            'month': month,
            'day': day,
            'hour': hour,
            'minute': minute,
            'second': second,
            'datetime': f"{year}-{month}-{day} {hour}:{minute}:{second}"
        }

    # Try format 2 (without seconds, assume :00)
    match = OLD_FILENAME_PATTERN_2.match(filename)
    if match:
        year, month, day, hour, minute = match.groups()
        return {
            'year': year,
            'month': month,
            'day': day,
            'hour': hour,
            'minute': minute,
            'second': '00',  # No seconds in filename, assume :00
            'datetime': f"{year}-{month}-{day} {hour}:{minute}:00"
        }

    return None


def determine_utc_time(local_time_str: str, logger: logging.Logger) -> Tuple[str, str, str]:
    """
    Convert local timestamp to UTC and determine AM/PM.

    The old recordings were in UK local time (GMT/BST).
    Shipping Forecast broadcasts at 00:48 UTC.

    Args:
        local_time_str: "YYYY-MM-DD HH:MM:SS" in local time
        logger: Logger instance

    Returns:
        Tuple of (yymmdd, ampm, hhmmss) in UTC
    """
    # Parse local time
    dt_local = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M:%S")

    # Assume UK timezone (GMT/BST)
    # For simplicity, we'll convert by checking if we're in BST period
    # BST runs from last Sunday in March to last Sunday in October
    year = dt_local.year

    # Simple BST check (approximate - good enough for our purposes)
    if dt_local.month >= 4 and dt_local.month <= 9:
        # Definitely BST (UTC+1)
        offset_hours = -1
    elif dt_local.month == 3:
        # Maybe BST (starts last Sunday of March)
        offset_hours = -1 if dt_local.day >= 25 else 0
    elif dt_local.month == 10:
        # Maybe BST (ends last Sunday of October)
        offset_hours = -1 if dt_local.day < 25 else 0
    else:
        # Winter (GMT = UTC)
        offset_hours = 0

    # Convert to UTC
    import datetime as dt_module
    utc_time = dt_local - dt_module.timedelta(hours=offset_hours)

    # Format for new filename
    yymmdd = utc_time.strftime("%y%m%d")
    ampm = utc_time.strftime("%p")
    hhmmss = utc_time.strftime("%H%M%S")

    logger.debug(f"Converted {local_time_str} (offset {offset_hours}h) → {utc_time.strftime('%Y-%m-%d %H:%M:%S')} UTC ({ampm})")

    return yymmdd, ampm, hhmmss


def convert_single_file(
    mp4_path: Path,
    output_dir: Path,
    dry_run: bool,
    logger: logging.Logger
) -> bool:
    """
    Convert a single MP4 file to new format.

    Args:
        mp4_path: Path to old MP4 file
        output_dir: Output directory for converted files
        dry_run: If True, don't actually convert
        logger: Logger instance

    Returns:
        True if successful
    """
    filename = mp4_path.name

    # Parse old filename
    parsed = parse_old_filename(filename)
    if not parsed:
        logger.warning(f"Skipping {filename} - doesn't match expected pattern")
        return False

    # Determine UTC time
    yymmdd, ampm, hhmmss = determine_utc_time(parsed['datetime'], logger)

    # Build new filename (without host/RSSI since we don't have that info for old files)
    new_base = f"ShippingFCST-{yymmdd}_{ampm}_{hhmmss}UTC--legacy--avg-99"
    wav_path = output_dir / f"{new_base}.wav"
    processed_path = output_dir / f"{new_base}_processed.wav"
    mp3_path = output_dir / f"{new_base}_processed.mp3"
    txt_path = output_dir / f"{new_base}.txt"

    # Check if already converted (skip if MP3 exists)
    if mp3_path.exists():
        logger.info(f"  ✓ Already converted - skipping")
        return True

    logger.info(f"Converting: {filename}")
    logger.info(f"  → {wav_path.name}")

    if dry_run:
        logger.info(f"  [DRY RUN] Would extract audio and process")
        return True

    try:
        # Extract audio from MP4 to WAV
        logger.info(f"  Extracting audio...")
        extract_cmd = [
            'ffmpeg', '-i', str(mp4_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '12000',  # Standard KiwiSDR sample rate
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            str(wav_path)
        ]
        result = subprocess.run(
            extract_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120
        )

        if result.returncode != 0:
            logger.error(f"  Failed to extract audio")
            return False

        logger.info(f"  Extracted to WAV")

        # Process recording (anthem detection + fade)
        logger.info(f"  Processing (anthem detection + fade)...")
        processed = process_recording(
            str(wav_path),
            fade_duration=10.0,
            logger=logger,
            insert_test_beep=False
        )

        if not processed:
            logger.warning(f"  Processing failed/skipped - keeping unprocessed WAV")
            processed = str(wav_path)
        else:
            logger.info(f"  Processed")

        # Convert to MP3
        logger.info(f"  Converting to MP3...")
        mp3 = convert_to_mp3(processed, logger)
        if mp3:
            logger.info(f"  Converted to MP3")

        # Detect presenter
        logger.info(f"  Detecting presenter...")
        presenter_result = detect_presenter(processed, logger)

        # Write sidecar file
        logger.info(f"  Writing metadata...")
        with open(txt_path, 'w') as f:
            f.write("Legacy Recording (converted from MP4)\n")
            f.write(f"Original file: {filename}\n")
            f.write(f"Original timestamp: {parsed['datetime']} (UK local time)\n")
            f.write(f"UTC timestamp: 20{yymmdd} {hhmmss[:2]}:{hhmmss[2:4]}:{hhmmss[4:]} ({ampm})\n")
            f.write(f"\nSource: Legacy archive (pre-KiwiSDR system)\n")
            f.write(f"Note: No receiver host or RSSI data available for legacy recordings\n")

        # Add presenter info to sidecar
        if presenter_result:
            update_sidecar_with_presenter(str(txt_path), presenter_result, logger)

        logger.info(f"  ✓ Complete")
        return True

    except subprocess.TimeoutExpired:
        logger.error(f"  Timeout during conversion")
        return False
    except Exception as e:
        logger.error(f"  Conversion failed: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Convert legacy MP4 archive to new ShippingFCST format",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--archive-path",
        default="/mnt/rack-shipping",
        help="Base path to archive (default: /mnt/rack-shipping)"
    )

    parser.add_argument(
        "--output-path",
        default="/mnt/rack-shipping",
        help="Output path (default: same as archive-path, preserves YYYY/MM structure)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Process only N files (for testing)"
    )

    parser.add_argument(
        "--year",
        help="Process only files from this year"
    )

    parser.add_argument(
        "--month",
        help="Process only files from this month (requires --year)"
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(None)

    logger.info("=" * 80)
    logger.info("  Legacy Archive Converter")
    logger.info("=" * 80)
    logger.info(f"Archive path: {args.archive_path}")
    logger.info(f"Output path: {args.output_path}")
    if args.dry_run:
        logger.info("DRY RUN MODE - no files will be modified")
    if args.limit:
        logger.info(f"Limit: {args.limit} files")
    logger.info("")

    # Find all old MP4 files
    archive_path = Path(args.archive_path)

    if args.year:
        if args.month:
            search_pattern = str(archive_path / args.year / args.month / "Shipping_Forecast_*.mp4")
        else:
            search_pattern = str(archive_path / args.year / "**" / "Shipping_Forecast_*.mp4")
    else:
        search_pattern = str(archive_path / "**" / "Shipping_Forecast_*.mp4")

    import glob
    mp4_files = [Path(p) for p in glob.glob(search_pattern, recursive=True)]
    mp4_files.sort()

    if args.limit:
        mp4_files = mp4_files[:args.limit]

    if not mp4_files:
        logger.warning("No MP4 files found matching criteria")
        return 1

    logger.info(f"Found {len(mp4_files)} MP4 files to convert")
    logger.info("─" * 80)
    logger.info("")

    # Convert each file
    success_count = 0
    fail_count = 0

    for i, mp4_path in enumerate(mp4_files, 1):
        logger.info(f"[{i:3d}/{len(mp4_files)}] {mp4_path.name}")

        # Determine output directory (preserve YYYY/MM structure)
        # Extract year/month from filename
        parsed = parse_old_filename(mp4_path.name)
        if not parsed:
            logger.warning(f"  Skipping - invalid filename format")
            fail_count += 1
            continue

        output_dir = Path(args.output_path) / parsed['year'] / parsed['month']

        # Create output directory if needed
        if not args.dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)

        # Convert
        success = convert_single_file(mp4_path, output_dir, args.dry_run, logger)

        if success:
            success_count += 1
        else:
            fail_count += 1

        logger.info("")

    # Summary
    logger.info("=" * 80)
    logger.info("  CONVERSION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total files: {len(mp4_files)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info("=" * 80)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
