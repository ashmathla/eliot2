# wave_engine/multi_tf_wave_engine.py
"""
Multi-Timeframe Wave Analysis.

CHANGE LOG (this revision):
- After analyzing each timeframe, we now also compute that timeframe's
  own `direction` (via direction_utils.compute_direction) from its raw
  swings — independent of whatever pattern label it was classified as.
- Both parent_pattern AND parent_direction are passed down to the next
  (smaller) timeframe. parent_direction is what actually drives the
  "is this a correction relative to parent" logic now; parent_pattern
  is kept only for diagnostics/confidence weighting.
- This fixes the regression where a parent classified as a correction
  itself (e.g. "zigzag") was not recognized by the old
  parent_pattern == "bearish_impulse"/"bullish_impulse" check, causing
  the child timeframe to fall through to an invalid correction_start
  and return "unknown".
"""

from wave_engine.pivot_detector import get_last_pivots
from wave_engine.swing_structure import build_swing_sequence
from wave_engine.elliott_wave_engine import detect_elliott_pattern
from wave_engine.wave_context import build_wave_context
from wave_engine.direction_utils import compute_direction

DIRECTION_WINDOW = 15  # same lookback used for correction_start search


def analyze_timeframe_wave(df, timeframe, parent_pattern=None, parent_direction=None):
    pivots = get_last_pivots(df, timeframe)
    swings = build_swing_sequence(pivots)

    elliott = detect_elliott_pattern(
        swings,
        parent_pattern=parent_pattern,
        parent_direction=parent_direction,
    )

    context = build_wave_context(elliott)
    direction = compute_direction(swings, window=DIRECTION_WINDOW)

    return {
        "pivots": pivots,
        "swings": swings,
        "elliott": elliott,
        "context": context,
        "wave_type": elliott["pattern"],
        "current_wave": elliott["current_wave"],
        "confidence": elliott["confidence"],
        "direction": direction,
    }


def analyze_multi_tf_waves(timeframes):
    w1_wave = analyze_timeframe_wave(timeframes["W1"], "W1")

    d1_wave = analyze_timeframe_wave(
        timeframes["D1"],
        "D1",
        parent_pattern=w1_wave["elliott"]["pattern"],
        parent_direction=w1_wave["direction"],
    )

    h4_wave = analyze_timeframe_wave(
        timeframes["H4"],
        "H4",
        parent_pattern=d1_wave["elliott"]["pattern"],
        parent_direction=d1_wave["direction"],
    )

    h1_wave = analyze_timeframe_wave(
        timeframes["H1"],
        "H1",
        parent_pattern=h4_wave["elliott"]["pattern"],
        parent_direction=h4_wave["direction"],
    )

    return {
        "W1": w1_wave,
        "D1": d1_wave,
        "H4": h4_wave,
        "H1": h1_wave,
    }