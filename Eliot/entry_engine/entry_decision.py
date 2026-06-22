# entry_engine/entry_decision.py


def _get_direction(bos_result: dict) -> str:
    """
    يستخرج الاتجاه من نتيجة detect_bos() الجديدة.

    الهيكل الجديد: {"direction": "bullish"/"bearish"/"none", "type": "BOS"/"CHoCH"/"none", ...}
    الهيكل القديم: {"bos": "bullish"/"bearish"/"none"} — متوافق أيضاً
    """
    if not isinstance(bos_result, dict):
        return "none"

    # الهيكل الجديد
    if "direction" in bos_result:
        return bos_result.get("direction", "none")

    # الهيكل القديم (fallback)
    if "bos" in bos_result:
        return bos_result.get("bos", "none")

    return "none"


def _get_type(bos_result: dict) -> str:
    """يستخرج نوع الكسر (BOS/CHoCH/none) من النتيجة."""
    if not isinstance(bos_result, dict):
        return "none"

    if "type" in bos_result:
        return bos_result.get("type", "none")

    # الهيكل القديم: إذا كان هناك choch منفصل
    if "choch" in bos_result:
        choch = bos_result.get("choch", "none")
        if choch != "none":
            return "CHoCH"

    return "BOS" if _get_direction(bos_result) != "none" else "none"


def _get_confidence(bos_result: dict) -> int:
    """يستخرج مستوى الثقة من نتيجة detect_bos()."""
    if not isinstance(bos_result, dict):
        return 0
    return int(bos_result.get("confidence", 0))


def build_entry_decision(
    timeframe_structure: dict,
) -> dict:
    """
    يبني قرار الدخول النهائي بناءً على BOS/CHoCH من W1 و D1 و H1.

    القاعدة:
        SELL  : W1 bearish + (D1 bearish أو H1 bearish) + CHoCH/BOS هابط على H1
        BUY   : W1 bullish + (D1 bullish أو H1 bullish) + CHoCH/BOS صاعد على H1
        WAIT  : غير ذلك

    Args:
        timeframe_structure: dict يحتوي على W1/D1/H1
                             كل منها يحوي "bos" (نتيجة detect_bos)
                             وقد يحوي "choch" اختياري (الهيكل القديم)

    Returns:
        dict: signal, reasons, confidence, bos_directions
    """

    w1 = timeframe_structure.get("W1", {})
    d1 = timeframe_structure.get("D1", {})
    h1 = timeframe_structure.get("H1", {})

    # ── استخراج BOS ──────────────────────────────
    w1_bos = w1.get("bos", {})
    d1_bos = d1.get("bos", {})
    h1_bos = h1.get("bos", {})

    # ── استخراج CHoCH (الهيكل القديم أو من type) ─
    w1_choch = w1.get("choch", {})
    d1_choch = d1.get("choch", {})
    h1_choch = h1.get("choch", {})

    # ── الاتجاهات ─────────────────────────────────
    w1_dir   = _get_direction(w1_bos)
    d1_dir   = _get_direction(d1_bos)
    h1_dir   = _get_direction(h1_bos)
    h1_type  = _get_type(h1_bos)

    # للهيكل القديم: تحقق من CHoCH منفصل
    h1_choch_dir = _get_direction(h1_choch) if h1_choch else "none"
    if h1_choch_dir == "none" and h1_type == "CHoCH":
        h1_choch_dir = h1_dir

    # ── مجموع الثقة ──────────────────────────────
    w1_conf = _get_confidence(w1_bos)
    d1_conf = _get_confidence(d1_bos)
    h1_conf = _get_confidence(h1_bos)
    avg_conf = int((w1_conf + d1_conf + h1_conf) / 3) if any([w1_conf, d1_conf, h1_conf]) else 0

    signal  = "WAIT"
    reasons = []

    # ══════════════════════════════════════════════
    # SELL: W1 هابط + تأكيد D1 أو H1
    # ══════════════════════════════════════════════
    if w1_dir == "bearish":

        # تأكيد قوي: W1 + D1 + H1 كلهم هابطون
        if d1_dir == "bearish" and h1_dir == "bearish":
            signal = "SELL"
            reasons.extend([
                "W1 bearish structure confirmed",
                "D1 bearish alignment",
                "H1 bearish confirmation",
            ])
            if h1_choch_dir == "bearish":
                reasons.append("H1 CHoCH bearish — تغيير اتجاه مؤكد")

        # تأكيد جزئي: W1 + H1 فقط
        elif h1_dir == "bearish" or h1_choch_dir == "bearish":
            signal = "SELL"
            reasons.extend([
                "W1 bearish structure",
                "H1 bearish confirmation",
            ])

        else:
            signal = "WAIT_SELL"
            reasons.append("W1 bearish — انتظار تأكيد H1")

    # ══════════════════════════════════════════════
    # BUY: W1 صاعد + تأكيد D1 أو H1
    # ══════════════════════════════════════════════
    elif w1_dir == "bullish":

        # تأكيد قوي: W1 + D1 + H1 كلهم صاعدون
        if d1_dir == "bullish" and h1_dir == "bullish":
            signal = "BUY"
            reasons.extend([
                "W1 bullish structure confirmed",
                "D1 bullish alignment",
                "H1 bullish confirmation",
            ])
            if h1_choch_dir == "bullish":
                reasons.append("H1 CHoCH bullish — تغيير اتجاه مؤكد")

        # تأكيد جزئي: W1 + H1 فقط
        elif h1_dir == "bullish" or h1_choch_dir == "bullish":
            signal = "BUY"
            reasons.extend([
                "W1 bullish structure",
                "H1 bullish confirmation",
            ])

        else:
            signal = "WAIT_BUY"
            reasons.append("W1 bullish — انتظار تأكيد H1")

    # ══════════════════════════════════════════════
    # لا يوجد اتجاه واضح
    # ══════════════════════════════════════════════
    else:
        signal = "WAIT"
        reasons.append("لا يوجد BOS واضح — الاتجاه غير محدد")

    return {
        "signal"    : signal,
        "reasons"   : reasons,
        "confidence": avg_conf,
        "bos_directions": {
            "W1": w1_dir,
            "D1": d1_dir,
            "H1": h1_dir,
        },
    }