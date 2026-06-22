# wave_engine/wave_alignment.py

# ── تصنيف الأنماط ─────────────────────────────
BEARISH_PATTERNS = {"bearish_impulse", "bearish_ABC"}
BULLISH_PATTERNS = {"bullish_impulse", "bullish_ABC"}

# CHANGE: كانت تحتوي فقط "ABC" الحرفية. بعد تعديل correction_detector.py
# صرنا نُرجع أسماء تصحيح أدق (zigzag, flat, triangle...)، وهذا الملف
# ما كان يتعرف عليها، فيصنّفها "unknown" ويحسبها "تعارض حقيقي" بدل
# "تصحيح طبيعي". أضفنا كل الأنماط التصحيحية المعروفة هنا.
CORRECTION_PATTERNS = {"ABC", "zigzag", "flat", "triangle"}

LATE_WAVES  = {"wave_4", "wave_5", "wave_C"}
EARLY_WAVES = {"wave_1", "wave_2", "wave_3", "wave_A", "wave_B"}


def _get_bias(pattern: str) -> str:
    """استخراج الاتجاه من اسم النمط."""
    if pattern in BEARISH_PATTERNS:
        return "bearish"
    if pattern in BULLISH_PATTERNS:
        return "bullish"
    # CHANGE: كانت `if pattern == "ABC"` فقط — الآن أي نمط تصحيحي معروف
    if pattern in CORRECTION_PATTERNS:
        return "correction"
    return "unknown"


def _is_corrective_relationship(
    parent_pattern: str,
    child_pattern: str
) -> bool:
    """
    هل child_pattern هو تصحيح طبيعي داخل parent_pattern؟
    مثال: W1=bearish_impulse و D1=zigzag (تصحيح صاعد) = تصحيح طبيعي ✅
    """
    parent_bias = _get_bias(parent_pattern)
    child_bias  = _get_bias(child_pattern)

    if parent_bias == "bearish" and child_bias == "bullish":
        return True
    if parent_bias == "bullish" and child_bias == "bearish":
        return True

    # CHANGE: كانت `if child_pattern == "ABC"` (مطابقة حرفية فقط).
    # الآن: أي نمط تصحيحي معروف (zigzag/flat/triangle/ABC) يُعتبر
    # تصحيحاً طبيعياً محتملاً داخل أي parent impulse/correction،
    # بغض النظر عن اسمه الدقيق.
    if child_bias == "correction":
        return True

    return False


def _score_pattern_pair(
    parent_pattern: str,
    child_pattern: str,
    weight: int,
    parent_direction: str = None,
    child_direction: str = None,
) -> tuple:
    """
    يحسب score وسبب العلاقة بين timeframe أب وطفل.

    CHANGE: بدل الاعتماد فقط على تخمين bias من اسم الـ pattern
    (اللي يفشل لما parent نفسه correction مثل zigzag)، نستخدم أولاً
    حقل `direction` الفعلي (up/down) المحسوب مباشرة من الأسعار —
    وهو متوفر أصلاً بـ wave_map[tf]["direction"]. هذا يحل حالة
    "H4=zigzag(up) ↔ H1=bullish_impulse(up)" بشكل صحيح: نفس
    الاتجاه الفعلي = توافق، بغض النظر عن اسمي الـ pattern.

    Returns: (score, reason)
    """
    # توافق كامل (نفس الـ pattern بالضبط)
    if parent_pattern == child_pattern:
        return weight, f"توافق كامل ({parent_pattern})"

    # الأولوية: قارن الاتجاه الفعلي إذا كان متوفراً
    if parent_direction in ("up", "down") and child_direction in ("up", "down"):
        if parent_direction == child_direction:
            return int(weight * 0.9), (
                f"توافق اتجاه فعلي ({child_pattern} نفس اتجاه {parent_pattern})"
            )
        # اتجاه معاكس: تحقق هل هذا تصحيح طبيعي متوقع
        if _is_corrective_relationship(parent_pattern, child_pattern):
            return int(weight * 0.75), f"تصحيح طبيعي ({child_pattern} داخل {parent_pattern})"
        return int(weight * 0.1), f"تعارض اتجاه فعلي ({parent_pattern} vs {child_pattern})"

    # احتياطي: لا يوجد direction متاح، نرجع لمنطق اسم الـ pattern القديم
    if _is_corrective_relationship(parent_pattern, child_pattern):
        return int(weight * 0.75), f"تصحيح طبيعي ({child_pattern} داخل {parent_pattern})"

    parent_bias = _get_bias(parent_pattern)
    child_bias  = _get_bias(child_pattern)
    if parent_bias == child_bias:
        return int(weight * 0.5), f"توافق اتجاه جزئي"

    return int(weight * 0.1), f"تعارض ({parent_pattern} vs {child_pattern})"


def _score_wave_position(
    w1_wave: str,
    d1_wave: str,
    h1_wave: str,
    w1_pattern: str,
    d1_pattern: str,
) -> tuple:
    """
    يحسب score بناءً على موقع الموجات.
    Returns: (score, reasons)
    """
    score   = 0
    reasons = []

    if (
        w1_wave in LATE_WAVES
        and d1_wave in LATE_WAVES
        and h1_wave in LATE_WAVES
    ):
        score += 20
        reasons.append("الثلاثة في مراحل متأخرة — دخول قريب")

    elif w1_wave in LATE_WAVES and d1_wave in LATE_WAVES:
        score += 10
        reasons.append("W1 و D1 في مرحلة متأخرة")

    if h1_wave == "wave_C":
        score += 15
        reasons.append("H1 wave_C — نهاية التصحيح مؤكدة")
    elif h1_wave == "wave_5":
        score += 10
        reasons.append("H1 wave_5 — نهاية impulse")

    if w1_wave in EARLY_WAVES:
        score -= 5
        reasons.append("W1 في مرحلة مبكرة — توخ الحذر")

    return score, reasons


def calculate_wave_alignment(wave_map: dict) -> dict:
    """
    يحسب مستوى التوافق بين W1 و D1 و H4 و H1.
    """

    w1_elliott = wave_map.get("W1", {}).get("elliott", {})
    d1_elliott = wave_map.get("D1", {}).get("elliott", {})
    h1_elliott = wave_map.get("H1", {}).get("elliott", {})
    h4_data    = wave_map.get("H4")
    h4_elliott = h4_data.get("elliott", {}) if h4_data else None

    if not w1_elliott or not d1_elliott or not h1_elliott:
        return {"aligned": False, "score": 0, "details": ["بيانات ناقصة"]}

    w1_pattern = w1_elliott.get("pattern", "")
    d1_pattern = d1_elliott.get("pattern", "")
    h1_pattern = h1_elliott.get("pattern", "")

    w1_wave = w1_elliott.get("current_wave", "")
    d1_wave = d1_elliott.get("current_wave", "")
    h1_wave = h1_elliott.get("current_wave", "")

    # CHANGE: استخرج direction الفعلي لكل فريم (موجود أصلاً بـwave_map
    # من تعديل multi_tf_wave_engine.py السابق)
    w1_direction = wave_map.get("W1", {}).get("direction")
    d1_direction = wave_map.get("D1", {}).get("direction")
    h1_direction = wave_map.get("H1", {}).get("direction")

    score   = 0
    details = []

    if h4_elliott:
        h4_pattern = h4_elliott.get("pattern", "")
        h4_wave    = h4_elliott.get("current_wave", "")
        h4_direction = wave_map.get("H4", {}).get("direction")

        s, r = _score_pattern_pair(w1_pattern, d1_pattern, 25, w1_direction, d1_direction)
        score += s
        details.append(f"W1↔D1: {r} (+{s})")

        s, r = _score_pattern_pair(d1_pattern, h4_pattern, 25, d1_direction, h4_direction)
        score += s
        details.append(f"D1↔H4: {r} (+{s})")

        s, r = _score_pattern_pair(h4_pattern, h1_pattern, 25, h4_direction, h1_direction)
        score += s
        details.append(f"H4↔H1: {r} (+{s})")

        s, reasons = _score_wave_position(
            w1_wave, d1_wave, h1_wave,
            w1_pattern, d1_pattern
        )
        s = int(s * (25 / 30))
        score += s
        details.extend(reasons)

    else:
        s, r = _score_pattern_pair(w1_pattern, d1_pattern, 35, w1_direction, d1_direction)
        score += s
        details.append(f"W1↔D1: {r} (+{s})")

        s, r = _score_pattern_pair(d1_pattern, h1_pattern, 35, d1_direction, h1_direction)
        score += s
        details.append(f"D1↔H1: {r} (+{s})")

        s, reasons = _score_wave_position(
            w1_wave, d1_wave, h1_wave,
            w1_pattern, d1_pattern
        )
        score += s
        details.extend(reasons)

    score   = max(0, min(score, 100))
    aligned = score >= 55

    return {
        "aligned": aligned,
        "score"  : score,
        "details": details,
    }