def get_wave_bias(wave_data):

    pattern = wave_data["wave_type"]

    if pattern == "bullish_impulse":
        return "bullish"

    if pattern == "bearish_impulse":
        return "bearish"

    return "neutral"

def get_next_wave_bias(wave_data):

    pattern = wave_data["wave_type"]

    current_wave = wave_data["current_wave"]

    context = wave_data["context"]

    next_expected = context["next_expected"]

    if (
        pattern == "bullish_impulse"
        and current_wave == "wave_5"
        and next_expected == "wave_A"
    ):
        return "bearish"

    if (
        pattern == "bearish_impulse"
        and current_wave == "wave_5"
        and next_expected == "wave_A"
    ):
        return "bullish"

    return "neutral"