#!/usr/bin/env python3
"""
Identify Presenters in Archive Using Voiceprint Matching

Processes archive recordings without presenter identification and attempts
to identify them using the voiceprint database.

Usage:
    python3 identify_archive_presenters.py [--archive-path PATH] [--limit N]
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import from main script
sys.path.insert(0, '/home/pi')
from kiwi_recorder import Config


logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def find_recordings_without_presenter(archive_path: str) -> List[Tuple[str, str]]:
    """
    Find recordings that don't have presenter information.

    Args:
        archive_path: Base path to search

    Returns:
        List of (mp3_path, txt_path) tuples for recordings without presenters
    """
    candidates = []

    for root, dirs, files in os.walk(archive_path):
        for file in files:
            if file.endswith('.mp3'):
                mp3_path = os.path.join(root, file)

                # Find corresponding txt file
                txt_path = mp3_path.replace('_processed.mp3', '.txt').replace('.mp3', '.txt')

                if not os.path.exists(txt_path):
                    continue

                # Check if presenter is already identified
                try:
                    with open(txt_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                        # Skip if already has presenter
                        if re.search(r'^Presenter:\s*\w+', content, re.MULTILINE):
                            presenter = re.search(r'^Presenter:\s*(.+)$', content, re.MULTILINE)
                            if presenter and presenter.group(1).strip().lower() not in ['not detected', '']:
                                continue

                        # Include if no presenter or unknown presenter
                        candidates.append((mp3_path, txt_path))

                except Exception as e:
                    logger.warning(f"Error reading {txt_path}: {e}")

    candidates.sort()
    return candidates


def extract_audio_segment(mp3_path: str, duration: float = 45.0) -> Optional[str]:
    """
    Extract final audio segment for voiceprint matching.

    Args:
        mp3_path: Path to MP3 file
        duration: Duration to extract in seconds (default: 45s from end)

    Returns:
        Path to temporary WAV file, or None if failed
    """
    try:
        # Get audio duration
        duration_cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            mp3_path
        ]

        result = subprocess.run(
            duration_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        total_duration = float(result.stdout.strip())
        start_time = max(0, total_duration - duration)

        # Extract segment to temporary WAV
        tmp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tmp_wav.close()

        extract_cmd = [
            'ffmpeg', '-i', mp3_path,
            '-ss', str(start_time),
            '-t', str(duration),
            '-ar', '16000',  # 16kHz for voiceprint
            '-ac', '1',  # Mono
            '-y',
            tmp_wav.name
        ]

        result = subprocess.run(
            extract_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30
        )

        if result.returncode == 0:
            return tmp_wav.name
        else:
            os.unlink(tmp_wav.name)
            return None

    except Exception as e:
        logger.debug(f"Error extracting segment: {e}")
        return None


def match_voiceprint(wav_path: str) -> Optional[Dict]:
    """
    Match audio against voiceprint database.

    Args:
        wav_path: Path to WAV file

    Returns:
        Dict with match results, or None if failed
    """
    try:
        # Copy audio to Rack
        remote_path = f"/tmp/voiceprint_query_{os.getpid()}.wav"
        scp_cmd = ['scp', '-q', wav_path, f'{Config.RACK_SSH_HOST}:{remote_path}']

        result = subprocess.run(scp_cmd, capture_output=True, timeout=30)
        if result.returncode != 0:
            return None

        # Run voiceprint comparison
        compare_cmd = [
            'ssh', Config.RACK_SSH_HOST,
            f'python3 /usr/local/bin/speaker_recognition.py compare {remote_path} {Config.VOICEPRINT_DATABASE}'
        ]

        result = subprocess.run(
            compare_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Cleanup remote file
        subprocess.run(
            ['ssh', Config.RACK_SSH_HOST, f'rm -f {remote_path}'],
            capture_output=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        # Parse JSON result
        match_result = json.loads(result.stdout)
        return match_result

    except Exception as e:
        logger.debug(f"Voiceprint matching error: {e}")
        return None


def update_sidecar_with_voiceprint(txt_path: str, match_result: Dict) -> bool:
    """
    Update sidecar file with voiceprint match results.

    Args:
        txt_path: Path to sidecar .txt file
        match_result: Dict from voiceprint matching

    Returns:
        True if updated successfully
    """
    try:
        if not os.path.exists(txt_path):
            return False

        # Read existing content
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Build presenter section
        presenter_section = "\n" + "="*70 + "\n"
        presenter_section += "PRESENTER\n"
        presenter_section += "="*70 + "\n\n"

        if match_result.get('matches') and len(match_result['matches']) > 0:
            best_match = match_result['matches'][0]
            presenter_section += f"Presenter: {best_match['name']}\n"
            presenter_section += f"Confidence: {best_match['similarity']:.2f}\n"
            presenter_section += f"Match type: voiceprint\n"
            presenter_section += f"Detection method: Voiceprint matching from archive\n"
        else:
            presenter_section += "Presenter: Not detected\n"
            presenter_section += "Status: voiceprint_no_match\n"

        # Insert presenter section before shipping forecast or at end
        forecast_marker = "="*70 + "\nSHIPPING FORECAST"
        if forecast_marker in content:
            content = content.replace(forecast_marker, presenter_section + "\n" + forecast_marker)
        else:
            content += presenter_section

        # Write back
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return True

    except Exception as e:
        logger.warning(f"Failed to update sidecar: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Identify archive presenters using voiceprint matching')
    parser.add_argument('--archive-path', default='/mnt/rack-shipping',
                        help='Base path to archive (default: /mnt/rack-shipping)')
    parser.add_argument('--limit', type=int, default=0,
                        help='Process only N files (for testing)')
    parser.add_argument('--min-confidence', type=float, default=0.70,
                        help='Minimum confidence threshold (default: 0.70)')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("  Archive Presenter Identification via Voiceprint Matching")
    logger.info("=" * 80)
    logger.info(f"Archive path: {args.archive_path}")
    logger.info(f"Voiceprint database: {Config.VOICEPRINT_DATABASE}")
    logger.info(f"Minimum confidence: {args.min_confidence}")
    logger.info("")

    # Find candidates
    logger.info("Scanning for recordings without presenter info...")
    candidates = find_recordings_without_presenter(args.archive_path)

    if not candidates:
        logger.info("No recordings need processing!")
        return 0

    total = len(candidates)
    if args.limit > 0:
        candidates = candidates[:args.limit]
        logger.info(f"Found {total} candidates (processing first {args.limit})")
    else:
        logger.info(f"Found {total} candidates")

    logger.info("")
    logger.info("─" * 80)

    # Process recordings
    identified_count = 0
    low_confidence_count = 0
    error_count = 0

    for i, (mp3_path, txt_path) in enumerate(candidates, 1):
        basename = os.path.basename(mp3_path)
        logger.info(f"[{i:3d}/{len(candidates)}] {basename}")

        # Extract audio segment
        wav_path = extract_audio_segment(mp3_path)
        if not wav_path:
            logger.info("  ✗ Failed to extract audio")
            error_count += 1
            continue

        # Match voiceprint
        match_result = match_voiceprint(wav_path)
        os.unlink(wav_path)  # Cleanup temp file

        if not match_result or not match_result.get('matches'):
            logger.info("  ✗ No voiceprint match")
            error_count += 1
            continue

        best_match = match_result['matches'][0]
        confidence = best_match['similarity']

        if confidence >= args.min_confidence:
            logger.info(f"  ✓ {best_match['name']} (confidence: {confidence:.2f})")
            identified_count += 1

            # Update sidecar
            if update_sidecar_with_voiceprint(txt_path, match_result):
                logger.info("    Updated sidecar file")
        else:
            logger.info(f"  ~ Low confidence: {best_match['name']} ({confidence:.2f})")
            low_confidence_count += 1

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("  SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total processed: {len(candidates)}")
    logger.info(f"Identified:      {identified_count}")
    logger.info(f"Low confidence:  {low_confidence_count}")
    logger.info(f"Errors/No match: {error_count}")
    logger.info("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
