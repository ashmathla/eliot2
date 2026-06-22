# structure_engine/choch_detector.py

def detect_choch(summary):

    weekly = summary["W1"]["primary_trend"]
    daily = summary["D1"]["primary_trend"]

    if weekly == "bearish" and daily == "bullish":

        return {
            "choch": "bullish_correction",
            "message": "daily counter trend move"
        }

    if weekly == "bullish" and daily == "bearish":

        return {
            "choch": "bearish_correction",
            "message": "daily counter trend move"
        }

    return {
        "choch": "none",
        "message": "trend aligned"
    }