#!/usr/bin/env python3
"""Test presenter name extraction patterns against sample sign-off phrases."""

import re
import json
from pathlib import Path
from difflib import SequenceMatcher

# Load known presenters
PRESENTERS_FILE = Path(__file__).parent / "presenters.json"

def load_presenters():
    """Load known presenters database."""
    if PRESENTERS_FILE.exists():
        with open(PRESENTERS_FILE) as f:
            data = json.load(f)
            return data.get("presenters", [])
    return []

# Extraction patterns - ordered by specificity
NAME_PATTERNS = [
    # "This is [Name]" - most common
    re.compile(r"\b(?:This is|This has been)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", re.IGNORECASE),
    # "I'm [Name]"
    re.compile(r"\b(?:I'm|I am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", re.IGNORECASE),
    # "[Name] for BBC Radio 4" or "[Name] on BBC Radio 4"
    re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:for|on|from)\s+(?:BBC|Radio)", re.IGNORECASE),
    # "...with [Name]" (less common)
    re.compile(r"\bwith\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[.,]", re.IGNORECASE),
]

# Words that shouldn't be treated as names (false positives)
FALSE_POSITIVE_WORDS = {
    "the", "shipping", "forecast", "weather", "radio", "bbc",
    "good", "night", "morning", "evening", "and", "now", "that"
}

def extract_name_candidates(transcript: str) -> list[str]:
    """Extract all potential presenter names from transcript."""
    candidates = []
    for pattern in NAME_PATTERNS:
        matches = pattern.findall(transcript)
        for match in matches:
            # Filter out false positives
            words = match.lower().split()
            if not all(w in FALSE_POSITIVE_WORDS for w in words):
                candidates.append(match)
    return candidates

def fuzzy_match(name: str, known_presenters: list[dict], threshold: float = 0.7) -> dict | None:
    """Fuzzy match extracted name against known presenters."""
    name_lower = name.lower().strip()

    for presenter in known_presenters:
        # Check exact match on full name
        if name_lower == presenter["name"].lower():
            return {"name": presenter["name"], "confidence": 1.0, "match_type": "exact"}

        # Check variations
        for variation in presenter.get("variations", []):
            if name_lower == variation.lower():
                return {"name": presenter["name"], "confidence": 1.0, "match_type": "variation"}

        # Fuzzy match on full name
        ratio = SequenceMatcher(None, name_lower, presenter["name"].lower()).ratio()
        if ratio >= threshold:
            return {"name": presenter["name"], "confidence": ratio, "match_type": "fuzzy"}

        # Fuzzy match on variations
        for variation in presenter.get("variations", []):
            ratio = SequenceMatcher(None, name_lower, variation.lower()).ratio()
            if ratio >= threshold:
                return {"name": presenter["name"], "confidence": ratio, "match_type": "fuzzy_variation"}

    return None

def detect_presenter(transcript: str, known_presenters: list[dict] = None) -> dict:
    """
    Detect presenter from transcript.

    Returns dict with:
        - presenter: str or None (canonical name)
        - raw_match: str (what was extracted)
        - confidence: float (0.0-1.0)
        - match_type: str (exact/variation/fuzzy/unknown)
    """
    if known_presenters is None:
        known_presenters = load_presenters()

    candidates = extract_name_candidates(transcript)

    if not candidates:
        return {"presenter": None, "raw_match": None, "confidence": 0.0, "match_type": "no_match"}

    # Try each candidate
    for candidate in candidates:
        match = fuzzy_match(candidate, known_presenters)
        if match:
            return {
                "presenter": match["name"],
                "raw_match": candidate,
                "confidence": match["confidence"],
                "match_type": match["match_type"]
            }

    # No known presenter matched - return first candidate as unknown
    return {
        "presenter": None,
        "raw_match": candidates[0],
        "confidence": 0.0,
        "match_type": "unknown"
    }


# Test cases - simulated sign-off phrases
TEST_CASES = [
    # Standard "This is [Name]" patterns
    ("And that concludes the shipping forecast. This is Zeb Soanes.", "Zeb Soanes"),
    ("...good night. This is Chris Aldridge.", "Chris Aldridge"),
    ("This has been Kathy Clugston with the shipping forecast.", "Kathy Clugston"),

    # "I'm [Name]" patterns
    ("I'm Neil Nunes, and that was the shipping forecast.", "Neil Nunes"),
    ("I'm Corrie Corfield. Good night.", "Corrie Corfield"),

    # "[Name] for BBC" patterns
    ("Carolyn Brown for BBC Radio 4.", "Carolyn Brown"),
    ("Diana Speed on BBC Radio 4.", "Diana Speed"),

    # First name only (should match via variations)
    ("This is Zeb. Good night.", "Zeb Soanes"),
    ("I'm Chris, and that was the late forecast.", "Chris Aldridge"),

    # Slight transcription errors (fuzzy matching)
    ("This is Zeb Soans.", "Zeb Soanes"),  # typo
    ("I'm Kathy Clugsten.", "Kathy Clugston"),  # typo

    # Unknown presenter (not in database)
    ("This is Alice Smith.", None),

    # No sign-off pattern
    ("Shipping areas Viking, North Utsire, South Utsire...", None),

    # Edge cases
    ("", None),
    ("This is the shipping forecast.", None),  # "the shipping forecast" shouldn't match
]


def run_tests():
    """Run all test cases and report results."""
    presenters = load_presenters()
    print(f"Loaded {len(presenters)} known presenters\n")

    passed = 0
    failed = 0

    for transcript, expected in TEST_CASES:
        result = detect_presenter(transcript, presenters)
        actual = result["presenter"]

        if actual == expected:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            failed += 1

        print(f"[{status}] '{transcript[:50]}...' if len(transcript) > 50 else '{transcript}'")
        print(f"       Expected: {expected}")
        print(f"       Got: {actual} (raw: {result['raw_match']}, conf: {result['confidence']:.2f}, type: {result['match_type']})")
        print()

    print(f"\n{'='*50}")
    print(f"Results: {passed}/{passed+failed} passed ({100*passed/(passed+failed):.0f}%)")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
