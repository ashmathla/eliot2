# recommendation_engine/signal_engine.py
"""
Signal Engine with Phase-Based Entry Logic

التحديثات:
- شروط دقيقة للإشارات بناءً على phase و subwave
- منع إشارات SELL_NOW إذا كانت wave_C لم تكتمل بعد
- WAIT_SELL بدلاً من SELL_NOW للتصحيحات الجارية
"""

from enum import Enum


class Bias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class Pattern(str, Enum):
    BULLISH_IMPULSE = "bullish_impulse"
    BEARISH_IMPULSE = "bearish_impulse"


def build_signal(
    weekly_bias    : str,
    daily_bias     : str,
    h1_bias        : str,
    confidence     : float,
    weekly_pattern : str | None  = None,
    daily_pattern  : str | None  = None,
    h1_pattern     : str | None  = None,
    weekly_elliott : dict | None = None,  # جديد
    daily_elliott  : dict | None = None,  # جديد
    h1_elliott     : dict | None = None,  # جديد
    conflict_result: dict | None = None,
    bos            : dict | None = None,
) -> str:
    """
    يبني إشارة تداول موحدة مع مراعاة Phase و Subwave
    
    الجديد:
    - فحص h1_elliott.phase و h1_elliott.subwave
    - منع SELL_NOW إذا كانت wave_C جارية وليست مكتملة
    - WAIT_SELL للتصحيحات الجارية
    
    Args:
        h1_elliott: dict من detect_elliott_pattern() يحتوي على:
            - phase: \"impulse_ongoing\" | \"impulse_completed\" | \"correction_ongoing\" | \"correction_completed\"\n            - current_wave: \"wave_A\" | \"wave_B\" | \"wave_C\" | ...\n            - subwave: \"wave_1\" | \"wave_2\" | ... | \"wave_5\" | None
    
    Returns:
        STRONG_SELL | SELL_NOW | SELL | WAIT_SELL |
        STRONG_BUY  | BUY_NOW  | BUY  | WAIT_BUY  |
        NO_TRADE
    """

    raw_signal = _build_raw_signal(
        weekly_bias, daily_bias, h1_bias, confidence,
        weekly_pattern, daily_pattern, h1_pattern,
        weekly_elliott, daily_elliott, h1_elliott,
        conflict_result,
    )

    # استيراد متأخر (lazy import) لتجنب الاستيراد الدائري
    from recommendation_engine.conflict_resolver import classify_signal_mode

    # ── تصنيف إشارات الدخول الفورية بناءً على BOS ──
    immediate_signals = (
        "SELL_NOW", "BUY_NOW", "STRONG_SELL", "STRONG_BUY"
    )

    if raw_signal in immediate_signals and bos is not None:
        base = "SELL_NOW" if "SELL" in raw_signal else "BUY_NOW"
        classification = classify_signal_mode(base, bos)

        if classification["mode"] == "AGGRESSIVE":
            return f"{raw_signal}_EARLY"

    return raw_signal


def _build_raw_signal(
    weekly_bias    : str,
    daily_bias     : str,
    h1_bias        : str,
    confidence     : float,
    weekly_pattern : str | None  = None,
    daily_pattern  : str | None  = None,
    h1_pattern     : str | None  = None,
    weekly_elliott : dict | None = None,
    daily_elliott  : dict | None = None,
    h1_elliott     : dict | None = None,
    conflict_result: dict | None = None,
) -> str:
    """
    المنطق الجديد لتحديد الإشارة مع Phase-Based Logic
    """

    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # فحص H1 Elliott أولاً (المستوى الأقرب)
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════
    if h1_elliott is not None:
        h1_signal = _evaluate_h1_elliott(h1_elliott)
        
        if h1_signal:
            # إذا كانت إشارة واضحة من H1
            return h1_signal
    
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # المسار القديم: conflict_result
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════
    if conflict_result is not None:
        from recommendation_engine.conflict_resolver import get_entry_signal
        return get_entry_signal(
            conflict_result,
            h1_elliott,
            confidence=confidence,
        )

    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # fallback – bias فقط (بدون Elliott)
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════

    # ── STRONG SELL ──────────────────────────────────────────────────────────────────────────────────────────
    if (
        weekly_bias == "bearish"
        and daily_bias == "bearish"
        and h1_bias   == "bearish"
        and confidence >= 75
    ):
        return "STRONG_SELL"

    # ── SELL ─────────────────────────────────────────────────────────────────────────────────────────────────
    if (
        weekly_bias == "bearish"
        and daily_bias == "bearish"
        and h1_bias   == "bearish"
    ):
        return "SELL"

    # ── WAIT_SELL (ABC Correction) ───────────────────────────────────────────────────────────────────────────
    if (
        weekly_pattern == "bearish_impulse"
        and (daily_pattern == "ABC" or h1_pattern == "ABC")
    ):
        return "WAIT_SELL"

    # ── WAIT_SELL (General) ──────────────────────────────────────────────────────────────────────────────────
    if (
        weekly_bias == "bearish"
        and (daily_bias != "bearish" or h1_bias != "bearish")
    ):
        return "WAIT_SELL"

    # ── STRONG BUY ───────────────────────────────────────────────────────────────────────────────────────────
    if (
        weekly_bias == "bullish"
        and daily_bias == "bullish"
        and h1_bias   == "bullish"
        and confidence >= 75
    ):
        return "STRONG_BUY"

    # ── BUY ──────────────────────────────────────────────────────────────────────────────────────────────────
    if (
        weekly_bias == "bullish"
        and daily_bias == "bullish"
        and h1_bias   == "bullish"
    ):
        return "BUY"

    # ── WAIT_BUY (ABC Correction) ────────────────────────────────────────────────────────────────────────────
    if (
        weekly_pattern == "bullish_impulse"
        and (daily_pattern == "ABC" or h1_pattern == "ABC")
    ):
        return "WAIT_BUY"

    # ── WAIT_BUY (General) ───────────────────────────────────────────────────────────────────────────────────
    if (
        weekly_bias == "bullish"
        and (daily_bias != "bullish" or h1_bias != "bullish")
    ):
        return "WAIT_BUY"

    return "NO_TRADE"


def _evaluate_h1_elliott(h1_elliott: dict) -> str | None:
    """
    قيّم إشارة H1 بناءً على Elliott data مع Phase-Based Logic
    
    الشروط:
    ✅ SELL_NOW فقط إذا:
       - phase = \"correction_completed\"
       - current_wave = \"wave_C\"
       - subwave = \"wave_5\"
    
    ⏳ WAIT_SELL إذا:
       - phase = \"correction_ongoing\"
       - current_wave = \"wave_A\" أو \"wave_B\" أو \"wave_C\" (wave_1-4)
    
    Args:
        h1_elliott: dict من detect_elliott_pattern()
    
    Returns:
        str | None: signal أو None
    """
    
    phase = h1_elliott.get("phase")
    pattern = h1_elliott.get("pattern")
    current_wave = h1_elliott.get("current_wave")
    subwave = h1_elliott.get("subwave")
    confidence = h1_elliott.get("confidence", 0)
    
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # BEARISH SIGNALS
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    # ✅ SELL_NOW: تصحيح هابط مكتمل
    # يعني: Wave_C انتهت، ترند هابط جديد قادم
    if (
        phase == "correction_completed"
        and current_wave == "wave_C"
        and subwave == "wave_5"
        and confidence >= 70
    ):
        return "SELL_NOW"
    
    # ⏳ WAIT_SELL: تصحيح صاعد جار (ما زال يرتفع)
    # يعني: Wave_A أو Wave_B أو Wave_C (لكن لم تنته بعد)
    if (
        phase == "correction_ongoing"
        and pattern in ("zigzag", "flat", "triangle")
        and current_wave in ("wave_A", "wave_B")
    ):
        return "WAIT_SELL"
    
    # ⏳ WAIT_SELL: Wave_C جارية لكن لم تكتمل بعد
    if (
        phase == "correction_ongoing"
        and current_wave == "wave_C"
        and subwave in ("wave_1", "wave_2", "wave_3", "wave_4")
    ):
        return "WAIT_SELL"
    
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # BULLISH SIGNALS
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    # ✅ BUY_NOW: تصحيح صاعد مكتمل
    # يعني: Wave_C انتهت، ترند صاعد جديد قادم
    if (
        phase == "correction_completed"
        and current_wave == "wave_C"
        and subwave == "wave_5"
        and confidence >= 70
    ):
        return "BUY_NOW"
    
    # ⏳ WAIT_BUY: تصحيح هابط جار (ما زال ينخفض)
    # يعني: Wave_A أو Wave_B أو Wave_C (لكن لم تنته بعد)
    if (
        phase == "correction_ongoing"
        and pattern in ("zigzag", "flat", "triangle")
        and current_wave in ("wave_A", "wave_B")
    ):
        return "WAIT_BUY"
    
    # ⏳ WAIT_BUY: Wave_C جارية لكن لم تكتمل بعد
    if (
        phase == "correction_ongoing"
        and current_wave == "wave_C"
        and subwave in ("wave_1", "wave_2", "wave_3", "wave_4")
    ):
        return "WAIT_BUY"
    
    return None