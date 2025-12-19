#!/usr/bin/env python3
"""
Analyze Archive - Scan existing Shipping Forecast recordings for presenter detection

This script:
1. Scans /mnt/rack-shipping/ for all MP3 recordings
2. Runs existing presenter detection on each
3. Generates a report of:
   - How many recordings per presenter
   - How many unknowns/failures
   - Which recordings are high-confidence (suitable for training)
4. Outputs presenter_labels.json for building voiceprint database

Usage:
    python3 analyze_archive.py [--limit N] [--year YYYY] [--month MM]

Options:
    --limit N       Process only N files (for testing)
    --year YYYY     Process only recordings from year YYYY
    --month MM      Process only recordings from month MM (requires --year)
    --output PATH   Output JSON file (default: presenter_labels.json)
"""

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import presenter detection functions from kiwi_recorder
sys.path.insert(0, '/home/pi')
from kiwi_recorder import (
    Config,
    detect_presenter,
    load_presenters,
    setup_logging
)


def find_recordings(
    base_path: str,
    year: Optional[str] = None,
    month: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Path]:
    """
    Find all MP3 recordings in archive.

    Args:
        base_path: Base archive path (e.g., /mnt/rack-shipping)
        year: Optional year filter (e.g., "2025")
        month: Optional month filter (e.g., "12")
        limit: Optional limit on number of files

    Returns:
        List of Path objects for MP3 files
    """
    base = Path(base_path)

    if not base.exists():
        raise FileNotFoundError(f"Archive path not found: {base_path}")

    recordings = []

    # If year/month specified, search specific path
    if year:
        if month:
            search_path = base / year / month
            if search_path.exists():
                recordings.extend(search_path.glob("*.mp3"))
        else:
            year_path = base / year
            if year_path.exists():
                for month_dir in sorted(year_path.iterdir()):
                    if month_dir.is_dir():
                        recordings.extend(month_dir.glob("*.mp3"))
    else:
        # Search all years and months
        for year_dir in sorted(base.iterdir()):
            if year_dir.is_dir() and year_dir.name.isdigit():
                for month_dir in sorted(year_dir.iterdir()):
                    if month_dir.is_dir() and month_dir.name.isdigit():
                        recordings.extend(month_dir.glob("*.mp3"))

    # Sort by modification time (newest first)
    recordings.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    if limit:
        recordings = recordings[:limit]

    return recordings


def analyze_single_recording(
    mp3_path: Path,
    index: int,
    total: int,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Analyze a single recording for presenter detection.

    Args:
        mp3_path: Path to MP3 file
        index: Current file index (for progress display)
        total: Total number of files
        logger: Logger instance

    Returns:
        Dict with analysis results
    """
    logger.info(f"[{index:4d}/{total}] {mp3_path.name[:60]:60s} ", extra={'end': ''})

    result = {
        "file": str(mp3_path),
        "filename": mp3_path.name,
        "year": mp3_path.parent.parent.name,
        "month": mp3_path.parent.name,
        "timestamp": datetime.fromtimestamp(mp3_path.stat().st_mtime).isoformat(),
    }

    try:
        # Convert MP3 to temporary WAV for processing
        # (detect_presenter expects WAV, but we can work around this)
        import tempfile
        import subprocess

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_wav = tmp.name

        # Convert to WAV
        convert_cmd = [
            "ffmpeg", "-y", "-i", str(mp3_path),
            "-ar", "12000",  # Standard KiwiSDR sample rate
            "-ac", "1",      # Mono
            tmp_wav
        ]
        subprocess.run(convert_cmd, capture_output=True, check=True, timeout=60)

        # Run presenter detection
        presenter_result = detect_presenter(tmp_wav, logger)

        # Clean up temp file
        os.unlink(tmp_wav)

        # Extract key fields
        result["presenter"] = presenter_result.get("presenter")
        result["raw_match"] = presenter_result.get("raw_match")
        result["confidence"] = presenter_result.get("confidence", 0.0)
        result["match_type"] = presenter_result.get("match_type", "error")
        result["transcript"] = presenter_result.get("transcript")

        # Determine suitability for training
        result["suitable_for_training"] = (
            result["presenter"] is not None and
            result["confidence"] >= 0.8 and
            result["match_type"] in ("exact", "variation", "llm_validated")
        )

        # Log result
        if result["presenter"]:
            logger.info(f"✓ {result['presenter']:20s} (conf: {result['confidence']:.2f}, {result['match_type']})")
        elif result["raw_match"]:
            logger.info(f"✗ Unknown: {result['raw_match']:20s}")
        else:
            logger.info(f"✗ No detection ({result['match_type']})")

    except subprocess.TimeoutExpired:
        logger.info("✗ TIMEOUT")
        result["presenter"] = None
        result["match_type"] = "timeout"
        result["suitable_for_training"] = False
    except Exception as e:
        logger.info(f"✗ ERROR: {str(e)[:40]}")
        result["presenter"] = None
        result["match_type"] = "error"
        result["error"] = str(e)
        result["suitable_for_training"] = False

    return result


def generate_summary_report(results: List[Dict[str, Any]], logger: logging.Logger) -> Dict[str, Any]:
    """Generate summary statistics from analysis results."""

    # Count by presenter
    by_presenter = {}
    by_match_type = {}
    suitable_by_presenter = {}
    unknowns = []
    errors = []

    for result in results:
        # Count by presenter
        presenter = result.get("presenter") or "NONE"
        by_presenter[presenter] = by_presenter.get(presenter, 0) + 1

        # Count by match type
        match_type = result.get("match_type", "unknown")
        by_match_type[match_type] = by_match_type.get(match_type, 0) + 1

        # Count suitable for training
        if result.get("suitable_for_training"):
            suitable_by_presenter[presenter] = suitable_by_presenter.get(presenter, 0) + 1

        # Collect unknowns
        if result.get("raw_match") and not result.get("presenter"):
            unknowns.append({
                "filename": result["filename"],
                "raw_match": result["raw_match"],
                "transcript": result.get("transcript", "")[:100]
            })

        # Collect errors
        if result.get("match_type") in ("error", "timeout", "transcription_error"):
            errors.append({
                "filename": result["filename"],
                "match_type": result["match_type"],
                "error": result.get("error", "")
            })

    summary = {
        "total_analyzed": len(results),
        "by_presenter": dict(sorted(by_presenter.items(), key=lambda x: x[1], reverse=True)),
        "by_match_type": dict(sorted(by_match_type.items(), key=lambda x: x[1], reverse=True)),
        "suitable_for_training": {
            "total": sum(suitable_by_presenter.values()),
            "by_presenter": dict(sorted(suitable_by_presenter.items(), key=lambda x: x[1], reverse=True))
        },
        "unknowns": unknowns,
        "errors": errors
    }

    # Print summary to console
    logger.info("\n" + "=" * 80)
    logger.info("  ANALYSIS SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total recordings analyzed: {summary['total_analyzed']}")
    logger.info("")

    logger.info("Recordings by presenter:")
    for presenter, count in summary["by_presenter"].items():
        if presenter == "NONE" or presenter is None:
            logger.info(f"  (No presenter detected): {count}")
        else:
            logger.info(f"  {presenter:30s}: {count}")
    logger.info("")

    logger.info("Suitable for training:")
    logger.info(f"  Total: {summary['suitable_for_training']['total']}")
    for presenter, count in summary["suitable_for_training"]["by_presenter"].items():
        logger.info(f"  {presenter:30s}: {count}")
    logger.info("")

    logger.info("Match types:")
    for match_type, count in summary["by_match_type"].items():
        logger.info(f"  {match_type:30s}: {count}")
    logger.info("")

    if unknowns:
        logger.info(f"Unknown presenters detected: {len(unknowns)}")
        logger.info("  (These may be new presenters to add to the database)")
        for u in unknowns[:5]:
            logger.info(f"  - {u['filename']}: {u['raw_match']}")
        if len(unknowns) > 5:
            logger.info(f"  ... and {len(unknowns) - 5} more")
        logger.info("")

    if errors:
        logger.info(f"Errors/timeouts: {len(errors)}")
        logger.info("")

    logger.info("=" * 80)

    return summary


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Analyze Shipping Forecast archive for presenter detection",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--archive-path",
        default="/mnt/rack-shipping",
        help="Base path to archive (default: /mnt/rack-shipping)"
    )

    parser.add_argument(
        "--year",
        help="Process only recordings from this year (e.g., 2025)"
    )

    parser.add_argument(
        "--month",
        help="Process only recordings from this month (e.g., 12, requires --year)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Process only N files (for testing)"
    )

    parser.add_argument(
        "--output",
        default="presenter_labels.json",
        help="Output JSON file (default: presenter_labels.json)"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1, sequential processing)"
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(None)

    logger.info("=" * 80)
    logger.info("  Shipping Forecast Archive Analyzer")
    logger.info("=" * 80)
    logger.info(f"Archive path: {args.archive_path}")
    if args.year:
        logger.info(f"Year filter: {args.year}")
    if args.month:
        logger.info(f"Month filter: {args.month}")
    if args.limit:
        logger.info(f"Limit: {args.limit} files")
    logger.info("")

    # Find recordings
    try:
        recordings = find_recordings(
            args.archive_path,
            year=args.year,
            month=args.month,
            limit=args.limit
        )
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1

    if not recordings:
        logger.warning("No recordings found matching criteria")
        return 1

    logger.info(f"Found {len(recordings)} recordings to analyze")
    logger.info("─" * 80)
    logger.info("")

    # Analyze recordings
    results = []

    if args.workers > 1:
        # Parallel processing
        logger.info(f"Processing with {args.workers} parallel workers...")
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(analyze_single_recording, rec, i+1, len(recordings), logger): rec
                for i, rec in enumerate(recordings)
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Analysis error: {e}")
    else:
        # Sequential processing (easier to follow)
        for i, rec in enumerate(recordings, 1):
            result = analyze_single_recording(rec, i, len(recordings), logger)
            results.append(result)

    # Generate summary
    summary = generate_summary_report(results, logger)

    # Save results
    output_data = {
        "analyzed_at": datetime.now().isoformat(),
        "archive_path": args.archive_path,
        "filters": {
            "year": args.year,
            "month": args.month,
            "limit": args.limit
        },
        "summary": summary,
        "results": results
    }

    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"Results saved to: {output_path}")
    logger.info("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
