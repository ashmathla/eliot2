# multi_timeframe_engine/timeframe_loader.py

from data_engine.market_data import get_candles


def load_timeframes(symbol, candle_limit):

    weekly_df = get_candles(
        symbol,
        "W1",
        candle_limit
    )

    daily_df = get_candles(
        symbol,
        "D1",
        candle_limit
    )

    # ── جديد: فريم H4 — تأكيد هيكلي بين D1 وH1 ──
    h4_df = get_candles(
        symbol,
        "H4",
        candle_limit
    )

    h1_df = get_candles(
        symbol,
        "H1",
        candle_limit
    )

    return {
        "W1": weekly_df,
        "D1": daily_df,
        "H4": h4_df,
        "H1": h1_df
    }