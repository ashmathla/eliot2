# wave_engine/wave_detector.py

def detect_wave_structure(pivots):

    highs = pivots["highs"]
    lows = pivots["lows"]

    if len(highs) < 2 or len(lows) < 2:

        return {
            "structure": "unknown",
            "current_wave": "unknown",
            "confidence": 0
        }

    last_high = highs[-1]["price"]
    prev_high = highs[-2]["price"]

    last_low = lows[-1]["price"]
    prev_low = lows[-2]["price"]

    # Higher High + Higher Low
    if last_high > prev_high and last_low > prev_low:

        return {
            "structure": "impulse",
            "current_wave": "bullish_sequence",
            "confidence": 60
        }

    # Lower High + Lower Low
    if last_high < prev_high and last_low < prev_low:

        return {
            "structure": "impulse",
            "current_wave": "bearish_sequence",
            "confidence": 60
        }

    # Higher Low + Lower High
    if last_low > prev_low and last_high < prev_high:

        return {
            "structure": "correction",
            "current_wave": "ABC",
            "confidence": 70
        }

    return {
        "structure": "complex",
        "current_wave": "unknown",
        "confidence": 40
    }