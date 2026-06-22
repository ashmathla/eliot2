# structure_engine/timeframe_choch.py

def detect_structure_choch(swings):

    if len(swings) < 4:

        return {
            "choch": "none",
            "confidence": 0
        }

    highs = [
        x for x in swings
        if x["type"] == "HIGH"
    ]

    lows = [
        x for x in swings
        if x["type"] == "LOW"
    ]

    if len(highs) < 2 or len(lows) < 2:

        return {
            "choch": "none",
            "confidence": 0
        }

    last_high = highs[-1]["price"]
    prev_high = highs[-2]["price"]

    last_low = lows[-1]["price"]
    prev_low = lows[-2]["price"]

    if last_high > prev_high and last_low > prev_low:

        return {
            "choch": "bullish",
            "confidence": 80
        }

    if last_high < prev_high and last_low < prev_low:

        return {
            "choch": "bearish",
            "confidence": 80
        }

    return {
        "choch": "none",
        "confidence": 40
    }