# recommendation_engine/trade_setup_builder.py


# ── إعدادات الـ ATR Buffer ────────────────────────
ATR_MULTIPLIER       = 1.5     # عدد مرات ATR المستخدمة كهامش أمان (invalidation)
EXECUTION_ATR_RATIO  = 0.5     # نسبة ATR المستخدمة لعرض منطقة التنفيذ الفعلية
FALLBACK_PERCENTAGE  = 0.003   # 0.3% — يُستخدم فقط إذا ATR غير متاح

# إشارات الدخول الفوري
IMMEDIATE_SIGNALS = (
    "SELL_NOW", "BUY_NOW",
    "SELL_NOW_EARLY", "BUY_NOW_EARLY",
    "STRONG_SELL", "STRONG_BUY",
    "STRONG_SELL_EARLY", "STRONG_BUY_EARLY",
)


def _last_price(pivot_list: list) -> float | None:
    if pivot_list:
        return pivot_list[-1]["price"]
    return None


def _calc_invalidation_sell(current_price, h1_highs, w1_highs, atr_h1):
    last_high = _last_price(h1_highs)
    source    = "H1"
    if last_high is None or (current_price is not None and last_high <= current_price):
        fallback = _last_price(w1_highs)
        if fallback is not None:
            last_high = fallback
            source    = "W1"
    if last_high is None:
        return None, "لا توجد بيانات pivots كافية"
    if atr_h1 is not None and atr_h1 > 0:
        buffer = atr_h1 * ATR_MULTIPLIER
        value  = round(last_high + buffer, 5)
        method = f"{source} last_high + {ATR_MULTIPLIER}xATR (ref={last_high}, ATR={atr_h1}, buffer={round(buffer,5)})"
        return value, method
    value  = round(last_high * (1 + FALLBACK_PERCENTAGE), 5)
    method = f"{source} last_high x {1+FALLBACK_PERCENTAGE} (ref={last_high}, fallback)"
    return value, method


def _calc_invalidation_buy(current_price, h1_lows, w1_lows, atr_h1):
    last_low = _last_price(h1_lows)
    source   = "H1"
    if last_low is None or (current_price is not None and last_low >= current_price):
        fallback = _last_price(w1_lows)
        if fallback is not None:
            last_low = fallback
            source   = "W1"
    if last_low is None:
        return None, "لا توجد بيانات pivots كافية"
    if atr_h1 is not None and atr_h1 > 0:
        buffer = atr_h1 * ATR_MULTIPLIER
        value  = round(last_low - buffer, 5)
        method = f"{source} last_low - {ATR_MULTIPLIER}xATR (ref={last_low}, ATR={atr_h1}, buffer={round(buffer,5)})"
        return value, method
    value  = round(last_low * (1 - FALLBACK_PERCENTAGE), 5)
    method = f"{source} last_low x {1-FALLBACK_PERCENTAGE} (ref={last_low}, fallback)"
    return value, method


def _calc_structural_stop_sell(d1_highs, w1_highs):
    """آخر high على D1 — وإن لم يتوفر فآخر high على W1."""
    val = _last_price(d1_highs)
    return val if val is not None else _last_price(w1_highs)


def _calc_structural_stop_buy(d1_lows, w1_lows):
    """آخر low على D1 — وإن لم يتوفر فآخر low على W1."""
    val = _last_price(d1_lows)
    return val if val is not None else _last_price(w1_lows)


def _calc_catastrophic_stop_sell(w1_highs):
    """
    wave_4 high = ثاني آخر قمة على W1
    كسرها يلغي العدّ الموجي الهابط كله.
    """
    if len(w1_highs) < 2:
        return None
    return w1_highs[-2]["price"]


def _calc_catastrophic_stop_buy(w1_lows):
    """
    wave_4 low = ثاني آخر قاع على W1
    كسره يلغي العدّ الموجي الصاعد كله.
    """
    if len(w1_lows) < 2:
        return None
    return w1_lows[-2]["price"]


def _build_targets_sell(current_price, h1_lows, w1_lows, fib_swing_low):
    candidates = []
    h1_low = _last_price(h1_lows)
    if h1_low is not None:
        candidates.append(h1_low)
    w1_low = _last_price(w1_lows)
    if w1_low is not None:
        candidates.append(w1_low)
    if fib_swing_low is not None:
        candidates.append(fib_swing_low)
    if current_price is not None:
        candidates = [c for c in candidates if c < current_price]
    return sorted(set(candidates), reverse=True)


def _build_targets_buy(current_price, h1_highs, w1_highs, fib_extension_127):
    candidates = []
    h1_high = _last_price(h1_highs)
    if h1_high is not None:
        candidates.append(h1_high)
    w1_high = _last_price(w1_highs)
    if w1_high is not None:
        candidates.append(w1_high)
    if fib_extension_127 is not None:
        candidates.append(fib_extension_127)
    if current_price is not None:
        candidates = [c for c in candidates if c > current_price]
    return sorted(set(candidates))


def format_distance(price_diff, pip_multiplier, reference_price=None):
    price_diff = abs(price_diff)
    if pip_multiplier >= 10000:
        return f"{round(price_diff * pip_multiplier, 1)} pip"
    if pip_multiplier <= 100:
        if reference_price is not None and reference_price >= 1000:
            return f"${round(price_diff, 2)}"
        if pip_multiplier == 100:
            return f"{round(price_diff * pip_multiplier, 1)} pip"
    return f"{round(price_diff * pip_multiplier, 1)} point"


def _build_execution_zone(current_price, atr_h1, fallback_zone):
    if current_price is None:
        return fallback_zone
    if atr_h1 is not None and atr_h1 > 0:
        half_width = atr_h1 * EXECUTION_ATR_RATIO
        return [
            round(current_price - half_width, 5),
            round(current_price + half_width, 5),
        ]
    return fallback_zone


STALE_ZONE_RATIO = 1.0


def _check_zone_validity(current_price, zone):
    if current_price is None or not zone or len(zone) != 2:
        return True
    zone_low, zone_high = sorted(zone)
    width = zone_high - zone_low
    if width <= 0:
        return True
    if current_price < zone_low:
        return (zone_low - current_price) <= (width * STALE_ZONE_RATIO)
    if current_price > zone_high:
        return (current_price - zone_high) <= (width * STALE_ZONE_RATIO)
    return True


def build_trade_setup(
    recommendation,
    elliott,
    fib,
    pivots,
    wave_context,
    current_price: float = None,
    atr_h1: float = None,
    pip_multiplier: float = 10000,
    h1_pivots: dict | None = None,
    d1_pivots: dict | None = None,
):
    """
    يبني خطة التداول الكاملة مع ثلاثة مستويات للـ Stop Loss:

        trade_stop        : SL تكتيكي (H1 ATR) — يُثبَّت وقت الإشارة
        structural_stop   : SL هيكلي  (D1 swing) — يتغير نادراً
        catastrophic_stop : SL كارثي  (أقصى/أدنى W1) — يلغي السيناريو كله
    """

    direction = recommendation.get("direction", "neutral")

    w1_highs = pivots.get("highs", [])
    w1_lows  = pivots.get("lows",  [])

    h1_pivots = h1_pivots or {}
    h1_highs  = h1_pivots.get("highs", [])
    h1_lows   = h1_pivots.get("lows",  [])

    d1_pivots = d1_pivots or {}
    d1_highs  = d1_pivots.get("highs", [])
    d1_lows   = d1_pivots.get("lows",  [])

    if not w1_highs or not w1_lows:
        return {"status": "invalid_setup"}

    expected_wave = wave_context.get("next_expected", "unknown")
    signal        = recommendation["signal"]
    is_immediate  = signal in IMMEDIATE_SIGNALS

    setup = {
        "signal"             : signal,
        "direction"          : direction,
        "expected_wave"      : expected_wave,
        "strategic_zone"     : [],
        "execution_zone"     : [],
        "entry_zone"         : [],
        "zone_valid"         : True,
        "trade_stop"         : None,   # SL تكتيكي — ثابت بعد الإشارة
        "structural_stop"    : None,   # SL هيكلي  — D1 swing
        "catastrophic_stop"  : None,   # SL كارثي  — أقصى/أدنى W1
        "invalidation"       : None,   # = trade_stop (توافق مع السابق)
        "invalidation_method": None,
        "atr_h1"             : atr_h1,
        "pip_multiplier"     : pip_multiplier,
        "targets"            : [],
        "current_price"      : current_price,
        "distance_pips"      : None,
        "distance_label"     : None,
        "entry_status"       : None,
    }

    # --------------------
    # SELL SETUP
    # --------------------

    if direction == "sell":

        entry_high = fib["retracement"]["23.6"]
        entry_low  = fib["retracement"]["38.2"]
        strategic_zone = [entry_low, entry_high]

        execution_zone = (
            _build_execution_zone(current_price, atr_h1, strategic_zone)
            if is_immediate else strategic_zone
        )

        zone_valid = is_immediate or _check_zone_validity(current_price, strategic_zone)
        setup["zone_valid"] = zone_valid

        setup["strategic_zone"] = strategic_zone
        if zone_valid:
            setup["execution_zone"] = execution_zone
            setup["entry_zone"]     = strategic_zone
        else:
            setup["execution_zone"] = []
            setup["entry_zone"]     = []

        tactical, t_method = _calc_invalidation_sell(current_price, h1_highs, w1_highs, atr_h1)
        structural         = _calc_structural_stop_sell(d1_highs, w1_highs)
        catastrophic       = _calc_catastrophic_stop_sell(w1_highs)

        setup["trade_stop"]          = tactical
        setup["structural_stop"]     = structural
        setup["catastrophic_stop"]   = catastrophic
        setup["invalidation"]        = tactical
        setup["invalidation_method"] = t_method

        setup["targets"] = _build_targets_sell(
            current_price, h1_lows, w1_lows, fib.get("swing_low")
        )

        if current_price is not None:
            zone_low, zone_high = execution_zone
            zone_mid   = round((zone_low + zone_high) / 2, 5)
            price_diff = abs(current_price - zone_mid)
            setup["distance_pips"]  = round(price_diff * pip_multiplier, 1)
            setup["distance_label"] = format_distance(price_diff, pip_multiplier, reference_price=current_price)

            if zone_low <= current_price <= zone_high:
                setup["entry_status"] = f"في منطقة الدخول (mid: {zone_mid})"
            elif current_price > zone_high:
                setup["entry_status"] = (
                    f"السعر فوق المنطقة بـ {setup['distance_label']} "
                    f"— انتظر تراجع لـ {zone_mid}"
                )
            elif is_immediate:
                setup["entry_status"] = (
                    f"السعر تجاوز منطقة التنفيذ هبوطاً بـ {setup['distance_label']} "
                    f"— الإشارة منتهية"
                )
            else:
                ctx = recommendation.get("context", "")
                setup["entry_status"] = (
                    f"السعر تجاوز منطقة فيبوناتشي W1 (الإستراتيجية) هبوطاً "
                    f"بـ {setup['distance_label']} — هذه المنطقة لم تعد ذات صلة. "
                    f"التوصية الحالية تعتمد على السياق الفراكتلي: {ctx}"
                )

    # --------------------
    # BUY SETUP
    # --------------------

    elif direction == "buy":

        entry_low  = fib["retracement"]["61.8"]
        entry_high = fib["retracement"]["38.2"]
        strategic_zone = [entry_low, entry_high]

        execution_zone = (
            _build_execution_zone(current_price, atr_h1, strategic_zone)
            if is_immediate else strategic_zone
        )

        zone_valid = is_immediate or _check_zone_validity(current_price, strategic_zone)
        setup["zone_valid"] = zone_valid

        setup["strategic_zone"] = strategic_zone
        if zone_valid:
            setup["execution_zone"] = execution_zone
            setup["entry_zone"]     = strategic_zone
        else:
            setup["execution_zone"] = []
            setup["entry_zone"]     = []

        tactical, t_method = _calc_invalidation_buy(current_price, h1_lows, w1_lows, atr_h1)
        structural         = _calc_structural_stop_buy(d1_lows, w1_lows)
        catastrophic       = _calc_catastrophic_stop_buy(w1_lows)

        setup["trade_stop"]          = tactical
        setup["structural_stop"]     = structural
        setup["catastrophic_stop"]   = catastrophic
        setup["invalidation"]        = tactical
        setup["invalidation_method"] = t_method

        setup["targets"] = _build_targets_buy(
            current_price, h1_highs, w1_highs, fib.get("extension", {}).get("127.2")
        )

        if current_price is not None:
            zone_low, zone_high = execution_zone
            zone_mid   = round((zone_low + zone_high) / 2, 5)
            price_diff = abs(current_price - zone_mid)
            setup["distance_pips"]  = round(price_diff * pip_multiplier, 1)
            setup["distance_label"] = format_distance(price_diff, pip_multiplier, reference_price=current_price)

            if zone_low <= current_price <= zone_high:
                setup["entry_status"] = f"في منطقة الدخول (mid: {zone_mid})"
            elif current_price < zone_low:
                setup["entry_status"] = (
                    f"السعر تحت المنطقة بـ {setup['distance_label']} "
                    f"— انتظر ارتداد لـ {zone_mid}"
                )
            elif is_immediate:
                setup["entry_status"] = (
                    f"السعر تجاوز منطقة التنفيذ صعوداً بـ {setup['distance_label']} "
                    f"— الإشارة منتهية"
                )
            else:
                ctx = recommendation.get("context", "")
                setup["entry_status"] = (
                    f"السعر تجاوز منطقة فيبوناتشي W1 (الإستراتيجية) صعوداً "
                    f"بـ {setup['distance_label']} — هذه المنطقة لم تعد ذات صلة. "
                    f"التوصية الحالية تعتمد على السياق الفراكتلي: {ctx}"
                )

    return setup