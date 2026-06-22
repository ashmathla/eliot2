# multi_timeframe_engine/trend_alignment.py

def advanced_alignment(summary):

    score = 0

    weekly = summary["W1"]["primary_trend"]
    daily = summary["D1"]["primary_trend"]
    h1 = summary["H1"]["primary_trend"]

    # Weekly weight = 50

    if weekly == "bullish":
        score += 50

    elif weekly == "bearish":
        score -= 50

    # Daily weight = 30

    if daily == "bullish":
        score += 30

    elif daily == "bearish":
        score -= 30

    # H1 weight = 20

    if h1 == "bullish":
        score += 20

    elif h1 == "bearish":
        score -= 20

    if score >= 50:

        return {
            "bias": "bullish",
            "score": score
        }

    elif score <= -50:

        return {
            "bias": "bearish",
            "score": score
        }

    return {
        "bias": "mixed",
        "score": score
    }