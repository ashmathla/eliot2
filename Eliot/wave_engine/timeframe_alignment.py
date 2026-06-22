# wave_engine/timeframe_alignment.py

def analyze_alignment(
    weekly_wave,
    daily_wave,
    h1_wave
):

    score = 0

    if weekly_wave["pattern"] == daily_wave["pattern"]:
        score += 35

    if daily_wave["pattern"] == h1_wave["pattern"]:
        score += 35

    if weekly_wave["wave"] == daily_wave["wave"]:
        score += 15

    if daily_wave["wave"] == h1_wave["wave"]:
        score += 15

    aligned = score >= 70

    return {
        "aligned": aligned,
        "score": score
    }