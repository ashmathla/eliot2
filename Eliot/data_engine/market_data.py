# data_engine/market_data.py

import MetaTrader5 as mt5
import pandas as pd

TIMEFRAME_MAP = {
    "W1": mt5.TIMEFRAME_W1,
    "D1": mt5.TIMEFRAME_D1,
    "H4": mt5.TIMEFRAME_H4,
    "H1": mt5.TIMEFRAME_H1,
}


def get_candles(symbol, timeframe, count=500):

    rates = mt5.copy_rates_from_pos(
        symbol,
        TIMEFRAME_MAP[timeframe],
        0,
        count
    )

    if rates is None:
        return None

    df = pd.DataFrame(rates)

    df["time"] = pd.to_datetime(
        df["time"],
        unit="s"
    )

    return df