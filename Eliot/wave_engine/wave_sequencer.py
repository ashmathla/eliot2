# wave_engine/wave_sequencer.py


def _validate_bearish(prices: list) -> dict:
    """يتحقق من صحة bearish impulse ويحسب جودته."""
    p1, p2, p3, p4, p5 = prices

    # شرط أساسي: p1 > p3 > p5
    if not (p1 > p3 > p5):
        return {"valid": False, "score": 0}

    wave1 = abs(p2 - p1)
    wave3 = abs(p4 - p3)
    wave5 = abs(p4 - p5)

    if wave1 == 0 or wave3 == 0 or wave5 == 0:
        return {"valid": False, "score": 0}

    score = 100

    # قاعدة 1: wave3 لا تكون الأقصر
    if wave3 < min(wave1, wave5):
        score -= 35

    # قاعدة 2: wave4 لا يتداخل مع wave1
    if p4 >= p1:
        score -= 40

    # قاعدة 3: wave3 هي الأطول (مثالي)
    if wave3 == max(wave1, wave3, wave5):
        score += 10

    # قاعدة 4: wave5 ممتدة جداً
    if wave5 > wave3 * 1.618:
        score -= 10

    return {"valid": score >= 40, "score": max(0, score)}


def _validate_bullish(prices: list) -> dict:
    """يتحقق من صحة bullish impulse ويحسب جودته."""
    p1, p2, p3, p4, p5 = prices

    # شرط أساسي: p1 < p3 < p5
    if not (p1 < p3 < p5):
        return {"valid": False, "score": 0}

    wave1 = abs(p2 - p1)
    wave3 = abs(p4 - p3)
    wave5 = abs(p5 - p4)

    if wave1 == 0 or wave3 == 0 or wave5 == 0:
        return {"valid": False, "score": 0}

    score = 100

    if wave3 < min(wave1, wave5):
        score -= 35

    if p4 <= p1:
        score -= 40

    if wave3 == max(wave1, wave3, wave5):
        score += 10

    if wave5 > wave3 * 1.618:
        score -= 10

    return {"valid": score >= 40, "score": max(0, score)}


def build_wave_sequence(swings: list) -> list:
    if len(swings) < 5:
        return []

    wave_names    = ["wave_1", "wave_2", "wave_3", "wave_4", "wave_5"]
    best_sequence = []
    best_score    = -1
    n             = len(swings)

    bearish_types = ["LOW", "HIGH", "LOW", "HIGH", "LOW"]
    bullish_types = ["HIGH", "LOW", "HIGH", "LOW", "HIGH"]

    for i in range(n - 4):
        window = swings[i: i + 5]
        types  = [x["type"]  for x in window]
        prices = [x["price"] for x in window]

        if types == bearish_types:
            result = _validate_bearish(prices)
        elif types == bullish_types:
            result = _validate_bullish(prices)
        else:
            continue

        if not result["valid"]:
            continue

        # ✅ أضف وزن للحداثة — النافذة الأحدث تأخذ أولوية
        # i=0 → قديم | i=n-5 → أحدث
        recency_bonus = int((i / (n - 4)) * 20)
        final_score   = result["score"] + recency_bonus

        if final_score > best_score:
            best_score    = final_score
            best_sequence = window

    if not best_sequence:
        return []

    return [
        {
            "wave" : wave_names[i],
            "index": swing["index"],
            "price": swing["price"],
            "type" : swing["type"],
        }
        for i, swing in enumerate(best_sequence)
    ]