#!/usr/bin/env python3
"""
Test anthem detection using cross-correlation with a template
"""

import wave
import numpy as np
from scipy import signal
import sys


def load_wav(path: str) -> tuple[np.ndarray, int]:
    """Load WAV file and return samples and sample rate"""
    with wave.open(path, 'r') as wav:
        frames = wav.readframes(wav.getnframes())
        sample_rate = wav.getframerate()
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    return samples, sample_rate


def detect_anthem_with_template(recording_path: str, template_path: str, start_search_time: float = 600) -> tuple[float, float] | None:
    """
    Detect anthem in recording using cross-correlation with template

    Args:
        recording_path: Path to full recording
        template_path: Path to anthem template (drumroll + opening)
        start_search_time: Start searching from this time in seconds (default 10 minutes)

    Returns:
        Tuple of (time_in_seconds, correlation_score) or None
    """
    print(f"Loading template from {template_path}")
    template, template_rate = load_wav(template_path)
    print(f"  Template: {len(template)} samples, {len(template)/template_rate:.2f}s duration")

    print(f"\nLoading recording from {recording_path}")
    recording, rec_rate = load_wav(recording_path)
    print(f"  Recording: {len(recording)} samples, {len(recording)/rec_rate:.2f}s duration")

    # Verify sample rates match
    if template_rate != rec_rate:
        print(f"ERROR: Sample rate mismatch! Template: {template_rate}, Recording: {rec_rate}")
        return None

    # Start search from specified time
    start_sample = int(start_search_time * rec_rate)
    search_region = recording[start_sample:]

    print(f"\nSearching from {start_search_time/60:.1f} minutes onwards...")
    print(f"  Search region: {len(search_region)} samples, {len(search_region)/rec_rate:.2f}s")

    # Normalize both signals
    template_norm = (template - np.mean(template)) / np.std(template)
    search_norm = (search_region - np.mean(search_region)) / np.std(search_region)

    # Compute cross-correlation
    print("\nComputing cross-correlation...")
    correlation = signal.correlate(search_norm, template_norm, mode='valid')

    # Find peak
    peak_idx = np.argmax(correlation)
    peak_value = correlation[peak_idx]

    # Convert to time in original recording
    detection_sample = start_sample + peak_idx
    detection_time = detection_sample / rec_rate

    print(f"\n{'='*70}")
    print(f"RESULTS:")
    print(f"{'='*70}")
    print(f"Peak correlation: {peak_value:.2f}")
    print(f"Detected at: {int(detection_time // 60)}:{int(detection_time % 60):02d} ({detection_time:.2f}s)")
    print(f"Sample index: {detection_sample}")

    # Show some context around the peak
    context_window = 50
    start_ctx = max(0, peak_idx - context_window)
    end_ctx = min(len(correlation), peak_idx + context_window)
    context = correlation[start_ctx:end_ctx]

    print(f"\nCorrelation values around peak:")
    for i, val in enumerate(context[::10]):  # Show every 10th value
        actual_idx = start_ctx + i * 10
        time_offset = actual_idx / rec_rate
        actual_time = start_search_time + time_offset
        marker = " <-- PEAK" if (start_ctx + i * 10) == peak_idx else ""
        print(f"  {int(actual_time // 60)}:{int(actual_time % 60):02d} - {val:.2f}{marker}")

    return detection_time, peak_value


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_anthem_detection.py <recording.wav> [template.wav]")
        sys.exit(1)

    recording = sys.argv[1]
    template = sys.argv[2] if len(sys.argv) > 2 else "/home/pi/share/198k/anthem_template.wav"

    result = detect_anthem_with_template(recording, template)

    if result:
        time, score = result
        print(f"\n✓ Anthem detected at {int(time // 60)}:{int(time % 60):02d} with confidence {score:.2f}")
    else:
        print("\n✗ Detection failed")
