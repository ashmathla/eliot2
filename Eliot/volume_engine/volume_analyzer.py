# volume_engine/volume_analyzer.py

def analyze_volume(df):

    if len(df) < 25:
        return None

    closed_df = df.iloc[:-1]

    current_volume = float(
        closed_df["tick_volume"].iloc[-1]
    )

    average_volume = float(
        closed_df["tick_volume"].tail(20).mean()
    )

    if average_volume == 0:
        wvi = 0
    else:
        wvi = current_volume / average_volume

    if wvi >= 1.5:
        strength = "very_strong"

    elif wvi >= 1.2:
        strength = "strong"

    elif wvi >= 0.8:
        strength = "normal"

    else:
        strength = "weak"

    return {
        "current_volume": round(current_volume, 2),
        "average_volume": round(average_volume, 2),
        "wvi": round(wvi, 2),
        "strength": strength
    }