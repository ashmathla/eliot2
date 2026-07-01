"""
mt5_handler.py — كل شيء يخص MT5
════════════════════════════════════
- الاتصال وإعادة الاتصال
- المؤشرات التقنية المحسّنة:
    EMA (20/50/200) | RSI | ATR
    Bollinger Bands | Stochastic | VWAP
- فيبوناتشي Retracement + Extension
- Order Blocks + BOS
- Fair Value Gaps (FVG) المفلترة
- ملخص الرمز للـ Prompt
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime

from config import (
    EMA_PERIODS, RSI_PERIOD, ATR_PERIOD,
    BB_PERIOD, BB_STD,
    STOCH_K, STOCH_D, STOCH_SMOOTH,
    BARS_H4, BARS_H1, BARS_M15,
    BARS_FVG, BARS_OB, OB_LOOKBACK,
    DXY_SYMBOLS, SYMBOLS,
)
from logger import log

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    log.warning("⚠️ MetaTrader5 غير مثبّت.")


# ╔══════════════════════════════════════════╗
# ║  1. إدارة الاتصال                        ║
# ╚══════════════════════════════════════════╝

def ensure_mt5_connected() -> bool:
    if not MT5_AVAILABLE:
        return False
    if mt5.terminal_info() is not None:
        return True

    log.warning("⚠️ MT5 منقطع — إعادة الاتصال...")
    for attempt in range(3):
        if mt5.initialize():
            log.info("✅ MT5 متصل مجدداً.")
            return True
        log.warning(f"محاولة {attempt + 1}/3 فشلت.")
        time.sleep(3)

    log.error("❌ فشل الاتصال بـ MT5 نهائياً.")
    return False


def get_current_price(symbol: str) -> float:
    """يُعيد سعر Ask الحالي أو 0 عند الفشل."""
    if not ensure_mt5_connected():
        return 0.0
    tick = mt5.symbol_info_tick(symbol)
    return round(tick.ask, 3) if tick else 0.0


# ╔══════════════════════════════════════════╗
# ║  2. المؤشرات التقنية المحسّنة            ║
# ╚══════════════════════════════════════════╝

def calculate_indicators(rates) -> dict:
    """
    يحسب مجموعة كاملة من المؤشرات:
    EMA 20/50/200 | RSI | ATR
    Bollinger Bands | Stochastic | VWAP
    """
    if rates is None or len(rates) < 50:
        return {}

    df = pd.DataFrame(rates)
    c  = df["close"]
    h  = df["high"]
    l  = df["low"]

    # ── EMA ──────────────────────────────────
    ema20  = c.ewm(span=20,  adjust=False).mean()
    ema50  = c.ewm(span=50,  adjust=False).mean()
    ema200 = c.ewm(span=200, adjust=False).mean()

    # ── RSI ──────────────────────────────────
    delta    = c.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=RSI_PERIOD - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=RSI_PERIOD - 1, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, float("nan"))
    rsi      = 100 - (100 / (1 + rs))
    rsi_val  = float(rsi.iloc[-1])

    # ── ATR ──────────────────────────────────
    hl  = h - l
    hcp = (h - c.shift()).abs()
    lcp = (l - c.shift()).abs()
    atr = pd.concat(
        [hl, hcp, lcp], axis=1
    ).max(axis=1).ewm(com=ATR_PERIOD - 1, adjust=False).mean()
    atr_val = float(atr.iloc[-1])

    # ── Bollinger Bands ───────────────────────
    bb_mid   = c.rolling(BB_PERIOD).mean()
    bb_std   = c.rolling(BB_PERIOD).std()
    bb_upper = bb_mid + BB_STD * bb_std
    bb_lower = bb_mid - BB_STD * bb_std

    price    = float(c.iloc[-1])
    bb_pos   = _bb_position(
        price,
        float(bb_upper.iloc[-1]),
        float(bb_lower.iloc[-1]),
        float(bb_mid.iloc[-1]),
    )
    bb_width = round(
        (float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1]))
        / float(bb_mid.iloc[-1]) * 100, 2
    )

    # ── Stochastic ───────────────────────────
    low_min  = l.rolling(STOCH_K).min()
    high_max = h.rolling(STOCH_K).max()
    stoch_k  = 100 * (c - low_min) / (high_max - low_min + 1e-10)
    stoch_k  = stoch_k.rolling(STOCH_SMOOTH).mean()
    stoch_d  = stoch_k.rolling(STOCH_D).mean()
    sk_val   = round(float(stoch_k.iloc[-1]), 1)
    sd_val   = round(float(stoch_d.iloc[-1]), 1)
    stoch_signal = _stoch_signal(sk_val, sd_val)

    # ── VWAP (اليوم الحالي فقط) ───────────────
    vwap = _calculate_vwap(df)

    # ── حجم التداول ──────────────────────────
    vol = (
        df["tick_volume"]
        if "tick_volume" in df.columns
        else pd.Series([0] * len(df))
    )
    vol_avg   = vol.rolling(20).mean()
    vol_trend = (
        "مرتفع 🔥"
        if vol.iloc[-1] > vol_avg.iloc[-1] * 1.5
        else "فوق المتوسط"
        if vol.iloc[-1] > vol_avg.iloc[-1] * 1.2
        else "عادي"
    )

    # ── اتجاه EMA ────────────────────────────
    e20  = float(ema20.iloc[-1])
    e50  = float(ema50.iloc[-1])
    e200 = float(ema200.iloc[-1])
    ema_trend = _ema_trend(price, e20, e50, e200)

    # ── حالة RSI ─────────────────────────────
    rsi_state = (
        f"{rsi_val:.1f} ⚠️ تشبع شرائي"
        if rsi_val >= 70
        else f"{rsi_val:.1f} ⚠️ تشبع بيعي"
        if rsi_val <= 30
        else f"{rsi_val:.1f} ✅ محايد"
    )

    return {
        # EMA
        "ema20":     round(e20,  3),
        "ema50":     round(e50,  3),
        "ema200":    round(e200, 3),
        "ema_trend": ema_trend,
        # RSI
        "rsi":       round(rsi_val, 1),
        "rsi_state": rsi_state,
        # ATR
        "atr":       round(atr_val, 3),
        # Bollinger Bands
        "bb_upper":  round(float(bb_upper.iloc[-1]), 3),
        "bb_mid":    round(float(bb_mid.iloc[-1]),   3),
        "bb_lower":  round(float(bb_lower.iloc[-1]), 3),
        "bb_pos":    bb_pos,
        "bb_width":  bb_width,
        # Stochastic
        "stoch_k":      sk_val,
        "stoch_d":      sd_val,
        "stoch_signal": stoch_signal,
        # VWAP
        "vwap":      round(vwap, 3) if vwap else None,
        # Volume
        "vol_trend": vol_trend,
    }


def _ema_trend(price, e20, e50, e200) -> str:
    if price > e20 > e50 > e200:
        return "صاعد قوي ↑↑"
    elif price > e50 > e200:
        return "صاعد معتدل ↑"
    elif price > e200:
        return "فوق EMA200 ↑"
    elif price < e20 < e50 < e200:
        return "هابط قوي ↓↓"
    elif price < e50 < e200:
        return "هابط معتدل ↓"
    elif price < e200:
        return "تحت EMA200 ↓"
    return "محايد ↔"


def _bb_position(price, upper, lower, mid) -> str:
    if price >= upper:
        return "فوق الحد العلوي ⚠️ (تشبع)"
    elif price >= mid:
        return "بين المتوسط والحد العلوي"
    elif price <= lower:
        return "تحت الحد السفلي ⚠️ (تشبع)"
    else:
        return "بين المتوسط والحد السفلي"


def _stoch_signal(k: float, d: float) -> str:
    if k >= 80 and d >= 80:
        return f"K={k} D={d} ⚠️ تشبع شرائي"
    elif k <= 20 and d <= 20:
        return f"K={k} D={d} ⚠️ تشبع بيعي"
    elif k > d and k < 80:
        return f"K={k} D={d} 📈 إشارة شراء"
    elif k < d and k > 20:
        return f"K={k} D={d} 📉 إشارة بيع"
    return f"K={k} D={d} محايد"


def _calculate_vwap(df: pd.DataFrame) -> float | None:
    """
    يحسب VWAP اليومي من الشموع المتاحة.
    يُعيد None إذا لم تتوفر بيانات الحجم.
    """
    try:
        vol = (
            df["tick_volume"]
            if "tick_volume" in df.columns
            else None
        )
        if vol is None or vol.sum() == 0:
            return None

        typical = (df["high"] + df["low"] + df["close"]) / 3
        vwap    = (typical * vol).cumsum() / vol.cumsum()
        return float(vwap.iloc[-1])
    except Exception:
        return None


# ╔══════════════════════════════════════════╗
# ║  3. مستويات فيبوناتشي                    ║
# ╚══════════════════════════════════════════╝

def calculate_fibonacci(
    rates,
    lookback: int = 100,
) -> str:
    """
    يحسب مستويات فيبوناتشي من آخر قمة وقاع واضحين.

    يكتشف الاتجاه تلقائياً:
    - صاعد: من القاع إلى القمة (Retracement هابط)
    - هابط: من القمة إلى القاع (Retracement صاعد)

    المستويات:
    - Retracement: 0.236 | 0.382 | 0.5 | 0.618 | 0.786
    - Extension:   1.0   | 1.272 | 1.618
    """
    if rates is None or len(rates) < 20:
        return "   لا توجد بيانات كافية."

    df   = pd.DataFrame(rates).tail(lookback)
    high = float(df["high"].max())
    low  = float(df["low"].min())
    diff = high - low

    if diff <= 0:
        return "   نطاق السعر صفري — لا يمكن الحساب."

    # اكتشاف الاتجاه من موقع آخر إغلاق
    last_close = float(df["close"].iloc[-1])
    mid        = (high + low) / 2
    is_uptrend = last_close >= mid

    retrace_levels = [0.236, 0.382, 0.500, 0.618, 0.786]
    extend_levels  = [1.000, 1.272, 1.618]

    lines = []

    if is_uptrend:
        lines.append(
            f"   📐 فيبوناتشي صاعد "
            f"({low:.3f} → {high:.3f})"
        )
        lines.append(f"   القمة       : {high:.3f} ←")
        for lvl in retrace_levels:
            price = round(high - diff * lvl, 3)
            star  = "⭐" if lvl in (0.382, 0.500, 0.618) else "  "
            lines.append(
                f"   {star} Ret {lvl:.3f} : {price}"
            )
        lines.append(f"   القاع       : {low:.3f}")
        lines.append("   ── Extension (أهداف) ──")
        for lvl in extend_levels:
            price = round(low + diff * lvl, 3)
            lines.append(f"   Ext {lvl:.3f}   : {price}")

    else:
        lines.append(
            f"   📐 فيبوناتشي هابط "
            f"({high:.3f} → {low:.3f})"
        )
        lines.append(f"   القاع       : {low:.3f} ←")
        for lvl in retrace_levels:
            price = round(low + diff * lvl, 3)
            star  = "⭐" if lvl in (0.382, 0.500, 0.618) else "  "
            lines.append(
                f"   {star} Ret {lvl:.3f} : {price}"
            )
        lines.append(f"   القمة       : {high:.3f}")
        lines.append("   ── Extension (أهداف) ──")
        for lvl in extend_levels:
            price = round(high - diff * lvl, 3)
            lines.append(f"   Ext {lvl:.3f}   : {price}")

    return "\n".join(lines)


def _find_major_swings(
    df: pd.DataFrame,
    swing_window: int = 5,
) -> tuple[float, float, int, int]:
    """
    يكتشف Swing High/Low حقيقية (وليس مجرد أعلى/أدنى
    rolling) عبر مقارنة كل شمعة بجيرانها على الجانبين.

    يُعيد آخر Swing High وآخر Swing Low مهمّين
    (بأكبر/أصغر قيمة ضمن آخر الانعكاسات المكتشفة)
    مع index كل منهما لحساب المسافة الزمنية لاحقاً.

    هذا أدق من rolling(N).max() لأنه يلتقط نقاط
    الانعكاس الفعلية للسعر بدل حافة النافذة الزمنية.
    """
    highs = df["high"].values
    lows  = df["low"].values
    n     = len(df)

    swing_highs = []
    swing_lows  = []

    for i in range(swing_window, n - swing_window):
        window_h = highs[i - swing_window: i + swing_window + 1]
        window_l = lows[i - swing_window: i + swing_window + 1]

        if highs[i] == window_h.max():
            swing_highs.append((i, highs[i]))
        if lows[i] == window_l.min():
            swing_lows.append((i, lows[i]))

    if not swing_highs:
        swing_highs = [(int(highs.argmax()), float(highs.max()))]
    if not swing_lows:
        swing_lows = [(int(lows.argmin()), float(lows.min()))]

    # نأخذ أبرز Swing High وSwing Low (الأعلى/الأدنى قيمة)
    # من بين كل الـ Swings المكتشفة — هذا يمثل الحركة
    # الدافعة الحقيقية وليس فقط آخر تصحيح صغير
    major_high_idx, major_high = max(swing_highs, key=lambda x: x[1])
    major_low_idx,  major_low  = min(swing_lows,  key=lambda x: x[1])

    return major_high, major_low, major_high_idx, major_low_idx


def _detect_divergence(
    df:        pd.DataFrame,
    rsi:       pd.Series,
    near_low:  bool,
    near_high: bool,
) -> dict:
    """
    يكشف Divergence بسيط بين السعر وRSI عند آخر قاع/قمة:

    Bullish divergence: قاع سعري أدنى لكن RSI أعلى
                         (ضعف بيعي — يدعم رفض SELL)
    Bearish divergence: قمة سعرية أعلى لكن RSI أدنى
                         (ضعف شرائي — يدعم رفض BUY)

    يُعيد {"bullish_divergence": bool, "bearish_divergence": bool}
    """
    result = {"bullish_divergence": False, "bearish_divergence": False}

    if len(df) < 30 or rsi.isna().all():
        return result

    lookback = min(30, len(df))
    recent_df  = df.tail(lookback).reset_index(drop=True)
    recent_rsi = rsi.tail(lookback).reset_index(drop=True)

    if near_low:
        # قارن أدنى نقطتين منخفضتين في النافذة
        lows_idx = recent_df["low"].nsmallest(2).index.tolist()
        if len(lows_idx) == 2:
            i1, i2 = sorted(lows_idx)
            price_lower_low = (
                recent_df["low"].iloc[i2]
                < recent_df["low"].iloc[i1]
            )
            rsi_higher_low = (
                recent_rsi.iloc[i2] > recent_rsi.iloc[i1]
            )
            result["bullish_divergence"] = bool(
                price_lower_low and rsi_higher_low
            )

    if near_high:
        highs_idx = recent_df["high"].nlargest(2).index.tolist()
        if len(highs_idx) == 2:
            i1, i2 = sorted(highs_idx)
            price_higher_high = (
                recent_df["high"].iloc[i2]
                > recent_df["high"].iloc[i1]
            )
            rsi_lower_high = (
                recent_rsi.iloc[i2] < recent_rsi.iloc[i1]
            )
            result["bearish_divergence"] = bool(
                price_higher_high and rsi_lower_high
            )

    return result


def detect_liquidity_proximity(
    rates,
    lookback: int = 100,
) -> dict:
    """
    يكشف هل السعر الحالي قريب من منطقة سيولة رئيسية
    (Swing High/Low حقيقي) — مع معايير أدق من نسخة سابقة:

    1. القاع/القمة من Swings حقيقية وليس rolling window
       فقط — يتجنب الخلط بين تصحيح حالي وحركة دافعة.
    2. عتبة القرب بـ ATR وليس نسبة % ثابتة — تتكيف مع
       تقلب السوق الفعلي بدل قيمة دولارية صماء.
    3. لا يُصدر قراراً نهائياً (near_low/near_high فقط) —
       بل يُرفق Divergence وVolume كمدخلات إضافية
       يستخدمها confidence_engine لاحقاً بدل رفض مطلق.

    يُعيد قاموساً غنياً بالمعلومات بدل قرار ثنائي:
        {
            "near_major_low":  bool,
            "near_major_high": bool,
            "major_low":       float,
            "major_high":      float,
            "distance_pct":    float,  # للطرف الأقرب
            "distance_atr":    float,  # بوحدات ATR
            "bullish_divergence": bool,
            "bearish_divergence": bool,
            "volume_rising":      bool,
            "liquidity_score":    int,  # 0-100
        }
    """
    empty_result = {
        "near_major_low": False, "near_major_high": False,
        "major_low": 0.0, "major_high": 0.0,
        "distance_pct": 999.0, "distance_atr": 999.0,
        "bullish_divergence": False,
        "bearish_divergence": False,
        "volume_rising": False,
        "liquidity_score": 0,
    }

    if rates is None or len(rates) < 30:
        return empty_result

    df    = pd.DataFrame(rates).tail(lookback).reset_index(drop=True)
    price = float(df["close"].iloc[-1])

    # ── Swings حقيقية بدل rolling min/max ─────
    major_high, major_low, _, _ = _find_major_swings(df)
    diff = major_high - major_low

    if diff <= 0:
        return empty_result

    # ── ATR كمرجع نسبي بدل نسبة % ثابتة ───────
    ind      = calculate_indicators(rates)
    atr      = ind.get("atr", 0) or (diff * 0.02)  # احتياطي
    atr      = max(atr, 0.01)  # تجنب القسمة على صفر

    dist_from_low  = price - major_low
    dist_from_high = major_high - price

    # "قريب" = أقل من 1.5×ATR (بدل 10% ثابتة من المدى)
    ATR_MULTIPLIER = 1.5
    near_low  = dist_from_low  <= atr * ATR_MULTIPLIER
    near_high = dist_from_high <= atr * ATR_MULTIPLIER

    dist_atr = (
        round(dist_from_low / atr, 2) if near_low
        else round(dist_from_high / atr, 2) if near_high
        else round(min(dist_from_low, dist_from_high) / atr, 2)
    )
    dist_pct = (
        round(dist_from_low  / diff * 100, 1) if near_low
        else round(dist_from_high / diff * 100, 1) if near_high
        else round(min(dist_from_low, dist_from_high) / diff * 100, 1)
    )

    # ── Divergence كمدخل إضافي (ليس قراراً نهائياً) ──
    delta    = df["close"].diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, float("nan"))
    rsi      = 100 - (100 / (1 + rs))

    div = _detect_divergence(df, rsi, near_low, near_high)

    # ── حجم تداول صاعد (يدعم استمرار الاتجاه) ───
    vol = (
        df["tick_volume"]
        if "tick_volume" in df.columns
        else pd.Series([0] * len(df))
    )
    vol_avg      = vol.rolling(10).mean()
    volume_rising = bool(
        vol.iloc[-1] > vol_avg.iloc[-1] * 1.1
    ) if not vol_avg.isna().all() else False

    # ── liquidity_score: 0-100 بدل قرار ثنائي ──
    # يبدأ من قرب المنطقة، ويُعدَّل بالـ Divergence
    # والحجم — درجة عالية = حذر أكبر من الدخول المعاكس
    score = 0
    if near_low or near_high:
        # كلما اقترب أكثر (ATR أصغر) زادت الدرجة
        proximity_factor = max(0, 1 - (dist_atr / ATR_MULTIPLIER))
        score = int(proximity_factor * 60)  # حتى 60 من القرب

        if near_low and div["bullish_divergence"]:
            score += 25
        if near_high and div["bearish_divergence"]:
            score += 25
        if volume_rising:
            score += 15

    score = min(100, score)

    return {
        "near_major_low":  near_low,
        "near_major_high": near_high,
        "major_low":       round(major_low, 3),
        "major_high":      round(major_high, 3),
        "distance_pct":    dist_pct,
        "distance_atr":    dist_atr,
        "bullish_divergence": div["bullish_divergence"],
        "bearish_divergence": div["bearish_divergence"],
        "volume_rising":      volume_rising,
        "liquidity_score":    score,
    }


# ╔══════════════════════════════════════════╗
# ║  4. Order Blocks + Break of Structure    ║
# ╚══════════════════════════════════════════╝

def detect_order_blocks_with_bos(
    rates,
    lookback: int = BARS_OB,
) -> str:
    if rates is None or len(rates) < lookback:
        return "لا توجد بيانات كافية."

    df = pd.DataFrame(rates).tail(
        lookback
    ).reset_index(drop=True)

    df["swing_high"] = False
    df["swing_low"]  = False

    for i in range(2, len(df) - 2):
        window = slice(i - 2, i + 3)
        if df["high"].iloc[i] == df["high"].iloc[window].max():
            df.at[i, "swing_high"] = True
        if df["low"].iloc[i] == df["low"].iloc[window].min():
            df.at[i, "swing_low"] = True

    blocks          = []
    last_swing_high = None
    last_swing_low  = None

    for i in range(2, len(df)):
        if df["swing_high"].iloc[i - 1]:
            last_swing_high = df["high"].iloc[i - 1]
        if df["swing_low"].iloc[i - 1]:
            last_swing_low = df["low"].iloc[i - 1]

        # BOS صاعد → OB شرائي
        if (
            last_swing_high
            and df["close"].iloc[i] > last_swing_high
        ):
            for j in range(i - 1, max(0, i - OB_LOOKBACK), -1):
                if df["close"].iloc[j] < df["open"].iloc[j]:
                    blocks.append((
                        "BUY",
                        f"🟢 [+BOS] OB شرائي: "
                        f"{df['low'].iloc[j]:.3f}"
                        f" — {df['high'].iloc[j]:.3f}"
                    ))
                    last_swing_high = None
                    break

        # BOS هابط → OB بيعي
        if (
            last_swing_low
            and df["close"].iloc[i] < last_swing_low
        ):
            for j in range(i - 1, max(0, i - OB_LOOKBACK), -1):
                if df["close"].iloc[j] > df["open"].iloc[j]:
                    blocks.append((
                        "SELL",
                        f"🔴 [-BOS] OB بيعي: "
                        f"{df['low'].iloc[j]:.3f}"
                        f" — {df['high'].iloc[j]:.3f}"
                    ))
                    last_swing_low = None
                    break

    if not blocks:
        return "   لا توجد OB مصحوبة بـ BOS مؤخراً."

    # آخر 3 OB بدون تكرار
    seen   = set()
    unique = []
    for _, text in reversed(blocks):
        if text not in seen:
            seen.add(text)
            unique.append(f"   {text}")
        if len(unique) == 3:
            break

    return "\n".join(reversed(unique))


# ╔══════════════════════════════════════════╗
# ║  5. Fair Value Gaps (FVG) المفلترة       ║
# ╚══════════════════════════════════════════╝

def check_fvg_imbalance(
    symbol:    str,
    timeframe,
    bars:      int = BARS_FVG,
) -> str:
    if not ensure_mt5_connected():
        return "⚠️ MT5 غير متصل."

    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(
        symbol, timeframe, 1, bars
    )
    if rates is None or len(rates) < 4:
        return "⚠️ لا توجد بيانات كافية."

    fvgs = []

    for i in range(1, len(rates) - 2):
        prev = rates[i - 1]
        nxt  = rates[i + 1]

        # فجوة شرائية
        if prev["high"] < nxt["low"]:
            bottom    = prev["high"]
            top       = nxt["low"]
            mitigated = any(
                rates[j]["low"] <= bottom
                for j in range(i + 2, len(rates))
            )
            if not mitigated:
                size = round(top - bottom, 3)
                fvgs.append(
                    f"   📈 فجوة شرائية: "
                    f"{bottom:.3f} — {top:.3f} "
                    f"(حجم: {size})"
                )

        # فجوة بيعية
        elif prev["low"] > nxt["high"]:
            top       = prev["low"]
            bottom    = nxt["high"]
            mitigated = any(
                rates[j]["high"] >= top
                for j in range(i + 2, len(rates))
            )
            if not mitigated:
                size = round(top - bottom, 3)
                fvgs.append(
                    f"   📉 فجوة بيعية: "
                    f"{top:.3f} — {bottom:.3f} "
                    f"(حجم: {size})"
                )

    return (
        "\n".join(fvgs[-3:])
        if fvgs
        else "   ✅ لا توجد فجوات مفتوحة."
    )


# ╔══════════════════════════════════════════╗
# ║  6. مؤشر الدولار DXY                    ║
# ╚══════════════════════════════════════════╝

def analyze_dxy_trend() -> tuple[str, str]:
    """يُعيد (وصف نصي, اتجاه: 'UP'/'DOWN'/'UNKNOWN')"""
    if not ensure_mt5_connected():
        return "🔄 MT5 غير متصل.", "UNKNOWN"

    try:
        for symbol in DXY_SYMBOLS:
            mt5.symbol_select(symbol, True)
            rates = mt5.copy_rates_from_pos(
                symbol, mt5.TIMEFRAME_H1, 0, 10
            )
            if rates is None or len(rates) < 5:
                continue

            closes = [r["close"] for r in rates]
            # مقارنة آخر إغلاق مع متوسط آخر 5 شموع
            avg5   = sum(closes[-5:]) / 5
            last   = closes[-1]

            if last > closes[-3]:
                strength = (
                    "قوي" if last > avg5 * 1.001 else "خفيف"
                )
                return (
                    f"📈 صاعد {strength} "
                    f"(ضغط سلبي على المعادن)",
                    "UP",
                )
            else:
                strength = (
                    "قوي" if last < avg5 * 0.999 else "خفيف"
                )
                return (
                    f"📉 هابط {strength} "
                    f"(دعم لصعود المعادن)",
                    "DOWN",
                )

        return "🔄 بيانات DXY غير متاحة.", "UNKNOWN"

    except Exception as e:
        log.error(f"⚠️ خطأ في analyze_dxy_trend: {e}")
        return "🔄 خطأ في قراءة DXY.", "UNKNOWN"


# ╔══════════════════════════════════════════╗
# ║  7. ملخص الرمز الكامل للـ Prompt         ║
# ╚══════════════════════════════════════════╝

def get_symbol_summary(
    symbol:    str,
    timeframe,
    count:     int,
) -> dict:
    """
    يُعيد قاموساً شاملاً بكل بيانات الرمز:
    الاتجاه | الأعلى/الأدنى | المؤشرات | OB
    """
    if not ensure_mt5_connected():
        return {"error": "MT5 غير متصل"}

    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(
        symbol, timeframe, 0, count
    )

    if rates is None or len(rates) == 0:
        return {"error": "لا توجد بيانات"}

    df    = pd.DataFrame(rates)
    last  = df.iloc[-1]
    first = df.iloc[0]

    # اتجاه عام
    price_change = last["close"] - first["close"]
    trend = (
        "صاعد ↑" if price_change > 0 else "هابط ↓"
    )

    # مستويات الدعم والمقاومة البسيطة (أعلى/أدنى آخر 20 شمعة)
    recent = df.tail(20)
    support    = round(float(recent["low"].min()),  3)
    resistance = round(float(recent["high"].max()), 3)

    indicators   = calculate_indicators(rates)
    order_blocks = detect_order_blocks_with_bos(rates, count)
    fibonacci    = calculate_fibonacci(rates, count)
    liquidity    = detect_liquidity_proximity(rates, count)

    return {
        "trend":        trend,
        "high":         round(float(df["high"].max()), 3),
        "low":          round(float(df["low"].min()),  3),
        "last_close":   round(float(last["close"]),    3),
        "avg_range":    round(
            float((df["high"] - df["low"]).mean()), 3
        ),
        "support":      support,
        "resistance":   resistance,
        "indicators":   indicators,
        "order_blocks": order_blocks,
        "fibonacci":    fibonacci,
        "liquidity":    liquidity,
    }


def get_current_atr(symbol: str) -> float:
    """ATR الحالي من H1 — للاستخدام في signal_tracker."""
    if not ensure_mt5_connected():
        return 5.0 if symbol == "XAUUSD" else 0.1

    try:
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(
            symbol, mt5.TIMEFRAME_H1, 0, 20
        )
        if rates is None or len(rates) < 14:
            return 5.0 if symbol == "XAUUSD" else 0.1

        ind = calculate_indicators(rates)
        return ind.get("atr", 5.0)

    except Exception:
        return 5.0 if symbol == "XAUUSD" else 0.1