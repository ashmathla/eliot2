# recommendation_engine/conflict_resolver.py

# CHANGE: نفس مجموعة الأنماط التصحيحية المستخدمة بـ wave_alignment.py
# (كانت الدالة هنا تتعرف فقط على "ABC" الحرفية، فتفشل مع zigzag/flat/triangle)
CORRECTION_PATTERNS = {"ABC", "zigzag", "flat", "triangle"}


def _bias_of(pattern: str, direction: str | None = None) -> str | None:
    """
    يحدد الـ bias الفعلي ("bullish"/"bearish") لأي pattern.

    CHANGE (الإصلاح الجوهري): قبل، كل الكود بهذا الملف كان يفحص
    `"bullish" in pattern` أو `"bearish" in pattern` مباشرة على
    النص — وهذا يفشل تماماً مع أي pattern تصحيحي اسمه لا يحمل
    الاتجاه بالحرف (zigzag, flat, triangle). الآن:
        1. لو الاسم نفسه يحمل اتجاه واضح (bullish_impulse,
           bearish_impulse, bullish_ABC, bearish_ABC) → نستخدمه مباشرة.
        2. غير كذلك (zigzag/flat/triangle/ABC العامة) → نستخدم
           `direction` الفعلي (up/down) الممرر من wave_map، وهو
           محسوب من الأسعار الخام لا من اسم الـ pattern.
        3. لو ما توفر direction ولا اتجاه بالاسم → None (غير محدد).
    """
    if "bullish_impulse" in pattern or pattern == "bullish_ABC":
        return "bullish"
    if "bearish_impulse" in pattern or pattern == "bearish_ABC":
        return "bearish"

    if direction == "up":
        return "bullish"
    if direction == "down":
        return "bearish"

    return None


def _is_correction(pattern: str) -> bool:
    return pattern in CORRECTION_PATTERNS


def _is_undefined(pattern: str) -> bool:
    """
    يفحص ما إذا كان pattern غير محدد (unknown أو empty).
    """
    return pattern in ("unknown", "", None)


def _check_h4_confirmation(
    primary_bias: str, h4_elliott: dict, h4_direction: str | None = None
) -> dict:
    """
    يفحص ما إذا كان H4 يؤكد primary_bias (القادم من W1+D1) أم يعارضه.
    """
    h4_pattern = h4_elliott.get("pattern", "")

    expected_impulse = (
        "bullish_impulse" if primary_bias == "bullish" else "bearish_impulse"
    )
    opposite_impulse = (
        "bearish_impulse" if primary_bias == "bullish" else "bullish_impulse"
    )

    if h4_pattern == expected_impulse:
        return {
            "confirmed": True,
            "strength" : "full",
            "reason"   : f"H4 {h4_pattern} يؤكد {primary_bias} بقوة كاملة",
        }

    if h4_pattern == opposite_impulse:
        return {
            "confirmed": False,
            "strength" : "none",
            "reason"   : f"H4 {h4_pattern} يعارض {primary_bias} هيكلياً — تعارض حقيقي",
        }

    # CHANGE: كانت `h4_pattern == "ABC"` فقط — الآن أي نمط تصحيحي معروف
    if _is_correction(h4_pattern):
        h4_bias = _bias_of(h4_pattern, h4_direction)
        if h4_bias is not None and h4_bias != primary_bias:
            # تصحيح فعلي معاكس لـ primary_bias = طبيعي ومتوقع
            return {
                "confirmed": True,
                "strength" : "partial",
                "reason"   : (
                    f"H4 في تصحيح {h4_pattern} — لا يعارض {primary_bias} "
                    f"لكن لا يؤكده بالكامل"
                ),
            }
        if h4_bias is not None and h4_bias == primary_bias:
            # تصحيح لكن اتجاهه الفعلي مع نفس primary_bias — تأكيد كامل تقريباً
            return {
                "confirmed": True,
                "strength" : "full",
                "reason"   : (
                    f"H4 ({h4_pattern}) اتجاهه الفعلي يوافق {primary_bias}"
                ),
            }
        return {
            "confirmed": True,
            "strength" : "partial",
            "reason"   : f"H4 في تصحيح {h4_pattern} — اتجاه غير محدد، يُسمح بثقة جزئية",
        }

    return {
        "confirmed": True,
        "strength" : "partial",
        "reason"   : f"H4 ({h4_pattern}) غير حاسم — يُسمح بالاستمرار بثقة جزئية",
    }


def resolve_timeframe_conflict(
    w1_elliott: dict,
    d1_elliott: dict,
    h1_elliott: dict,
    h4_elliott: dict | None = None,
    w1_direction: str | None = None,
    d1_direction: str | None = None,
    h4_direction: str | None = None,
) -> dict:
    """
    يحل التعارض بين timeframes ويحدد السياق الحقيقي.
    القاعدة: W1 > D1 > H4 > H1.

    ✅ CHANGE: الآن يتعامل مع حالة D1 = unknown
    لو W1 واضح و D1 غير محدد → لا تعارض، بل "undefined D1"
    يسمح بدخول بناءً على W1 لكن مع تنبيه انتظار تأكيد D1

    CHANGE: تستقبل الآن w1_direction/d1_direction/h4_direction
    (اختيارية، تأتي من wave_map[tf]["direction"]) لتحديد الـ bias
    الفعلي لأي pattern تصحيحي (zigzag/flat/triangle) بدل الاعتماد
    فقط على وجود كلمة bullish/bearish بالاسم.
    """

    w1_pattern = w1_elliott.get("pattern", "")
    d1_pattern = d1_elliott.get("pattern", "")
    w1_next    = w1_elliott.get("next_wave", "")
    d1_next    = d1_elliott.get("next_wave", "")

    w1_bias = _bias_of(w1_pattern, w1_direction)
    d1_bias = _bias_of(d1_pattern, d1_direction)

    d1_is_undefined = _is_undefined(d1_pattern)

    # هل D1 اكتملت؟
    if _is_correction(d1_pattern):
        d1_completed = d1_next == "trend_resumption"
    else:
        d1_completed = d1_next == "wave_A"

    base_result = None

    # ══════════════════════════════════════════════════════════════════════════
    # ✅ CASE UNDEFINED: W1 واضح لكن D1 غير محدد (unknown)
    # ──────────────────────────────────────────────────────────────────────────
    # المشكلة السابقة: كانت تعود تعارض مباشرة
    # الحل الجديد: نقبل W1 لكن مع تنبيه انتظار تأكيد D1
    # ══════════════════════════════════════════════════════════════════════════
    if (
        base_result is None
        and w1_bias is not None
        and w1_next == "wave_A"  # W1 انتهى من impulse
        and d1_is_undefined  # ← المفتاح: D1 لا توجد بيانات كافية
    ):
        primary_bias = w1_bias
        action_verb  = "BUY" if primary_bias == "bullish" else "SELL"

        base_result = {
            "conflict"    : False,  # ✅ ليس تعارضاً — D1 فقط غير محدد
            "context"     : (
                f"W1={w1_pattern} واضح ({primary_bias}) لكن D1 بدون بيانات كافية "
                f"— انتظر تأكيد D1"
            ),
            "primary_bias": primary_bias,
            "d1_role"     : "undefined",  # بدل "conflicting"
            "d1_completed": False,
            "action"      : f"انتظر تأكيد D1 قبل {action_verb}",
            "entry_timing": "D1_confirmation",
        }

    # ══════════════════════════════════════════════════════════════════════════
    # CASE NEW: W1 انتهى من impulse + D1 = تصحيح (أي نمط تصحيحي)
    # ══════════════════════════════════════════════════════════════════════════
    if base_result is None and w1_next == "wave_A" and _is_correction(d1_pattern):

        primary_bias = w1_bias
        action_verb  = "BUY" if primary_bias == "bullish" else (
            "SELL" if primary_bias == "bearish" else None
        )

        if primary_bias is not None:
            if d1_completed:
                base_result = {
                    "conflict"    : False,
                    "context"     : (
                        f"D1={d1_pattern} هو تصحيح W1 المتوقع وقد اكتمل "
                        f"— استمرار {primary_bias}"
                    ),
                    "primary_bias": primary_bias,
                    "d1_role"     : "corrective_wave_A_completed",
                    "d1_completed": True,
                    "action"      : f"{action_verb} عند تأكيد H1",
                    "entry_timing": "H1",
                }
            else:
                base_result = {
                    "conflict"    : False,
                    "context"     : (
                        f"D1={d1_pattern} هو تصحيح W1 المتوقع — لا يزال جارياً"
                    ),
                    "primary_bias": primary_bias,
                    "d1_role"     : "corrective_wave_A_in_progress",
                    "d1_completed": False,
                    "action"      : f"انتظر اكتمال D1 قبل {action_verb}",
                    "entry_timing": "H1",
                }

    # ══════════════════════════════════════════════════════════════════════════
    # CASE A/B: W1 انتهى impulse + D1 تصحيح بعكس اتجاه W1
    # (نفس فكرة CASE NEW لكن بدون شرط w1_next == "wave_A" الحرفي،
    # تغطي أي تصحيح فعلي بعكس اتجاه W1 بغض النظر عن next_wave)
    # ══════════════════════════════════════════════════════════════════════════
    if (
        base_result is None
        and w1_bias is not None
        and w1_next == "wave_A"
        and d1_bias is not None
        and d1_bias != w1_bias
    ):
        action_verb = "SELL" if w1_bias == "bearish" else "BUY"
        if d1_completed:
            base_result = {
                "conflict"    : False,
                "context"     : f"تصحيح W1 اكتمل ({d1_pattern}) — استمرار {w1_bias} متوقع",
                "primary_bias": w1_bias,
                "d1_role"     : "corrective_wave_A_completed",
                "d1_completed": True,
                "action"      : f"{action_verb} عند تأكيد H1",
                "entry_timing": "H1",
            }
        else:
            base_result = {
                "conflict"    : False,
                "context"     : f"تصحيح W1 ({d1_pattern}) لا يزال جارياً — انتظر اكتماله",
                "primary_bias": w1_bias,
                "d1_role"     : "corrective_wave_A_in_progress",
                "d1_completed": False,
                "action"      : f"انتظر اكتمال D1 قبل {action_verb}",
                "entry_timing": "H1",
            }

    # ══════════════════════════════════════════════════════════════════════════
    # CASE C: توافق كامل W1+D1 — نفس bias الفعلي
    # CHANGE: بدل `"bearish" in w1_pattern and "bearish" in d1_pattern`
    # (يفشل مع zigzag)، نقارن w1_bias/d1_bias الفعليين.
    # ══════════════════════════════════════════════════════════════════════════
    if (
        base_result is None
        and w1_bias is not None
        and d1_bias is not None
        and w1_bias == d1_bias
    ):
        action_verb = "SELL" if w1_bias == "bearish" else "BUY"
        label = "هبوطي" if w1_bias == "bearish" else "صعودي"
        base_result = {
            "conflict"    : False,
            "context"     : f"توافق {label} كامل W1+D1 (W1={w1_pattern}, D1={d1_pattern})",
            "primary_bias": w1_bias,
            "d1_role"     : "aligned",
            "d1_completed": d1_completed,
            "action"      : f"{action_verb} عند تأكيد H1",
            "entry_timing": "H1",
        }

    # ═════════════════════════════════════════════════════��════════════════════
    # CASE D: تعارض مؤقت — W1 لسه في منتصف impulse، D1 بعكسه تماماً
    # (D1 نفسه impulse معاكس، مو تصحيح طبيعي)
    # ══════════════════════════════════════════════════════════════════════════
    if (
        base_result is None
        and w1_bias is not None
        and d1_bias is not None
        and d1_bias != w1_bias
        and w1_next not in ("wave_A", "")
        and not _is_correction(d1_pattern)
    ):
        base_result = {
            "conflict"    : True,
            "context"     : f"W1 لا يزال في impulse و D1 عكسه — تعارض مؤقت",
            "primary_bias": w1_bias,
            "d1_role"     : "conflicting",
            "d1_completed": False,
            "action"      : "انتظر وضوح W1 قبل الدخول",
            "entry_timing": None,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # الحالة الافتراضية: تعارض حقيقي (أو بيانات غير كافية لتحديد اتجاه)
    # ══════════════════════════════════════════════════════════════════════════
    if base_result is None:
        base_result = {
            "conflict"    : True,
            "context"     : f"تعارض حقيقي: W1={w1_pattern} vs D1={d1_pattern}",
            "primary_bias": "neutral",
            "d1_role"     : "conflicting",
            "d1_completed": False,
            "action"      : "NO_TRADE — انتظر وضوح الاتجاه",
            "entry_timing": None,
        }

    base_result["h4_role"]      = "not_checked"
    base_result["h4_confirmed"] = None

    if (
        h4_elliott is not None
        and not base_result["conflict"]
        and base_result["primary_bias"] in ("bullish", "bearish")
    ):
        h4_check = _check_h4_confirmation(
            base_result["primary_bias"], h4_elliott, h4_direction
        )

        base_result["h4_role"]      = h4_check["strength"]
        base_result["h4_confirmed"] = h4_check["confirmed"]

        if not h4_check["confirmed"]:
            primary_bias = base_result["primary_bias"]
            action_verb  = "SELL" if primary_bias == "bearish" else "BUY"

            base_result["context"] += f" | H4 يعارض: {h4_check['reason']}"
            base_result["action"]   = f"انتظر — H4 يعارض {action_verb} حالياً"
            base_result["entry_timing"] = None
        else:
            base_result["context"] += f" | H4: {h4_check['reason']}"

    return base_result


def get_entry_signal(
    conflict_result: dict,
    h1_elliott: dict,
    confidence: float | None = None,
) -> str:
    """
    يحدد إشارة الدخول النهائية بناءً على H1.
    
    ✅ CHANGE: الآن يتعامل مع d1_role = "undefined"
    إذا كان D1 غير محدد، نسمح بـ WAIT_BUY/WAIT_SELL بدل NO_TRADE
    """

    if conflict_result["conflict"]:
        return "NO_TRADE"

    primary_bias  = conflict_result["primary_bias"]
    d1_role       = conflict_result.get("d1_role", "")
    d1_completed  = conflict_result.get("d1_completed", False)

    h4_confirmed = conflict_result.get("h4_confirmed", None)
    h4_blocked   = h4_confirmed is False

    h1_pattern = h1_elliott.get("pattern", "")
    h1_wave    = h1_elliott.get("current_wave", "")
    h1_next    = h1_elliott.get("next_wave", "")

    is_strong = confidence is not None and confidence >= 75

    print(f"\nENTRY SIGNAL DEBUG")
    print(f"primary_bias={primary_bias} | d1_role={d1_role} | d1_completed={d1_completed}")
    print(f"h4_confirmed={h4_confirmed} | h4_blocked={h4_blocked}")
    print(f"h1_pattern={h1_pattern} | h1_wave={h1_wave} | h1_next={h1_next}")
    print(f"confidence={confidence} | is_strong={is_strong}")

    if primary_bias == "bearish":

        if h4_blocked:
            return "WAIT_SELL"

        # ✅ CHANGE: إذا كان D1 غير محدد، نعامله مثل "in_progress"
        if not d1_completed and d1_role in ("corrective_wave_A_in_progress", "undefined"):
            return "WAIT_SELL"

        if d1_completed or d1_role == "aligned":

            now_signal = "STRONG_SELL" if is_strong else "SELL_NOW"

            if (
                h1_pattern == "ABC"
                and h1_wave == "wave_C"
                and h1_next == "trend_resumption"
            ):
                return now_signal

            if "bearish_impulse" in h1_pattern:
                return now_signal

            if h1_pattern == "ABC" and h1_wave != "wave_C":
                return "WAIT_SELL"

            if "bullish" in h1_pattern:
                return "WAIT_SELL"

        return "WAIT_SELL"

    if primary_bias == "bullish":

        if h4_blocked:
            return "WAIT_BUY"

        # ✅ CHANGE: إذا كان D1 غير محدد، نعامله مثل "in_progress"
        if not d1_completed and d1_role in ("corrective_wave_A_in_progress", "undefined"):
            return "WAIT_BUY"

        if d1_completed or d1_role == "aligned":

            now_signal = "STRONG_BUY" if is_strong else "BUY_NOW"

            if (
                h1_pattern == "ABC"
                and h1_wave == "wave_C"
                and h1_next == "trend_resumption"
            ):
                return now_signal

            if "bullish_impulse" in h1_pattern:
                return now_signal

            if h1_pattern == "ABC" and h1_wave != "wave_C":
                return "WAIT_BUY"

            if "bearish" in h1_pattern:
                return "WAIT_BUY"

        return "WAIT_BUY"

    return "WAIT"


def classify_signal_mode(entry_signal: str, bos: dict) -> dict:
    bos_direction = ""
    if isinstance(bos, dict):
        bos_direction = str(bos.get("direction", "")).lower()

    has_bos = bos_direction in ("bullish", "bearish")

    immediate_sell = ("SELL_NOW", "STRONG_SELL")
    immediate_buy  = ("BUY_NOW", "STRONG_BUY")

    if entry_signal in immediate_sell + immediate_buy:

        expected_bos_dir = "bearish" if entry_signal in immediate_sell else "bullish"

        if has_bos and bos_direction == expected_bos_dir:
            return {
                "mode"        : "CONFIRMED",
                "final_signal": entry_signal,
                "note"        : "Elliott + BOS متوافقان — دخول مؤكد",
            }

        return {
            "mode"        : "AGGRESSIVE",
            "final_signal": f"{entry_signal}_EARLY",
            "note"        : "إشارة استباقية — بدون تأكيد BOS، يُفضّل حجم مخاطرة أصغر أو انتظار retest",
        }

    return {
        "mode"        : "WAIT",
        "final_signal": entry_signal,
        "note"        : "لا تغيير",
    }
