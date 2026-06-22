# wave_engine/wave_context_engine.py

def detect_wave_context(swings):

    if len(swings) < 10:

        return {
            "cycle": "unknown",
            "next_expected": "unknown"
        }

    highs = [
        x["price"]
        for x in swings
        if x["type"] == "HIGH"
    ]

    lows = [
        x["price"]
        for x in swings
        if x["type"] == "LOW"
    ]

    bearish_count = 0

    for i in range(1, len(highs)):

        if highs[i] < highs[i - 1]:
            bearish_count += 1

    for i in range(1, len(lows)):

        if lows[i] < lows[i - 1]:
            bearish_count += 1

    bullish_count = 0

    for i in range(1, len(highs)):

        if highs[i] > highs[i - 1]:
            bullish_count += 1

    for i in range(1, len(lows)):

        if lows[i] > lows[i - 1]:
            bullish_count += 1

    if bearish_count >= 6:

        return {
            "cycle": "bearish",
            "next_expected": "wave_4"
        }

    if bullish_count >= 6:

        return {
            "cycle": "bullish",
            "next_expected": "wave_4"
        }

    return {
        "cycle": "correction",
        "next_expected": "wave_C"
    }