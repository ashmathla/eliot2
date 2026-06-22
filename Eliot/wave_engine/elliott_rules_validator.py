# wave_engine/elliott_rules_validator.py


def validate_elliott_rules(sequence: list) -> dict:
    print("\nVALIDATOR RUNNING")

    if len(sequence) < 5:
        return {
            "valid"  : False,
            "score"  : 0,
            "reasons": ["insufficient_waves"]
        }

    p1 = sequence[0]["price"]
    p2 = sequence[1]["price"]
    p3 = sequence[2]["price"]
    p4 = sequence[3]["price"]
    p5 = sequence[4]["price"]

    score   = 100
    reasons = []

    # ── Bearish Structure: p1 > p3 > p5 ──────
    if p1 > p3 > p5:

        wave1 = abs(p2 - p1)
        wave3 = abs(p4 - p3)
        wave5 = abs(p4 - p5)

        # قاعدة 1: wave3 لا تكون الأقصر (خصم 35)
        if wave3 < min(wave1, wave5):
            score -= 35
            reasons.append("wave3_shortest")

        # قاعدة 2: wave4 لا تتداخل مع wave1 (خصم 25)
        if p4 >= p1:
            score -= 25
            reasons.append("wave4_overlaps_wave1")

        # قاعدة 3: wave5 ممتدة جداً (خصم 10)
        if wave3 > 0 and wave5 > wave3 * 1.618:
            score -= 10
            reasons.append("wave5_extended")

        return {
            "valid"  : score >= 50,
            "score"  : max(score, 0),
            "reasons": reasons
        }

    # ── Bullish Structure: p1 < p3 < p5 ──────
    if p1 < p3 < p5:

        wave1 = abs(p2 - p1)
        wave3 = abs(p4 - p3)
        wave5 = abs(p5 - p4)

        # قاعدة 1: wave3 لا تكون الأقصر (خصم 35)
        if wave3 < min(wave1, wave5):
            score -= 35
            reasons.append("wave3_shortest")

        # قاعدة 2: wave4 لا تتداخل مع wave1 (خصم 25)
        if p4 <= p1:
            score -= 25
            reasons.append("wave4_overlaps_wave1")

        # قاعدة 3: wave5 ممتدة جداً (خصم 10)
        if wave3 > 0 and wave5 > wave3 * 1.618:
            score -= 10
            reasons.append("wave5_extended")

        return {
            "valid"  : score >= 50,
            "score"  : max(score, 0),
            "reasons": reasons
        }

    # ── هيكل غير معروف ────────────────────────
    return {
        "valid"  : False,
        "score"  : 20,
        "reasons": ["invalid_structure"]
    }