#!/usr/bin/env python3
"""
Speaker Recognition Service for Shipping Forecast Voiceprint Identification

This script runs on Rack and provides speaker recognition capabilities using
pyannote.audio for extracting speaker embeddings and comparing them.

Installation (on Rack):
    pip install pyannote.audio torch torchaudio

Usage:
    # Extract embedding from audio file
    python3 speaker_recognition.py extract <audio_file>

    # Compare embedding against database
    python3 speaker_recognition.py compare <audio_file> <database_json>

    # Batch extract embeddings (for building database)
    python3 speaker_recognition.py batch <file_list.txt> <output_dir>

Database format (JSON):
{
    "John Hammond": [
        [0.123, 0.456, ...],  # embedding 1 (512 floats)
        [0.234, 0.567, ...]   # embedding 2 (512 floats)
    ],
    "Kelsey Bennett": [...]
}

Output format:
{
    "embedding": [0.123, 0.456, ...],  # 512 floats
    "matches": [
        {"name": "John Hammond", "similarity": 0.87, "rank": 1},
        {"name": "Kelsey Bennett", "similarity": 0.45, "rank": 2}
    ]
}
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np


def setup_model():
    """
    Load and initialize the speaker embedding model.

    Returns:
        Tuple of (model, device)
    """
    try:
        import torch
        from pyannote.audio import Model, Inference
    except ImportError as e:
        print(json.dumps({"error": f"Required packages not installed: {e}"}), file=sys.stderr)
        sys.exit(1)

    # Use GPU if available, otherwise CPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load pre-trained speaker embedding model
    # Using pyannote/embedding which is a general-purpose speaker embedding model
    try:
        model = Model.from_pretrained("pyannote/embedding")
        inference = Inference(model, window="whole", device=device)
    except Exception as e:
        print(json.dumps({"error": f"Failed to load model: {e}"}), file=sys.stderr)
        sys.exit(1)

    return inference, device


def extract_embedding(audio_path: str, inference) -> np.ndarray:
    """
    Extract speaker embedding from audio file.

    Args:
        audio_path: Path to audio file (WAV, MP3, etc.)
        inference: Pyannote inference model

    Returns:
        NumPy array of embedding (512-dimensional vector)
    """
    try:
        # Load audio manually using soundfile to avoid torchcodec issues
        import soundfile as sf
        import torch

        # Read audio file
        waveform, sample_rate = sf.read(audio_path)

        # Convert to torch tensor and ensure correct shape
        if waveform.ndim == 1:
            waveform = waveform[np.newaxis, :]  # Add channel dimension
        elif waveform.ndim == 2 and waveform.shape[0] > waveform.shape[1]:
            waveform = waveform.T  # Transpose if needed (samples, channels) -> (channels, samples)

        # Create dict format expected by pyannote
        audio_dict = {
            "waveform": torch.from_numpy(waveform).float(),
            "sample_rate": sample_rate
        }

        # Extract embedding
        embedding = inference(audio_dict)

        # Convert to numpy array
        if hasattr(embedding, 'numpy'):
            embedding_np = embedding.numpy()
        elif hasattr(embedding, 'cpu'):
            embedding_np = embedding.cpu().numpy()
        else:
            embedding_np = np.array(embedding)

        # Ensure 1D array
        if embedding_np.ndim > 1:
            embedding_np = embedding_np.flatten()

        return embedding_np

    except Exception as e:
        raise RuntimeError(f"Failed to extract embedding: {e}")


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two embeddings.

    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector

    Returns:
        Similarity score (0.0 to 1.0, higher is more similar)
    """
    # Normalize vectors
    e1_norm = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
    e2_norm = embedding2 / (np.linalg.norm(embedding2) + 1e-8)

    # Compute cosine similarity
    similarity = np.dot(e1_norm, e2_norm)

    # Clamp to [0, 1] range
    return float(max(0.0, min(1.0, similarity)))


def load_database(database_path: str) -> Dict[str, List[np.ndarray]]:
    """
    Load voiceprint database from JSON file.

    Args:
        database_path: Path to database JSON file

    Returns:
        Dict mapping presenter names to lists of embeddings
    """
    try:
        with open(database_path) as f:
            data = json.load(f)

        # Convert lists back to numpy arrays
        database = {}
        for name, embeddings in data.items():
            database[name] = [np.array(emb, dtype=np.float32) for emb in embeddings]

        return database

    except Exception as e:
        raise RuntimeError(f"Failed to load database: {e}")


def compare_against_database(
    embedding: np.ndarray,
    database: Dict[str, List[np.ndarray]]
) -> List[Dict[str, Any]]:
    """
    Compare embedding against voiceprint database.

    Args:
        embedding: Query embedding to compare
        database: Database of reference embeddings

    Returns:
        List of matches sorted by similarity (best first)
    """
    matches = []

    for name, reference_embeddings in database.items():
        # Compare against all reference embeddings for this presenter
        similarities = [
            cosine_similarity(embedding, ref_emb)
            for ref_emb in reference_embeddings
        ]

        # Take the maximum similarity (best match)
        best_similarity = max(similarities) if similarities else 0.0
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

        matches.append({
            "name": name,
            "similarity": round(best_similarity, 4),
            "avg_similarity": round(avg_similarity, 4),
            "num_references": len(similarities)
        })

    # Sort by similarity (descending)
    matches.sort(key=lambda x: x["similarity"], reverse=True)

    # Add rank
    for i, match in enumerate(matches, 1):
        match["rank"] = i

    return matches


def cmd_extract(args):
    """Extract embedding from audio file."""
    inference, device = setup_model()

    try:
        embedding = extract_embedding(args.audio_file, inference)

        # Output JSON
        result = {
            "embedding": embedding.tolist(),
            "dimension": len(embedding),
            "audio_file": args.audio_file
        }

        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_compare(args):
    """Compare audio file against database."""
    inference, device = setup_model()

    try:
        # Extract embedding
        embedding = extract_embedding(args.audio_file, inference)

        # Load database
        database = load_database(args.database)

        # Compare
        matches = compare_against_database(embedding, database)

        # Output JSON
        result = {
            "audio_file": args.audio_file,
            "embedding": embedding.tolist(),
            "matches": matches
        }

        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_batch(args):
    """Batch process files for database building."""
    inference, device = setup_model()

    try:
        # Read file list
        with open(args.file_list) as f:
            files = [line.strip() for line in f if line.strip()]

        results = {}

        for i, audio_file in enumerate(files, 1):
            print(f"[{i}/{len(files)}] Processing: {audio_file}", file=sys.stderr)

            try:
                embedding = extract_embedding(audio_file, inference)
                results[audio_file] = {
                    "embedding": embedding.tolist(),
                    "dimension": len(embedding)
                }
            except Exception as e:
                print(f"  Error: {e}", file=sys.stderr)
                results[audio_file] = {"error": str(e)}

        # Save results
        output_path = Path(args.output_file)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"Saved {len(results)} results to {output_path}", file=sys.stderr)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_build_database(args):
    """Build database from embeddings JSON."""
    try:
        # Load embeddings file (output from batch command)
        with open(args.embeddings_file) as f:
            embeddings_data = json.load(f)

        # Load labels file (mapping files to presenters)
        with open(args.labels_file) as f:
            labels_data = json.load(f)

        # Build database by grouping embeddings by presenter
        database = {}

        for file_path, emb_data in embeddings_data.items():
            if "error" in emb_data:
                continue

            # Find presenter label for this file
            presenter = None
            for result in labels_data.get("results", []):
                if result["file"] == file_path and result.get("suitable_for_training"):
                    presenter = result.get("presenter")
                    break

            if not presenter:
                continue

            # Add embedding to database
            if presenter not in database:
                database[presenter] = []

            database[presenter].append(emb_data["embedding"])

        # Save database
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(database, f, indent=2)

        # Print summary
        print(f"Built database with {len(database)} presenters:", file=sys.stderr)
        for presenter, embeddings in sorted(database.items()):
            print(f"  {presenter}: {len(embeddings)} embeddings", file=sys.stderr)

        print(f"Saved to: {output_path}", file=sys.stderr)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Speaker Recognition Service",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Extract command
    parser_extract = subparsers.add_parser(
        'extract',
        help='Extract speaker embedding from audio file'
    )
    parser_extract.add_argument('audio_file', help='Path to audio file')

    # Compare command
    parser_compare = subparsers.add_parser(
        'compare',
        help='Compare audio file against voiceprint database'
    )
    parser_compare.add_argument('audio_file', help='Path to audio file')
    parser_compare.add_argument('database', help='Path to database JSON file')

    # Batch command
    parser_batch = subparsers.add_parser(
        'batch',
        help='Batch process audio files for database building'
    )
    parser_batch.add_argument('file_list', help='Text file with list of audio files (one per line)')
    parser_batch.add_argument('output_file', help='Output JSON file for embeddings')

    # Build database command
    parser_build = subparsers.add_parser(
        'build-database',
        help='Build database from embeddings and labels'
    )
    parser_build.add_argument('embeddings_file', help='JSON file from batch command')
    parser_build.add_argument('labels_file', help='JSON file from analyze_archive.py')
    parser_build.add_argument('--output', default='database.json', help='Output database file')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command
    commands = {
        'extract': cmd_extract,
        'compare': cmd_compare,
        'batch': cmd_batch,
        'build-database': cmd_build_database,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
