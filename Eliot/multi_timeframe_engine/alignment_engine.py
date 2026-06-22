# multi_timeframe_engine/alignment_engine.py

def calculate_alignment(summary):

    score = 0

    for tf in ["W1", "D1", "H1"]:

        trend = summary[tf]["primary_trend"]

        if trend == "bullish":
            score += 1

        elif trend == "bearish":
            score -= 1

    if score >= 2:

        return {
            "direction": "buy",
            "score": 100
        }

    elif score <= -2:

        return {
            "direction": "sell",
            "score": 100
        }

    return {
        "direction": "neutral",
        "score": 50
    }