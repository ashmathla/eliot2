# structure_engine/bos_detector.py


def _get_market_direction(swings: list) -> str:
    """
    يحدد الاتجاه السابق من تسلسل الـ swings.
        - Higher Highs + Higher Lows → bullish
        - Lower Highs  + Lower Lows  → bearish
        - غير ذلك                    → sideways
    """
    highs = [x for x in swings if x["type"] == "HIGH"]
    lows  = [x for x in swings if x["type"] == "LOW"]

    if len(highs) < 2 or len(lows) < 2:
        return "unknown"

    hh = highs[-1]["price"] > highs[-2]["price"]
    hl = lows[-1]["price"]  > lows[-2]["price"]
    lh = highs[-1]["price"] < highs[-2]["price"]
    ll = lows[-1]["price"]  < lows[-2]["price"]

    if hh and hl:
        return "bullish"
    if lh and ll:
        return "bearish"
    return "sideways"


def _find_ref_level(highs: list, lows: list, direction: str) -> float | None:
    """
    يجد المستوى المرجعي للكسر:
    - bullish BOS: أعلى قمة قبل الأخيرة (prev_high) — إذا تجاوزتها last_high فهو BOS
    - bearish BOS: أعلى قاع قبل الأخير (prev_low)  — إذا كُسر فهو BOS

    المنطق: نريد المستوى الذي إذا تجاوزه السعر يؤكد استمرار الترند،
    وهو دائماً العنصر قبل الأخير (index -2) وليس الأخير.
    """
    if direction == "bullish":
        # ref = أعلى قمة مؤكدة قبل الأخيرة
        if len(highs) >= 2:
            return highs[-2]["price"]
    elif direction == "bearish":
        # ref = أدنى قاع مؤكد قبل الأخير
        if len(lows) >= 2:
            return lows[-2]["price"]
    return None


def detect_bos(
    swings: list,
    current_price: float | None = None,
    h1_swings: list | None = None,
) -> dict:
    """
    يكتشف Break of Structure (BOS) و Change of Character (CHoCH).

    المنطق المُصحح:
        BOS bullish : last_high > prev_high  (كسر قمة سابقة في ترند صاعد)
        BOS bearish : last_low  < prev_low   (كسر قاع سابق في ترند هابط)
        CHoCH bearish: last_low  < prev_low  في ترند صاعد (انعكاس)
        CHoCH bullish: last_high > prev_high في ترند هابط (انعكاس)

    Returns:
        direction    : bullish / bearish / none
        type         : BOS / CHoCH / none
        level        : السعر الذي تم كسره
        confidence   : 0-100
        prev_trend   : الاتجاه السابق
        h1_confirmed : هل تم تأكيد الكسر على H1؟
    """

    result = {
        "direction"   : "none",
        "type"        : "none",
        "level"       : None,
        "confidence"  : 0,
        "prev_trend"  : "unknown",
        "h1_confirmed": False,
    }

    if len(swings) < 4:
        return result

    highs = sorted([x for x in swings if x["type"] == "HIGH"], key=lambda x: x["index"])
    lows  = sorted([x for x in swings if x["type"] == "LOW"],  key=lambda x: x["index"])

    if len(highs) < 2 or len(lows) < 2:
        return result

    prev_trend = _get_market_direction(swings)
    result["prev_trend"] = prev_trend

    last_high = highs[-1]["price"]
    prev_high = highs[-2]["price"]
    last_low  = lows[-1]["price"]
    prev_low  = lows[-2]["price"]

    # ── BOS: كسر في نفس اتجاه الترند ─────────────
    if prev_trend == "bullish":
        # BOS صاعد: آخر قمة تجاوزت القمة السابقة
        if last_high > prev_high:
            result.update({
                "direction" : "bullish",
                "type"      : "BOS",
                "level"     : round(prev_high, 5),
                "confidence": 75,
            })

    elif prev_trend == "bearish":
        # BOS هابط: آخر قاع كسر القاع السابق
        if last_low < prev_low:
            result.update({
                "direction" : "bearish",
                "type"      : "BOS",
                "level"     : round(prev_low, 5),
                "confidence": 75,
            })

    # ── CHoCH: كسر عكسي ────────────────────────────
    if result["type"] == "none":
        if prev_trend == "bullish":
            # CHoCH هابط: كسر قاع سابق في ترند صاعد
            if last_low < prev_low:
                result.update({
                    "direction" : "bearish",
                    "type"      : "CHoCH",
                    "level"     : round(prev_low, 5),
                    "confidence": 70,
                })
        elif prev_trend == "bearish":
            # CHoCH صاعد: كسر قمة سابقة في ترند هابط
            if last_high > prev_high:
                result.update({
                    "direction" : "bullish",
                    "type"      : "CHoCH",
                    "level"     : round(prev_high, 5),
                    "confidence": 70,
                })

    # ── Fallback: current_price يتجاوز المستويات ───
    if result["type"] == "none" and current_price is not None:
        if current_price > prev_high:
            result.update({
                "direction" : "bullish",
                "type"      : "BOS",
                "level"     : round(prev_high, 5),
                "confidence": 60,
            })
        elif current_price < prev_low:
            result.update({
                "direction" : "bearish",
                "type"      : "BOS",
                "level"     : round(prev_low, 5),
                "confidence": 60,
            })

    # ── sideways: استخدم current_price فقط ─────────
    if result["type"] == "none" and prev_trend == "sideways" and current_price is not None:
        if current_price > prev_high:
            result.update({
                "direction" : "bullish",
                "type"      : "BOS",
                "level"     : round(prev_high, 5),
                "confidence": 55,
            })
        elif current_price < prev_low:
            result.update({
                "direction" : "bearish",
                "type"      : "BOS",
                "level"     : round(prev_low, 5),
                "confidence": 55,
            })

    # ── تأكيد H1 ───────────────────────────────────
    if h1_swings and result["type"] != "none":
        h1_result = detect_bos(h1_swings, current_price)
        if h1_result["direction"] == result["direction"]:
            result["h1_confirmed"] = True
            result["confidence"]   = min(result["confidence"] + 15, 100)

    return result


def get_bos_summary(bos_result: dict) -> str:
    """يُرجع ملخصاً نصياً للـ BOS/CHoCH."""
    if bos_result.get("type", "none") == "none":
        return "لا يوجد BOS — الإشارة مبنية على Elliott فقط"

    direction  = "صاعد" if bos_result["direction"] == "bullish" else "هابط"
    level      = bos_result["level"]
    h1_conf    = " (مؤكد على H1)" if bos_result.get("h1_confirmed") else ""
    confidence = bos_result.get("confidence", 0)

    return (
        f"{bos_result['type']} {direction} عند {level}"
        f"{h1_conf} — ثقة {confidence}%"
    )