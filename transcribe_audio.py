#!/usr/bin/env python3
"""Simple Whisper transcription script for Shipping Forecast presenter detection."""

import sys
import json
from faster_whisper import WhisperModel

def transcribe(audio_path: str, model_size: str = "base") -> dict:
    """Transcribe audio file and return result."""
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(audio_path, beam_size=5)
    
    # Collect all text
    text_parts = []
    for segment in segments:
        text_parts.append(segment.text)
    
    full_text = " ".join(text_parts).strip()
    
    return {
        "text": full_text,
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: transcribe_audio.py <audio_file> [model_size]"}))
        sys.exit(1)
    
    audio_file = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "base"
    
    try:
        result = transcribe(audio_file, model_size)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
