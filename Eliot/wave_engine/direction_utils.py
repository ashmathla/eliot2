# wave_engine/direction_utils.py
"""
Shared helper for computing a simple trend direction ("up" / "down")
from a list of swings, independent of any pattern classification.

This is intentionally dumb and stable: it just compares the price of
the first and last swing in the given window. It must be the single
source of truth for "direction" used across classify_wave,
detect_correction, and the multi-timeframe orchestrator, so that
parent context is never inferred from a pattern label string again.
"""


def compute_direction(swings, window=None):
    """
    Compute direction from a list of swing dicts (each with a "price" key).

    Args:
        swings: list of swing dicts, ordered chronologically
        window: optional int, only look at the last `window` swings.
                If None, use the full list.

    Returns:
        "up" | "down" | None (None if not enough data to decide)
    """
    if not swings:
        return None

    points = swings[-window:] if window else swings

    if len(points) < 2:
        return None

    first_price = points[0]["price"]
    last_price = points[-1]["price"]

    if last_price == first_price:
        return None

    return "up" if last_price > first_price else "down"