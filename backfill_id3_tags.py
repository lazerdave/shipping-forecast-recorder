#!/usr/bin/env python3
"""
Backfill ID3 Metadata Tags for Shipping Forecast Archive

Adds ID3 tags to existing MP3 files using information from filenames and sidecar .txt files.
Uses the same metadata generation logic as the main recorder.

Usage:
    python3 backfill_id3_tags.py [--archive-path PATH] [--limit N]
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Import build_id3_metadata from main script
sys.path.insert(0, '/home/pi')
from kiwi_recorder import build_id3_metadata, Config


logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def find_mp3_files(archive_path: str) -> List[str]:
    """
    Find all MP3 files in the archive.

    Args:
        archive_path: Base path to search

    Returns:
        List of MP3 file paths
    """
    mp3_files = []

    for root, dirs, files in os.walk(archive_path):
        for file in files:
            if file.endswith('.mp3'):
                full_path = os.path.join(root, file)
                mp3_files.append(full_path)

    # Sort by filename
    mp3_files.sort()
    return mp3_files


def add_id3_tags(mp3_path: str, dry_run: bool = False) -> bool:
    """
    Add ID3 tags to an MP3 file.

    Args:
        mp3_path: Path to MP3 file
        dry_run: If True, only show what would be done

    Returns:
        True if successful, False otherwise
    """
    try:
        # Build metadata from filename/sidecar
        # We need to find the corresponding WAV to use build_id3_metadata
        # But for MP3s, we can derive from the MP3 path itself
        wav_equivalent = mp3_path.replace('.mp3', '.wav')

        # If the WAV doesn't exist (archive only has MP3), use MP3 path
        if not os.path.exists(wav_equivalent):
            # Create temporary "wav_path" for metadata extraction
            # The function works on filenames, not actual files
            wav_equivalent = mp3_path.replace('.mp3', '.wav')

        metadata = build_id3_metadata(wav_equivalent)

        if dry_run:
            logger.info(f"Would tag: {os.path.basename(mp3_path)}")
            logger.info(f"  Title:   {metadata['title']}")
            logger.info(f"  Artist:  {metadata['artist']}")
            logger.info(f"  Album:   {metadata['album']}")
            logger.info(f"  Date:    {metadata['date']}")
            logger.info(f"  Comment: {metadata['comment'][:60]}...")
            return True

        # Use ffmpeg to add tags (need to re-encode for MP3 metadata)
        # Create temp file with .mp3 extension so ffmpeg recognizes format
        tmp_path = mp3_path.replace('.mp3', '.tmp.mp3')

        cmd = [
            'ffmpeg', '-i', mp3_path,
            '-codec:a', 'libmp3lame',
            '-b:a', '64k',  # Match our recording bitrate
            '-metadata', f'title={metadata["title"]}',
            '-metadata', f'artist={metadata["artist"]}',
            '-metadata', f'album={metadata["album"]}',
            '-metadata', f'date={metadata["date"]}',
            '-metadata', f'comment={metadata["comment"]}',
            '-metadata', f'genre={metadata["genre"]}',
            '-y',  # Overwrite
            tmp_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            # Replace original with tagged version
            os.replace(tmp_path, mp3_path)
            return True
        else:
            logger.error(f"  ffmpeg failed for {os.path.basename(mp3_path)}")
            if result.stderr:
                # Show last 500 chars which usually has the actual error
                logger.error(f"  Error: {result.stderr[-500:]}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return False

    except Exception as e:
        logger.error(f"  Error tagging {os.path.basename(mp3_path)}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Backfill ID3 tags for Shipping Forecast archive')
    parser.add_argument('--archive-path', default='/mnt/rack-shipping',
                        help='Base path to archive (default: /mnt/rack-shipping)')
    parser.add_argument('--limit', type=int, default=0,
                        help='Process only N files (for testing)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without making changes')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("  ID3 Tag Backfill for Shipping Forecast Archive")
    logger.info("=" * 80)
    logger.info(f"Archive path: {args.archive_path}")
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    logger.info("")

    # Find all MP3 files
    logger.info("Scanning for MP3 files...")
    mp3_files = find_mp3_files(args.archive_path)

    if not mp3_files:
        logger.error("No MP3 files found!")
        return 1

    total = len(mp3_files)
    if args.limit > 0:
        mp3_files = mp3_files[:args.limit]
        logger.info(f"Found {total} MP3 files (processing first {args.limit})")
    else:
        logger.info(f"Found {total} MP3 files")

    logger.info("")
    logger.info("─" * 80)

    # Process files
    success_count = 0
    error_count = 0

    for i, mp3_path in enumerate(mp3_files, 1):
        logger.info(f"[{i:3d}/{len(mp3_files)}] {os.path.basename(mp3_path)}")

        if add_id3_tags(mp3_path, dry_run=args.dry_run):
            success_count += 1
            if not args.dry_run:
                logger.info("  ✓ Tagged")
        else:
            error_count += 1

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("  SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total files:    {len(mp3_files)}")
    logger.info(f"Successfully tagged: {success_count}")
    logger.info(f"Errors:         {error_count}")
    logger.info("=" * 80)

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
