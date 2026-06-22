# recommendation_engine/recommendation_builder.py

from recommendation_engine.conflict_resolver import (
    resolve_timeframe_conflict,
    get_entry_signal,
    classify_signal_mode,
)


def build_recommendation(
    trend,
    elliott,
    bos,
    choch,
    volume,
    alignment,
    wave_alignment,
    confidence,
    w1_elliott: dict = None,
    d1_elliott: dict = None,
    h1_elliott: dict = None,
    h4_elliott: dict = None,
) -> dict:
    """
    يبني التوصية النهائية مع حل التعارض بين timeframes.

    Args:
        trend         : نتيجة analyze_weekly_trend()
        elliott       : نتيجة detect_elliott_pattern() على W1
        bos           : نتيجة detect_bos()
        choch         : نتيجة detect_choch()
        volume        : نتيجة analyze_volume()
        alignment     : نتيجة calculate_alignment()
        wave_alignment: نتيجة calculate_wave_alignment()
        confidence    : نتيجة calculate_wave_confidence()
        w1_elliott    : elliott dict خاص بـ W1
        d1_elliott    : elliott dict خاص بـ D1
        h1_elliott    : elliott dict خاص بـ H1
        h4_elliott    : elliott dict خاص بـ H4 (جديد — فلتر تأكيد هيكلي
                        بين D1 وH1). اختياري؛ إن لم يُمرَّر، يعمل الكود
                        تماماً كما كان قبل إضافة H4.

    Returns:
        dict يحتوي على signal, direction, score, reasons,
             context, primary_bias, d1_role, h4_role, action
    """

    reasons  = []
    score    = 50
    signal   = "WAIT"
    direction = "neutral"

    # ── Confidence (يُحسب أولاً لاستخدامه في get_entry_signal) ──
    conf_val = confidence if isinstance(confidence, (int, float)) else 0

    # ── 1. حل التعارض بين timeframes (مع فلتر H4 إن وُجد) ──
    conflict_result = None
    entry_signal    = None

    if w1_elliott and d1_elliott and h1_elliott:
        conflict_result = resolve_timeframe_conflict(
            w1_elliott,
            d1_elliott,
            h1_elliott,
            h4_elliott=h4_elliott,
        )
        entry_signal = get_entry_signal(
            conflict_result,
            h1_elliott,
            confidence=conf_val,
        )
        reasons.append(conflict_result["context"])
        reasons.append(f"D1 دور: {conflict_result['d1_role']}")

        # ── جديد: سبب صريح لدور H4 إن تم فحصه ──
        h4_role = conflict_result.get("h4_role", "not_checked")
        if h4_role != "not_checked":
            h4_confirmed = conflict_result.get("h4_confirmed")
            if h4_confirmed:
                reasons.append(f"H4 دور: مؤكِّد ({h4_role})")
            else:
                reasons.append(f"H4 دور: معارض — تم تخفيض الإشارة لانتظار")

        reasons.append(
            f"H1: {h1_elliott.get('pattern')} "
            f"— {h1_elliott.get('current_wave')}"
        )

    # ── 2. الاتجاه الرئيسي من trend ──────────
    trend_dir = trend.get("direction", "") if trend else ""

    if "bearish" in trend_dir.lower():
        reasons.append("bearish primary trend")
        direction = "sell"
        score    += 10
    elif "bullish" in trend_dir.lower():
        reasons.append("bullish primary trend")
        direction = "buy"
        score    += 10

    # ── 3. Elliott Pattern ────────────────────
    elliott_pattern = elliott.get("pattern", "") if elliott else ""

    if "bearish_impulse" in elliott_pattern:
        reasons.append("bearish impulse structure")
        score += 10
    elif "bullish_impulse" in elliott_pattern:
        reasons.append("bullish impulse structure")
        score += 10

    # ── 4. BOS / CHoCH ────────────────────────
    from structure_engine.bos_detector import get_bos_summary

    if bos:
        bos_type = bos.get("type", "none") if isinstance(bos, dict) else "none"
        bos_dir  = bos.get("direction", "none") if isinstance(bos, dict) else "none"
        h1_conf  = bos.get("h1_confirmed", False) if isinstance(bos, dict) else False

        if bos_type != "none" and bos_dir != "none":
            reasons.append(get_bos_summary(bos))
            if bos_type == "BOS":
                score += 15
            elif bos_type == "CHoCH":
                score += 10
            if h1_conf:
                score += 5
        else:
            reasons.append("لا يوجد BOS — الإشارة مبنية على Elliott فقط")
    # ── 5. CHoCH ─────────────────────────────
    if choch:
        choch_dir = choch.get("direction", "") if isinstance(choch, dict) else str(choch)
        if "bearish" in str(choch_dir).lower():
            reasons.append("bearish CHoCH — انعكاس محتمل")
            score += 5
        elif "bullish" in str(choch_dir).lower():
            reasons.append("bullish CHoCH — انعكاس محتمل")
            score += 5

    # ── 6. Volume ─────────────────────────────
    if volume:
        vol_state = volume.get("state", "") if isinstance(volume, dict) else str(volume)
        if "high" in str(vol_state).lower():
            reasons.append("high volume — تأكيد قوي")
            score += 7
        elif "low" in str(vol_state).lower():
            reasons.append("low volume — تأكيد ضعيف")
            score -= 5
        else:
            reasons.append("normal volume")

    # ── 7. Alignment ──────────────────────────
    align_score = 0
    if isinstance(alignment, dict):
        align_score = alignment.get("score", 0)
    elif isinstance(alignment, (int, float)):
        align_score = alignment

    reasons.append(f"alignment score {align_score}")
    if align_score >= 70:
        score += 8
    elif align_score < 50:
        score -= 5

    # ── 8. Wave Alignment (الآن قد تشمل H4) ───
    wa_score = 0
    if isinstance(wave_alignment, dict):
        wa_score = wave_alignment.get("score", 0)
        aligned  = wave_alignment.get("aligned", False)
        if not aligned:
            reasons.append(f"wave misalignment {wa_score}")
            score -= 5
        else:
            reasons.append(f"wave aligned {wa_score}")
            score += 5
    elif isinstance(wave_alignment, (int, float)):
        wa_score = wave_alignment
        reasons.append(f"wave alignment {wa_score}")

    # ── 9. Confidence (تأثير على score) ──────
    if conf_val >= 80:
        score += 10
    elif conf_val >= 60:
        score += 5

    # ── 10. تحديد الإشارة النهائية ────────────
    signal_mode = "WAIT"
    signal_note = ""

    if entry_signal in ("SELL_NOW", "BUY_NOW", "STRONG_SELL", "STRONG_BUY"):
        direction = "sell" if entry_signal in ("SELL_NOW", "STRONG_SELL") else "buy"

        # توضيح سبب الإشارة بدلاً من 'no BOS'
        h1_pat  = h1_elliott.get("pattern",       "") if h1_elliott else ""
        h1_wave = h1_elliott.get("current_wave",  "") if h1_elliott else ""
        h1_next = h1_elliott.get("next_wave",     "") if h1_elliott else ""

        if h1_pat == "ABC" and h1_wave == "wave_C":
            reasons.append(
                f"{entry_signal} — H1 ABC اكتملت عند wave_C "
                f"→ {h1_next}"
            )
        elif "impulse" in h1_pat:
            reasons.append(
                f"{entry_signal} — H1 {h1_pat} "
                f"wave {h1_wave} يؤكد الاتجاه"
            )
        else:
            reasons.append(f"{entry_signal} — مبني على Elliott")

        # ── تصنيف الإشارة: CONFIRMED (BOS) أو AGGRESSIVE (Elliott فقط) ──
        signal_classification = classify_signal_mode(entry_signal, bos)
        signal      = signal_classification["final_signal"]
        signal_mode = signal_classification["mode"]
        signal_note = signal_classification["note"]
        reasons.append(f"[{signal_mode}] {signal_note}")

        if signal_mode == "AGGRESSIVE":
            score -= 10  # خصم لعدم وجود تأكيد هيكلي

    elif entry_signal in ("WAIT_SELL", "WAIT_BUY"):
        signal    = entry_signal
        direction = "sell" if entry_signal == "WAIT_SELL" else "buy"
        signal_mode = "WAIT"

        h1_pat  = h1_elliott.get("pattern",      "") if h1_elliott else ""
        h1_wave = h1_elliott.get("current_wave", "") if h1_elliott else ""

        # ── إذا كان السبب الفعلي هو معارضة H4، وضّح ذلك بدل الرسالة العامة ──
        h4_blocked = (
            conflict_result is not None
            and conflict_result.get("h4_confirmed") is False
        )
        if h4_blocked:
            reasons.append(
                f"{entry_signal} — H4 يعارض هيكلياً، تم تخفيض الإشارة للانتظار"
            )
        else:
            reasons.append(
                f"{entry_signal} — H1 {h1_pat} {h1_wave} "
                f"لم تكتمل بعد"
            )

    elif entry_signal == "NO_TRADE":
        signal    = "NO_TRADE"
        direction = "neutral"
        signal_mode = "WAIT"
        reasons.append("NO_TRADE — تعارض حقيقي بين W1 و D1")

    else:
        # fallback: اعتمد على الاتجاه العام
        signal_mode = "WAIT"
        if score >= 70 and direction == "sell":
            signal = "SELL"
        elif score >= 70 and direction == "buy":
            signal = "BUY"
        else:
            signal = "WAIT"

    return {
        "signal"      : signal,
        "signal_mode" : signal_mode,
        "signal_note" : signal_note,
        "direction"   : direction,
        "score"       : max(0, min(score, 100)),
        "confidence"  : conf_val,
        "reasons"     : reasons,
        "context"     : conflict_result["context"]       if conflict_result else "no conflict analysis",
        "primary_bias": conflict_result["primary_bias"]  if conflict_result else direction,
        "d1_role"     : conflict_result["d1_role"]       if conflict_result else "unknown",
        "h4_role"     : conflict_result.get("h4_role", "not_checked") if conflict_result else "not_checked",
        "action"      : conflict_result["action"]        if conflict_result else signal,
    }