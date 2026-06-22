# multi_timeframe_engine/timeframe_summary.py

from trend_engine.weekly_trend import analyze_weekly_trend


def analyze_all_timeframes(data):

    result = {}

    for tf, df in data.items():

        result[tf] = analyze_weekly_trend(df)

    return result