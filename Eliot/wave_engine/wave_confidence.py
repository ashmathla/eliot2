# wave_engine/wave_confidence.py


def calculate_wave_confidence(
    wave_result,
    fib,
    volume,
    wave_alignment  = None,
    trend_alignment = None,
    elliott_rules   = None,
) -> int:
    """
    يحسب confidence موحّد يعكس جودة الإشارة الكلية.

    المكونات:
        - Elliott confidence الأساسي  : 40%
        - Elliott Rules (صحة الموجات) : 20%
        - Wave Alignment               : 20%
        - Volume Confirmation          : 10%
        - Trend Alignment              : 10%

    Returns: int بين 0 و 100
    """

    # ── 1. Elliott Confidence الأساسي (40%) ──
    elliott_conf = int(wave_result.get("confidence", 50))
    component_elliott = int(elliott_conf * 0.40)

    # ── 2. Elliott Rules (20%) ────────────────
    if elliott_rules is not None:
        rules_score   = int(elliott_rules.get("score", 50))
        rules_valid   = elliott_rules.get("valid", True)
        rules_reasons = elliott_rules.get("reasons", [])

        # خصم إضافي لكل خرق
        penalty = len(rules_reasons) * 5
        rules_score = max(0, rules_score - penalty)

        if not rules_valid:
            rules_score = min(rules_score, 30)

        component_rules = int(rules_score * 0.20)
    else:
        component_rules = int(50 * 0.20)  # افتراضي

    # ── 3. Wave Alignment (20%) ───────────────
    if wave_alignment is not None:
        align_score = int(wave_alignment.get("score", 0))
        aligned     = wave_alignment.get("aligned", False)

        if not aligned:
            align_score = min(align_score, 50)

        component_align = int(align_score * 0.20)
    else:
        component_align = 0

    # ── 4. Volume Confirmation (10%) ──────────
    wave_name       = wave_result.get("current_wave", "")
    volume_strength = volume.get("strength", "weak") if volume else "weak"

    volume_score = 50  # افتراضي

    if wave_name == "wave_3":
        if volume_strength == "very_strong" : volume_score = 100
        elif volume_strength == "strong"    : volume_score = 80
        elif volume_strength == "normal"    : volume_score = 60
        else                                : volume_score = 20

    elif wave_name in ("wave_5", "wave_C"):
        if volume_strength in ("normal", "strong", "very_strong"):
            volume_score = 70
        else:
            volume_score = 40

    elif wave_name == "wave_B":
        volume_score = 70 if volume_strength == "weak" else 50

    component_volume = int(volume_score * 0.10)

    # ── 5. Fibonacci Confirmation (bonus) ─────
    fib_bonus = 0
    if fib is not None:
        retracement = fib.get("retracement", {})
        swing_high  = fib.get("swing_high", 0)
        swing_low   = fib.get("swing_low",  0)

        # تحقق من وجود مستويات Fibonacci منطقية
        level_618 = retracement.get("61.8", 0)
        level_382 = retracement.get("38.2", 0)

        if swing_high > 0 and swing_low > 0 and level_618 > 0:
            fib_bonus = 3  # بونص صغير لوجود Fib صحيح

    # ── 6. Trend Alignment (10%) ──────────────
    if trend_alignment is not None:
        trend_score     = int(trend_alignment.get("score", 0))
        component_trend = int(trend_score * 0.10)
    else:
        component_trend = 0

    # ── التجميع النهائي ───────────────────────
    confidence = (
        component_elliott
        + component_rules
        + component_align
        + component_volume
        + component_trend
        + fib_bonus
    )

    return max(0, min(confidence, 100))


def get_confidence_breakdown(
    wave_result,
    fib,
    volume,
    wave_alignment  = None,
    trend_alignment = None,
    elliott_rules   = None,
) -> dict:
    """
    نفس الحساب لكن يُرجع تفصيل كل مكوّن للمراجعة.
    """
    elliott_conf      = int(wave_result.get("confidence", 50))
    component_elliott = int(elliott_conf * 0.40)

    if elliott_rules is not None:
        rules_score   = int(elliott_rules.get("score", 50))
        rules_valid   = elliott_rules.get("valid", True)
        rules_reasons = elliott_rules.get("reasons", [])
        penalty       = len(rules_reasons) * 5
        rules_score   = max(0, rules_score - penalty)
        if not rules_valid:
            rules_score = min(rules_score, 30)
        component_rules = int(rules_score * 0.20)
    else:
        component_rules = int(50 * 0.20)

    if wave_alignment is not None:
        align_score = int(wave_alignment.get("score", 0))
        aligned     = wave_alignment.get("aligned", False)
        if not aligned:
            align_score = min(align_score, 50)
        component_align = int(align_score * 0.20)
    else:
        component_align = 0

    wave_name       = wave_result.get("current_wave", "")
    volume_strength = volume.get("strength", "weak") if volume else "weak"
    volume_score    = 50

    if wave_name == "wave_3":
        if volume_strength == "very_strong" : volume_score = 100
        elif volume_strength == "strong"    : volume_score = 80
        elif volume_strength == "normal"    : volume_score = 60
        else                                : volume_score = 20
    elif wave_name in ("wave_5", "wave_C"):
        volume_score = 70 if volume_strength in ("normal", "strong", "very_strong") else 40
    elif wave_name == "wave_B":
        volume_score = 70 if volume_strength == "weak" else 50

    component_volume = int(volume_score * 0.10)

    fib_bonus = 0
    if fib is not None:
        retracement = fib.get("retracement", {})
        level_618   = retracement.get("61.8", 0)
        swing_high  = fib.get("swing_high", 0)
        swing_low   = fib.get("swing_low",  0)
        if swing_high > 0 and swing_low > 0 and level_618 > 0:
            fib_bonus = 3

    if trend_alignment is not None:
        trend_score     = int(trend_alignment.get("score", 0))
        component_trend = int(trend_score * 0.10)
    else:
        component_trend = 0

    total = max(0, min(
        component_elliott + component_rules + component_align
        + component_volume + component_trend + fib_bonus,
        100
    ))

    return {
        "total"            : total,
        "elliott_conf_40%" : component_elliott,
        "rules_score_20%"  : component_rules,
        "alignment_20%"    : component_align,
        "volume_10%"       : component_volume,
        "trend_10%"        : component_trend,
        "fib_bonus"        : fib_bonus,
    }