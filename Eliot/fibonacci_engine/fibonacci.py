# fibonacci_engine/fibonacci.py

def fibonacci_retracement(high_price, low_price):

    diff = high_price - low_price

    return {
        "23.6": round(high_price - diff * 0.236, 5),
        "38.2": round(high_price - diff * 0.382, 5),
        "50.0": round(high_price - diff * 0.500, 5),
        "61.8": round(high_price - diff * 0.618, 5),
        "78.6": round(high_price - diff * 0.786, 5)
    }


def fibonacci_extension(high_price, low_price):

    diff = high_price - low_price

    return {
        "127.2": round(high_price + diff * 0.272, 5),
        "161.8": round(high_price + diff * 0.618, 5),
        "261.8": round(high_price + diff * 1.618, 5)
    }


def get_swing_high(df, lookback=50):

    return float(
        df["high"].tail(lookback).max()
    )


def get_swing_low(df, lookback=50):

    return float(
        df["low"].tail(lookback).min()
    )


def analyze_fibonacci(df):

    swing_high = get_swing_high(df)

    swing_low = get_swing_low(df)

    retracement = fibonacci_retracement(
        swing_high,
        swing_low
    )

    extension = fibonacci_extension(
        swing_high,
        swing_low
    )

    return {
        "swing_high": round(swing_high, 5),
        "swing_low": round(swing_low, 5),
        "retracement": retracement,
        "extension": extension
    }