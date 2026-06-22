# trend_engine/weekly_trend.py

import pandas as pd


def calculate_ema(df, period=200):

    return df["close"].ewm(
        span=period,
        adjust=False
    ).mean()


def detect_market_structure(df):

    highs = df["high"].tail(20).tolist()
    lows = df["low"].tail(20).tolist()

    last_high = highs[-1]
    prev_high = highs[-5]

    last_low = lows[-1]
    prev_low = lows[-5]

    bullish = (
        last_high > prev_high
        and
        last_low > prev_low
    )

    bearish = (
        last_high < prev_high
        and
        last_low < prev_low
    )

    if bullish:
        return "bullish"

    if bearish:
        return "bearish"

    return "range"


def detect_bos(df):

    recent_high = df["high"].tail(20).max()

    current_close = df["close"].iloc[-1]

    if current_close > recent_high:
        return "bullish"

    recent_low = df["low"].tail(20).min()

    if current_close < recent_low:
        return "bearish"

    return "none"


def analyze_weekly_trend(df):

    ema = calculate_ema(df)

    current_close = df["close"].iloc[-1]
    current_ema = ema.iloc[-1]

    structure = detect_market_structure(df)
    bos = detect_bos(df)

    primary_trend = (
        "bullish"
        if current_close > current_ema
        else "bearish"
    )

    if primary_trend == structure:

        market_phase = "trend_continuation"

    else:

        market_phase = "correction"

    score = 0

    if primary_trend == "bullish":
        score += 50
    else:
        score -= 50

    if structure == "bullish":
        score += 30

    elif structure == "bearish":
        score -= 30

    if bos == "bullish":
        score += 20

    elif bos == "bearish":
        score -= 20

    return {
        "primary_trend": primary_trend,
        "current_structure": structure,
        "market_phase": market_phase,
        "score": score,
        "ema": round(float(current_ema), 5),
        "close": round(float(current_close), 5),
        "bos": bos
    }

    score = 0

    ema = calculate_ema(df)

    current_close = df["close"].iloc[-1]

    current_ema = ema.iloc[-1]

    structure = detect_market_structure(df)

    bos = detect_bos(df)

    if current_close > current_ema:
        score += 40
    else:
        score -= 40

    if structure == "bullish":
        score += 30

    elif structure == "bearish":
        score -= 30

    if bos == "bullish":
        score += 30

    elif bos == "bearish":
        score -= 30

    if score >= 40:

        trend = "bullish"

    elif score <= -40:

        trend = "bearish"

    else:

        trend = "range"

    return {
        "trend": trend,
        "score": score,
        "ema": round(float(current_ema), 5),
        "close": round(float(current_close), 5),
        "structure": structure,
        "bos": bos
    }