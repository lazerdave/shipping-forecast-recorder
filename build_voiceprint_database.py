#!/usr/bin/env python3
"""
Build Voiceprint Database from Analyzed Archive

This script:
1. Loads presenter_labels.json from analyze_archive.py
2. Filters for high-confidence matches suitable for training
3. Selects diverse samples for each presenter (max N per presenter)
4. Extracts embeddings via Rack speaker_recognition.py
5. Builds final voiceprint database

Usage:
    python3 build_voiceprint_database.py presenter_labels.json \
        --max-samples 10 \
        --output /mnt/rack-shipping/voiceprints/database.json

Requirements:
    - speaker_recognition.py installed on Rack at /usr/local/bin/speaker_recognition.py
    - SSH access to Rack configured
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration for database building"""
    RACK_SSH_HOST = "root@192.168.4.64"
    RACK_SPEAKER_SCRIPT = "/usr/local/bin/speaker_recognition.py"
    RACK_TEMP_DIR = "/tmp/voiceprints"


def filter_suitable_recordings(
    labels_data: Dict[str, Any],
    max_samples_per_presenter: int = 10
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Filter recordings suitable for training and group by presenter.

    Args:
        labels_data: Data from presenter_labels.json
        max_samples_per_presenter: Maximum samples to keep per presenter

    Returns:
        Dict mapping presenter names to lists of recording data
    """
    by_presenter = defaultdict(list)

    # Filter suitable recordings
    for result in labels_data.get("results", []):
        if result.get("suitable_for_training"):
            presenter = result.get("presenter")
            if presenter:
                by_presenter[presenter].append(result)

    # Limit samples per presenter (keep most recent)
    for presenter in by_presenter:
        recordings = by_presenter[presenter]

        # Sort by timestamp (newest first)
        recordings.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Keep only max_samples
        by_presenter[presenter] = recordings[:max_samples_per_presenter]

    return dict(by_presenter)


def copy_file_to_rack(local_path: str, remote_path: str) -> bool:
    """
    Copy file to Rack via SCP.

    Args:
        local_path: Local file path
        remote_path: Remote file path on Rack

    Returns:
        True if successful
    """
    try:
        cmd = ["scp", "-q", local_path, f"{Config.RACK_SSH_HOST}:{remote_path}"]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to copy {local_path} to Rack: {e}")
        return False


def extract_embedding_on_rack(audio_path: str) -> Optional[List[float]]:
    """
    Extract speaker embedding via Rack.

    Args:
        audio_path: Path to audio file (will be copied to Rack)

    Returns:
        Embedding vector (list of floats) or None if failed
    """
    try:
        # Copy file to Rack temp directory
        filename = Path(audio_path).name
        remote_path = f"{Config.RACK_TEMP_DIR}/{filename}"

        # Ensure temp directory exists on Rack
        mkdir_cmd = ["ssh", Config.RACK_SSH_HOST, f"mkdir -p {Config.RACK_TEMP_DIR}"]
        subprocess.run(mkdir_cmd, capture_output=True, timeout=10)

        # Copy file
        logger.info(f"  Copying to Rack: {filename}")
        if not copy_file_to_rack(audio_path, remote_path):
            return None

        # Extract embedding
        logger.info(f"  Extracting embedding...")
        ssh_cmd = [
            "ssh", Config.RACK_SSH_HOST,
            f"python3 {Config.RACK_SPEAKER_SCRIPT} extract {remote_path}"
        ]

        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            logger.error(f"  Extraction failed: {result.stderr}")
            return None

        # Parse JSON response
        response = json.loads(result.stdout)

        if "error" in response:
            logger.error(f"  Error: {response['error']}")
            return None

        embedding = response.get("embedding")

        # Clean up remote file
        cleanup_cmd = ["ssh", Config.RACK_SSH_HOST, f"rm -f {remote_path}"]
        subprocess.run(cleanup_cmd, capture_output=True, timeout=10)

        logger.info(f"  ✓ Extracted {len(embedding)}-dimensional embedding")
        return embedding

    except subprocess.TimeoutExpired:
        logger.error("  Timeout extracting embedding")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"  Invalid JSON response: {e}")
        return None
    except Exception as e:
        logger.error(f"  Extraction failed: {e}")
        return None


def build_database(
    recordings_by_presenter: Dict[str, List[Dict[str, Any]]],
    progress_callback=None
) -> Dict[str, List[List[float]]]:
    """
    Build voiceprint database by extracting embeddings.

    Args:
        recordings_by_presenter: Dict mapping presenters to recording data
        progress_callback: Optional callback(current, total, presenter, file)

    Returns:
        Dict mapping presenter names to lists of embeddings
    """
    database = {}

    # Count total files
    total_files = sum(len(recordings) for recordings in recordings_by_presenter.values())
    current_file = 0

    logger.info(f"Extracting embeddings for {len(recordings_by_presenter)} presenters...")
    logger.info("─" * 80)

    for presenter, recordings in sorted(recordings_by_presenter.items()):
        logger.info(f"\n{presenter} ({len(recordings)} samples):")
        embeddings = []

        for recording in recordings:
            current_file += 1
            audio_path = recording["file"]

            if progress_callback:
                progress_callback(current_file, total_files, presenter, audio_path)

            logger.info(f"[{current_file:3d}/{total_files}] {Path(audio_path).name}")

            embedding = extract_embedding_on_rack(audio_path)

            if embedding:
                embeddings.append(embedding)
            else:
                logger.warning(f"  ✗ Skipping (extraction failed)")

        if embeddings:
            database[presenter] = embeddings
            logger.info(f"  ✓ Collected {len(embeddings)} embeddings for {presenter}")
        else:
            logger.warning(f"  ✗ No embeddings collected for {presenter}")

    return database


def validate_database(database: Dict[str, List[List[float]]]) -> Dict[str, Any]:
    """
    Validate database quality by computing within-speaker and between-speaker similarities.

    Args:
        database: Voiceprint database

    Returns:
        Dict with validation statistics
    """
    import numpy as np

    def cosine_similarity(e1, e2):
        e1 = np.array(e1)
        e2 = np.array(e2)
        return np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-8)

    stats = {
        "presenters": len(database),
        "total_embeddings": sum(len(embs) for embs in database.values()),
        "within_speaker_similarity": {},
        "between_speaker_similarity": []
    }

    # Within-speaker similarity (should be high)
    for presenter, embeddings in database.items():
        if len(embeddings) < 2:
            continue

        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(float(sim))

        if similarities:
            stats["within_speaker_similarity"][presenter] = {
                "mean": float(np.mean(similarities)),
                "std": float(np.std(similarities)),
                "min": float(np.min(similarities)),
                "max": float(np.max(similarities)),
                "count": len(similarities)
            }

    # Between-speaker similarity (should be low)
    presenter_names = list(database.keys())
    for i in range(len(presenter_names)):
        for j in range(i + 1, len(presenter_names)):
            p1_embs = database[presenter_names[i]]
            p2_embs = database[presenter_names[j]]

            # Compare first embeddings (representative)
            if p1_embs and p2_embs:
                sim = cosine_similarity(p1_embs[0], p2_embs[0])
                stats["between_speaker_similarity"].append({
                    "pair": f"{presenter_names[i]} vs {presenter_names[j]}",
                    "similarity": float(sim)
                })

    # Compute overall between-speaker stats
    if stats["between_speaker_similarity"]:
        between_sims = [x["similarity"] for x in stats["between_speaker_similarity"]]
        stats["between_speaker_mean"] = float(np.mean(between_sims))
        stats["between_speaker_std"] = float(np.std(between_sims))

    return stats


def print_validation_report(stats: Dict[str, Any]):
    """Print validation report to console."""
    logger.info("\n" + "=" * 80)
    logger.info("  DATABASE VALIDATION")
    logger.info("=" * 80)
    logger.info(f"Total presenters: {stats['presenters']}")
    logger.info(f"Total embeddings: {stats['total_embeddings']}")
    logger.info("")

    logger.info("Within-speaker similarity (higher is better, should be > 0.7):")
    for presenter, similarity in sorted(stats["within_speaker_similarity"].items()):
        logger.info(
            f"  {presenter:30s}: "
            f"mean={similarity['mean']:.3f} "
            f"std={similarity['std']:.3f} "
            f"(n={similarity['count']})"
        )
    logger.info("")

    if "between_speaker_mean" in stats:
        logger.info("Between-speaker similarity (lower is better, should be < 0.5):")
        logger.info(f"  Overall mean: {stats['between_speaker_mean']:.3f}")
        logger.info(f"  Overall std:  {stats['between_speaker_std']:.3f}")
        logger.info("")

        # Show most similar pairs (potential confusion)
        sorted_pairs = sorted(
            stats["between_speaker_similarity"],
            key=lambda x: x["similarity"],
            reverse=True
        )

        logger.info("Most similar presenter pairs (potential confusion):")
        for pair in sorted_pairs[:5]:
            logger.info(f"  {pair['pair']:50s}: {pair['similarity']:.3f}")

    logger.info("=" * 80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Build voiceprint database from analyzed archive",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "labels_file",
        help="Path to presenter_labels.json from analyze_archive.py"
    )

    parser.add_argument(
        "--max-samples",
        type=int,
        default=10,
        help="Maximum samples per presenter (default: 10)"
    )

    parser.add_argument(
        "--output",
        default="/mnt/rack-shipping/voiceprints/database.json",
        help="Output database file (default: /mnt/rack-shipping/voiceprints/database.json)"
    )

    parser.add_argument(
        "--metadata-output",
        help="Optional metadata output file (saves validation stats and source info)"
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("  Voiceprint Database Builder")
    logger.info("=" * 80)
    logger.info(f"Labels file: {args.labels_file}")
    logger.info(f"Max samples per presenter: {args.max_samples}")
    logger.info(f"Output: {args.output}")
    logger.info("")

    # Load labels
    try:
        with open(args.labels_file) as f:
            labels_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load labels file: {e}")
        return 1

    # Filter suitable recordings
    recordings_by_presenter = filter_suitable_recordings(labels_data, args.max_samples)

    if not recordings_by_presenter:
        logger.error("No suitable recordings found for training")
        return 1

    logger.info("Selected recordings:")
    for presenter, recordings in sorted(recordings_by_presenter.items()):
        logger.info(f"  {presenter:30s}: {len(recordings)} samples")
    logger.info("")

    # Build database
    database = build_database(recordings_by_presenter)

    if not database:
        logger.error("Failed to build database (no embeddings extracted)")
        return 1

    # Validate database
    logger.info("")
    validation_stats = validate_database(database)
    print_validation_report(validation_stats)

    # Save database
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(database, f, indent=2)

    logger.info(f"\n✓ Database saved to: {output_path}")

    # Save metadata if requested
    if args.metadata_output:
        metadata = {
            "created_at": datetime.now().isoformat(),
            "labels_file": args.labels_file,
            "max_samples_per_presenter": args.max_samples,
            "recordings_by_presenter": {
                presenter: [r["file"] for r in recordings]
                for presenter, recordings in recordings_by_presenter.items()
            },
            "validation": validation_stats
        }

        metadata_path = Path(args.metadata_output)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"✓ Metadata saved to: {metadata_path}")

    logger.info("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
