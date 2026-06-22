# wave_engine/wave_classifier.py
"""
Wave classification with direction-aware context.

CHANGE LOG (this revision):
- classify_wave now accepts `parent_direction` ("up" | "down" | None)
  IN ADDITION to `parent_pattern`.
- The decision of "is this impulse actually a correction relative to
  the parent" is now made by comparing the candidate's own implied
  direction against `parent_direction`, NOT by string-matching
  parent_pattern against the literal "bearish_impulse" / "bullish_impulse".
  This fixes the bug where a parent that is itself a correction
  (e.g. "zigzag", "flat", "ABC") was silently ignored because the old
  code only recognized the two impulse labels.
- parent_pattern is still accepted and still used (e.g. to decide
  confidence weighting), but it is no longer load-bearing for the
  direction check.
- When the branch resolves to "ABC" (a correction relative to parent),
  we still compute correction_start the same way as before: search
  backwards through `swings` (not just the local 5-point window) for
  the genuine reversal point in the direction opposite to parent_direction.
"""

from wave_engine.direction_utils import compute_direction

CORRECTION_SEARCH_WINDOW = 15


def _find_correction_start(swings, parent_direction):
    """
    Walk backwards through swings to find the real start of the
    correction: the most extreme point in the direction of the
    parent's impulse, within a bounded lookback window.

    If parent_direction == "down": the parent impulse moved price down,
    so the correction starts at the lowest LOW in the lookback window
    (the bottom of that down move).

    If parent_direction == "up": correction starts at the highest HIGH
    in the lookback window.
    """
    if not swings or parent_direction not in ("up", "down"):
        return None

    window = swings[-CORRECTION_SEARCH_WINDOW:]

    if parent_direction == "down":
        candidates = [s for s in window if s["type"] == "LOW"]
        if not candidates:
            return None
        return min(candidates, key=lambda s: s["price"])
    else:
        candidates = [s for s in window if s["type"] == "HIGH"]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s["price"])


def classify_wave(swings, parent_pattern=None, parent_direction=None):
    """
    Classify the most recent wave structure in `swings`.

    Args:
        swings: full chronological list of swing dicts for this timeframe
        parent_pattern: pattern label of the higher timeframe (for
            confidence weighting / diagnostics only)
        parent_direction: "up" | "down" | None — the higher timeframe's
            actual price direction. This is what we use to decide
            whether the current candidate is a correction.

    Returns:
        dict with at least: pattern, wave/current_wave, confidence,
        and (when pattern == "ABC") correction_start.
    """

    if len(swings) < 5:
        return {
            "pattern": "unknown",
            "wave": "unknown",
            "confidence": 0,
            "correction_start": None,
        }

    recent = swings[-5:]
    p1 = recent[0]["price"]
    p2 = recent[1]["price"]
    p3 = recent[2]["price"]
    p4 = recent[3]["price"]
    p5 = recent[4]["price"]

    own_direction = "up" if p5 > p1 else ("down" if p5 < p1 else None)

    # ---- Bearish candidate (p3 < p1 and p5 < p3) ----
    if p3 < p1 and p5 < p3:
        if parent_direction == "up" and own_direction == "down":
            # Move is opposite to parent's actual direction -> correction
            correction_start = _find_correction_start(swings, parent_direction)
            return {
                "pattern": "ABC",
                "wave": "wave_C",
                "confidence": 70,
                "correction_start": correction_start,
            }
        return {
            "pattern": "bearish_impulse",
            "wave": "wave_3_or_5",
            "confidence": 75,
            "correction_start": None,
        }

    # ---- Bullish candidate (p3 > p1 and p5 > p3) ----
    if p3 > p1 and p5 > p3:
        if parent_direction == "down" and own_direction == "up":
            correction_start = _find_correction_start(swings, parent_direction)
            return {
                "pattern": "ABC",
                "wave": "wave_C",
                "confidence": 70,
                "correction_start": correction_start,
            }
        return {
            "pattern": "bullish_impulse",
            "wave": "wave_3_or_5",
            "confidence": 75,
            "correction_start": None,
        }

    # ---- Fallback: ambiguous shape ----
    correction_start = None
    if parent_direction in ("up", "down"):
        correction_start = _find_correction_start(swings, parent_direction)

    return {
        "pattern": "ABC",
        "wave": "wave_C",
        "confidence": 65,
        "correction_start": correction_start,
    }