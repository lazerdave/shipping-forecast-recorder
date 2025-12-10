#!/usr/bin/env python3
"""
Sync existing recordings to Rack backup and Internet Archive.

Checks destinations before copying/uploading to avoid duplicates.
Does not re-process files - uploads as-is.
"""

import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Configuration
LOCAL_DIR = "/home/pi/share/198k"
RACK_BASE = "/mnt/rack-shipping"


def extract_date_from_filename(filename: str) -> tuple:
    """Extract year, month, day from filename like ShippingFCST-YYMMDD_..."""
    match = re.search(r'ShippingFCST-(\d{2})(\d{2})(\d{2})_', filename)
    if match:
        yy, mm, dd = match.groups()
        return f"20{yy}", mm, dd
    return None, None, None


def extract_datetime_for_ia(filename: str) -> tuple:
    """Extract date and time for IA identifier from filename."""
    match = re.search(r'ShippingFCST-(\d{2})(\d{2})(\d{2})_[AP]M_(\d{2})(\d{2})', filename)
    if match:
        yy, mm, dd, hh, mi = match.groups()
        year = f"20{yy}"
        date_str = f"{year}-{mm}-{dd}"
        time_str = f"{hh}:{mi}"
        identifier = f"shipping-forecast-{year}-{mm}-{dd}-{hh}{mi}"
        return identifier, date_str, time_str
    return None, None, None


def check_rack_exists(filename: str) -> bool:
    """Check if file already exists on Rack."""
    year, month, _ = extract_date_from_filename(filename)
    if not year:
        return False
    rack_path = Path(RACK_BASE) / year / month / filename
    return rack_path.exists()


def check_ia_exists(identifier: str) -> bool:
    """Check if item already exists on Internet Archive."""
    try:
        import internetarchive as ia
        item = ia.get_item(identifier)
        return item.exists
    except Exception as e:
        print(f"  Warning: Could not check IA for {identifier}: {e}")
        return False


def backup_to_rack(src_path: str, dry_run: bool = False) -> bool:
    """Copy file to Rack with YYYY/MM structure."""
    filename = os.path.basename(src_path)
    year, month, _ = extract_date_from_filename(filename)

    if not year:
        print(f"  Skipping {filename} - cannot extract date")
        return False

    target_dir = Path(RACK_BASE) / year / month
    target_path = target_dir / filename

    if target_path.exists():
        print(f"  Already on Rack: {filename}")
        return True

    if dry_run:
        print(f"  Would copy to: {target_path}")
        return True

    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, target_path)

    if target_path.exists():
        print(f"  Backed up: {filename}")
        return True
    else:
        print(f"  FAILED: {filename}")
        return False


def upload_to_ia(mp3_path: str, dry_run: bool = False) -> bool:
    """Upload file to Internet Archive."""
    try:
        import internetarchive as ia
    except ImportError:
        print("  Error: internetarchive not installed")
        return False

    filename = os.path.basename(mp3_path)
    identifier, date_str, time_str = extract_datetime_for_ia(filename)

    if not identifier:
        print(f"  Skipping {filename} - cannot extract date/time")
        return False

    # Check if already exists
    try:
        item = ia.get_item(identifier)
        if item.exists:
            print(f"  Already on IA: {identifier}")
            return True
    except Exception as e:
        print(f"  Warning checking IA: {e}")

    if dry_run:
        print(f"  Would upload as: {identifier}")
        return True

    # Build metadata (no collection - uses personal uploads)
    metadata = {
        "title": f"BBC Shipping Forecast - {date_str} {time_str} UTC",
        "date": date_str,
        "mediatype": "audio",
        "language": "eng",
        "creator": "BBC Radio 4",
        "subject": ["BBC", "Shipping Forecast", "Radio 4", "198 kHz", "Maritime Weather", "Longwave"],
        "description": (
            f"BBC Radio 4 Shipping Forecast broadcast on {date_str} at {time_str} UTC. "
            "Recorded from 198 kHz longwave transmission via KiwiSDR network."
        ),
        "licenseurl": "https://creativecommons.org/licenses/by-nc-sa/4.0/"
    }

    print(f"  Uploading: {identifier}...")

    try:
        item = ia.get_item(identifier)
        responses = item.upload(
            mp3_path,
            metadata=metadata,
            verify=True,
            retries=3,
            retries_sleep=10
        )

        if responses and len(responses) > 0:
            response = responses[0]
            if hasattr(response, 'status_code') and response.status_code == 200:
                print(f"  Uploaded: https://archive.org/details/{identifier}")
                return True

        print(f"  Upload may have failed for {identifier}")
        return False

    except Exception as e:
        print(f"  Upload error: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sync recordings to Rack and Internet Archive")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    parser.add_argument("--rack-only", action="store_true", help="Only backup to Rack, skip IA upload")
    parser.add_argument("--ia-only", action="store_true", help="Only upload to IA, skip Rack backup")
    args = parser.parse_args()

    # Check Rack is mounted
    if not args.ia_only and not os.path.ismount(RACK_BASE):
        print(f"Error: Rack not mounted at {RACK_BASE}")
        sys.exit(1)

    # Find all MP3 files
    mp3_files = sorted(Path(LOCAL_DIR).glob("*_processed.mp3"))
    wav_files = sorted(Path(LOCAL_DIR).glob("*_processed.wav"))

    print(f"Found {len(mp3_files)} MP3 files and {len(wav_files)} WAV files")
    print(f"Dry run: {args.dry_run}")
    print("=" * 60)

    rack_success = 0
    rack_skip = 0
    ia_success = 0
    ia_skip = 0

    # Process each MP3 file
    for mp3_path in mp3_files:
        print(f"\n{mp3_path.name}")

        # Find corresponding WAV
        wav_path = str(mp3_path).replace('.mp3', '.wav')

        # Backup to Rack
        if not args.ia_only:
            # Backup MP3
            if backup_to_rack(str(mp3_path), args.dry_run):
                if check_rack_exists(mp3_path.name):
                    rack_skip += 1
                else:
                    rack_success += 1

            # Backup WAV if exists
            if os.path.exists(wav_path):
                backup_to_rack(wav_path, args.dry_run)

        # Upload to IA
        if not args.rack_only:
            identifier, _, _ = extract_datetime_for_ia(mp3_path.name)
            if identifier:
                try:
                    import internetarchive as ia
                    item = ia.get_item(identifier)
                    if item.exists:
                        print(f"  Already on IA: {identifier}")
                        ia_skip += 1
                    elif upload_to_ia(str(mp3_path), args.dry_run):
                        ia_success += 1
                except Exception as e:
                    print(f"  IA check failed: {e}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  Rack: {rack_success} backed up, {rack_skip} already existed")
    print(f"  IA:   {ia_success} uploaded, {ia_skip} already existed")


if __name__ == "__main__":
    main()
