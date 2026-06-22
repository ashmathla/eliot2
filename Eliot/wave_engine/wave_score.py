# wave_engine/wave_score.py

def calculate_wave_score(
    elliott,
    wave_context,
    wave_alignment
):

    score = 50

    pattern = elliott["pattern"]

    confidence = elliott["confidence"]

    if pattern in [
        "bullish_impulse",
        "bearish_impulse"
    ]:

        score += 20

    elif pattern == "ABC_correction":

        score += 10

    if confidence >= 80:

        score += 10

    elif confidence >= 60:

        score += 5

    if wave_alignment["aligned"]:

        score += 20

    return min(score, 100)