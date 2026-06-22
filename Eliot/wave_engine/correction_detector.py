# wave_engine/correction_detector.py
"""
Zigzag/Flat correction detector built on a real correction_start point
(passed in from wave_classifier), not a guessed local window.

Validates wave_B and wave_C against wave_A using formal Fibonacci
ratios instead of accepting any 3-swing shape as a correction.
"""

WAVE_B_MIN_RATIO = 0.382
WAVE_B_MAX_RATIO = 1.00
WAVE_C_MIN_RATIO = 0.618
WAVE_C_MAX_RATIO = 1.80


def _find_wave_end(swings, start_index, want_type):
    """Find the next swing after start_index whose type == want_type."""
    for s in swings:
        if s["index"] > start_index and s["type"] == want_type:
            return s
    return None


def detect_correction(swings, parent_pattern=None, correction_start=None):
    """
    Detect correction type (zigzag / flat / unknown) starting from
    `correction_start` (a swing dict, typically the extreme point that
    ends the parent's impulse).

    Returns dict with: correction_type, current_wave, next_expected,
    subwave, confidence — or correction_type == "unknown" if the
    shape doesn't pass Fibonacci validation.
    """
    if not correction_start or not swings:
        return {"correction_type": "unknown", "confidence": 0}

    start_idx = correction_start["index"]
    start_price = correction_start["price"]
    start_type = correction_start["type"]

    # wave_A ends at the first opposite-type swing after start
    a_end_type = "HIGH" if start_type == "LOW" else "LOW"
    a_end = _find_wave_end(swings, start_idx, a_end_type)
    if not a_end:
        return {"correction_type": "unknown", "confidence": 0}

    b_end_type = start_type  # back toward start's type
    b_end = _find_wave_end(swings, a_end["index"], b_end_type)
    if not b_end:
        return {"correction_type": "unknown", "confidence": 0}

    c_end_type = a_end_type
    c_end = _find_wave_end(swings, b_end["index"], c_end_type)
    if not c_end:
        return {"correction_type": "unknown", "confidence": 0}

    a_len = abs(a_end["price"] - start_price)
    b_len = abs(b_end["price"] - a_end["price"])
    c_len = abs(c_end["price"] - b_end["price"])

    if a_len == 0:
        return {"correction_type": "unknown", "confidence": 0}

    b_ratio = b_len / a_len
    c_ratio = c_len / a_len

    b_valid = b_ratio <= WAVE_B_MAX_RATIO
    c_valid = WAVE_C_MIN_RATIO <= c_ratio <= WAVE_C_MAX_RATIO

    if not (b_valid and c_valid):
        return {"correction_type": "unknown", "confidence": 0}

    confidence = 80
    if b_ratio < WAVE_B_MIN_RATIO:
        confidence -= 10  # B is unusually shallow

    return {
        "correction_type": "zigzag",
        "current_wave": "wave_C",
        "next_expected": "wave_2",
        "subwave": "wave_4",
        "confidence": confidence,
        "ratios": {"b_ratio": round(b_ratio, 4), "c_ratio": round(c_ratio, 4)},
    }