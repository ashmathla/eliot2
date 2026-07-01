"""
confidence_engine.py — محرك تقييم الثقة بالإشارات
════════════════════════════════════════════════════
بدل الرفض الثنائي المطلق (قبول/رفض) لإشارة قرب
القاع/القمة، هذا المحرك يحسب درجة ثقة (0-100) ويتخذ
قراراً متدرجاً:

  - liquidity_score منخفض  → الإشارة تمر عادي
  - liquidity_score متوسط  → تمر مع تخفيض RR المطلوب
    (تنبيه فقط، لا رفض)
  - liquidity_score عالي
    + Divergence مضاد
    + حجم تداول صاعد        → رفض قوي (هذا فقط الحالة
      التي ينصح فيها برفض حقيقي، حسب الملاحظة الأخيرة)

هذا يطبّق مباشرة: نظام "خصم ثقة" بدل "رفض مطلق"،
بالإضافة لفلتر الرفض القوي الموصوف.
"""

from logger import log


# ── أوزان النظام ──────────────────────────────
# يمكن ضبطها لاحقاً دون المساس بمنطق الحساب
HARD_REJECT_SCORE_THRESHOLD = 70   # فوقه + شروط إضافية = رفض قوي
SOFT_WARNING_SCORE_THRESHOLD = 40  # فوقه = تحذير فقط


def evaluate_signal_confidence(
    symbol:    str,
    direction: str,
    liquidity: dict,
) -> dict:
    """
    يحسب قرار الإشارة بناءً على بيانات السيولة الغنية
    القادمة من detect_liquidity_proximity().

    المنطق المطبّق من الملاحظات:
    1. لا رفض تلقائي لمجرد القرب من القاع/القمة.
    2. رفض قوي فقط عند اجتماع:
       - قرب فعلي (بـ ATR) من القاع/القمة
       - Divergence مضاد لاتجاه الصفقة
       - حجم تداول صاعد يدعم استمرار الحركة الحالية
       (أي: "ضعف واضح + زخم يؤكده" — وليس قرباً وحده)
    3. حالات أقل حدة تُمرَّر مع تحذير فقط، دون منع
       الإشارة، حفاظاً على فرص حقيقية في موجات دافعة
       (Wave 3 / Wave C) كما أشرت.

    يُعيد:
        {
            "decision":   "ALLOW" | "WARN" | "REJECT",
            "reason":     str,
            "score":      int,
        }
    """
    score = liquidity.get("liquidity_score", 0)

    near_low  = liquidity.get("near_major_low",  False)
    near_high = liquidity.get("near_major_high", False)

    bullish_div = liquidity.get("bullish_divergence", False)
    bearish_div = liquidity.get("bearish_divergence", False)
    vol_rising  = liquidity.get("volume_rising", False)

    # ── حالة BUY قرب القاع — هذا طبيعي وغير خطر ──
    # (الخطر فقط في SELL قرب القاع وBUY قرب القمة)
    if direction == "BUY" and near_low:
        return _allow(score, "شراء قرب قاع — اتجاه منطقي")
    if direction == "SELL" and near_high:
        return _allow(score, "بيع قرب قمة — اتجاه منطقي")

    # ── الحالة الخطرة: SELL قرب القاع ─────────
    if direction == "SELL" and near_low:
        return _evaluate_against_trend(
            symbol, direction, score,
            divergence = bullish_div,
            vol_rising = vol_rising,
            zone_label = "القاع الرئيسي",
        )

    # ── الحالة الخطرة: BUY قرب القمة ──────────
    if direction == "BUY" and near_high:
        return _evaluate_against_trend(
            symbol, direction, score,
            divergence = bearish_div,
            vol_rising = vol_rising,
            zone_label = "القمة الرئيسية",
        )

    # ── لا قرب من أي منطقة سيولة ───────────────
    return _allow(score, "لا توجد منطقة سيولة قريبة")


def _evaluate_against_trend(
    symbol:     str,
    direction:  str,
    score:      int,
    divergence: bool,
    vol_rising: bool,
    zone_label: str,
) -> dict:
    """
    يحسم قرار الصفقات المعاكسة لاتجاه السيولة القريبة.

    رفض قوي فقط عند: قرب حقيقي + Divergence + حجم صاعد
    (الحجم الصاعد هنا يعني الحركة الحالية لا تزال قوية،
    أي أن الـ Divergence لم يُترجم بعد لضعف فعلي بالسوق —
    فاتخاذ صفقة معاكسة الآن أخطر مما يبدو من الـ Divergence
    وحده).
    """
    if (
        score >= HARD_REJECT_SCORE_THRESHOLD
        and divergence
        and vol_rising
    ):
        return {
            "decision": "REJECT",
            "reason": (
                f"{symbol} {direction}: رفض قوي — قرب "
                f"{zone_label} (score={score}) مع "
                f"Divergence مضاد وحجم تداول صاعد يدعم "
                f"استمرار الحركة الحالية ضد الصفقة."
            ),
            "score": score,
        }

    if score >= SOFT_WARNING_SCORE_THRESHOLD:
        return {
            "decision": "WARN",
            "reason": (
                f"{symbol} {direction}: تحذير — قرب "
                f"{zone_label} (score={score}) لكن دون "
                f"تأكيد Divergence+Volume كافٍ للرفض "
                f"القوي. تُمرَّر مع الحذر."
            ),
            "score": score,
        }

    return _allow(
        score,
        f"قرب {zone_label} لكن score منخفض "
        f"({score}) — لا مؤشر كافٍ على انعكاس وشيك "
        f"(مثال: قد تكون السوق في موجة دافعة)."
    )


def _allow(score: int, reason: str) -> dict:
    return {
        "decision": "ALLOW",
        "reason":   reason,
        "score":    score,
    }