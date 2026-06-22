# analysis_engine/market_analyzer.py

import MetaTrader5 as mt5
import pandas as pd

from multi_timeframe_engine.timeframe_loader import load_timeframes
from multi_timeframe_engine.timeframe_summary import analyze_all_timeframes
from multi_timeframe_engine.alignment_engine import calculate_alignment
from multi_timeframe_engine.trend_alignment import advanced_alignment
from trend_engine.weekly_trend import analyze_weekly_trend
from fibonacci_engine.fibonacci import analyze_fibonacci
from volume_engine.volume_analyzer import analyze_volume
from wave_engine.pivot_detector import get_last_pivots
from wave_engine.wave_detector import detect_wave_structure
from wave_engine.swing_structure import build_swing_sequence
from wave_engine.elliott_wave_engine import detect_elliott_pattern
from wave_engine.wave_confidence import calculate_wave_confidence
from structure_engine.bos_detector import detect_bos
from structure_engine.choch_detector import detect_choch
from recommendation_engine.recommendation_builder import build_recommendation
from structure_engine.timeframe_structure import analyze_structure
from entry_engine.entry_decision import build_entry_decision
from wave_engine.wave_context import build_wave_context
from wave_engine.multi_tf_wave_engine import analyze_multi_tf_waves
from wave_engine.wave_alignment import calculate_wave_alignment
from wave_engine.wave_context_engine import detect_wave_context
from wave_engine.wave_sequencer import build_wave_sequence
from wave_engine.wave_score import calculate_wave_score
from recommendation_engine.trade_setup_builder import build_trade_setup
from wave_engine.elliott_rules_validator import validate_elliott_rules
from recommendation_engine.signal_engine import build_signal
from wave_engine.wave_bias import get_wave_bias, get_next_wave_bias


def calc_atr(df: pd.DataFrame, period: int = 14) -> float | None:
    """
    Average True Range — قياس التقلب لإطار زمني معين.
    """
    try:
        if df is None or len(df) < period + 1:
            return None

        required_cols = {"high", "low", "close"}
        if not required_cols.issubset(df.columns):
            return None

        high  = df["high"]
        low   = df["low"]
        close = df["close"]

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs(),
        ], axis=1).max(axis=1)

        atr_value = tr.rolling(period).mean().iloc[-1]

        if pd.isna(atr_value) or atr_value <= 0:
            return None

        return round(float(atr_value), 5)

    except Exception:
        return None


def get_pip_size(symbol: str) -> float:
    """
    يحسب حجم النقطة (pip) الصحيح لأي زوج بناءً على بيانات MT5.
    """
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            return 0.0001

        digits = info.digits
        point  = info.point

        if digits in (3, 5):
            return round(point * 10, 10)

        return point

    except Exception:
        return 0.0001


def get_pip_multiplier(symbol: str) -> float:
    """
    يُرجع المضاعف لتحويل فرق السعر إلى عدد النقاط (pips).
    """
    pip_size = get_pip_size(symbol)
    if pip_size <= 0:
        return 10000

    return round(1 / pip_size, 5)


def analyze_market(symbol, candle_limit):

    # ── السعر الحالي من MT5 ───────────────────
    tick          = mt5.symbol_info_tick(symbol)
    current_price = round(tick.ask, 5) if tick else None

    timeframes = load_timeframes(symbol, candle_limit)
    weekly_df  = timeframes["W1"]

    trend  = analyze_weekly_trend(weekly_df)
    fib    = analyze_fibonacci(weekly_df)
    volume = analyze_volume(weekly_df)
    pivots = get_last_pivots(weekly_df, "W1")
    wave   = detect_wave_structure(pivots)
    swings = build_swing_sequence(pivots)

    wave_sequence = build_wave_sequence(swings)

    print("\nSWINGS")
    print(swings)
    print("\nWAVE SEQUENCE")
    print(wave_sequence)
    print("\nSEQUENCE LENGTH")
    print(len(wave_sequence))

    market_wave_context = detect_wave_context(swings)
    elliott             = detect_elliott_pattern(wave_sequence)
    elliott_rules       = validate_elliott_rules(wave_sequence)
    wave_context        = build_wave_context(elliott)
    summary             = analyze_all_timeframes(timeframes)
    wave_map            = analyze_multi_tf_waves(timeframes)

    weekly_bias      = get_wave_bias(wave_map["W1"])
    daily_bias       = get_wave_bias(wave_map["D1"])
    h4_bias          = get_wave_bias(wave_map["H4"])
    h1_bias          = get_wave_bias(wave_map["H1"])
    weekly_next_bias = get_next_wave_bias(wave_map["W1"])
    daily_next_bias  = get_next_wave_bias(wave_map["D1"])
    h4_next_bias     = get_next_wave_bias(wave_map["H4"])
    h1_next_bias     = get_next_wave_bias(wave_map["H1"])

    print("\nW1 DEBUG")
    print(wave_map["W1"]["elliott"])
    print("bias =", weekly_bias)
    print("\nD1 DEBUG")
    print(wave_map["D1"]["elliott"])
    print("bias =", daily_bias)
    print("\nH4 DEBUG")
    print(wave_map["H4"]["elliott"])
    print("bias =", h4_bias)
    print("\nH1 DEBUG")
    print(wave_map["H1"]["elliott"])
    print("bias =", h1_bias)

    wave_alignment = calculate_wave_alignment(wave_map)
    wave_score     = calculate_wave_score(elliott, wave_context, wave_alignment)

    weekly_structure = analyze_structure(weekly_df)
    daily_structure  = analyze_structure(timeframes["D1"])
    h4_structure     = analyze_structure(timeframes["H4"])
    h1_structure     = analyze_structure(timeframes["H1"])

    entry = build_entry_decision({
        "W1": weekly_structure,
        "D1": daily_structure,
        "H4": h4_structure,
        "H1": h1_structure
    })

    alignment  = calculate_alignment(summary)
    advanced   = advanced_alignment(summary)
    confidence = calculate_wave_confidence(
        elliott,
        fib,
        volume,
        wave_alignment  = wave_alignment,
        trend_alignment = advanced,
        elliott_rules   = elliott_rules,
    )

    weekly_pattern = wave_map["W1"]["elliott"]["pattern"]
    daily_pattern  = wave_map["D1"]["elliott"]["pattern"]
    h4_pattern     = wave_map["H4"]["elliott"]["pattern"]
    h1_pattern     = wave_map["H1"]["elliott"]["pattern"]

    print("\nBIASES")
    print("W1:", weekly_bias)
    print("D1:", daily_bias)
    print("H4:", h4_bias)
    print("H1:", h1_bias)
    print("\nPATTERNS")
    print("W1:", weekly_pattern)
    print("D1:", daily_pattern)
    print("H4:", h4_pattern)
    print("H1:", h1_pattern)

    bos   = detect_bos(
        swings,
        current_price = current_price,
        h1_swings     = wave_map["H1"]["swings"],
    )
    choch = detect_choch(summary)

    # ── تحقق من صحة Elliott قبل المتابعة ─────
    if not elliott_rules["valid"]:
        return {
            "entry"              : {},
            "signal"             : "NO_TRADE",
            "elliott_rules"      : elliott_rules,
            "trend"              : trend,
            "trade_setup"        : {},
            "fib"                : fib,
            "volume"             : volume,
            "pivots"             : pivots,
            "wave"               : wave,
            "swings"             : swings,
            "wave_sequence"      : wave_sequence,
            "elliott"            : elliott,
            "confidence"         : 0,
            "wave_score"         : 0,
            "wave_context"       : wave_context,
            "market_wave_context": market_wave_context,
            "wave_map"           : wave_map,
            "wave_alignment"     : wave_alignment,
            "timeframes"         : summary,
            "alignment"          : alignment,
            "advanced_alignment" : advanced,
            "bos"                : {},
            "choch"              : {},
            "recommendation"     : {
                "signal"    : "NO_TRADE",
                "direction" : "none",
                "score"     : 0,
                "confidence": 0,
                "reasons"   : ["invalid_elliott_structure"]
            },
            "current_price"      : current_price,
            "timeframe_structure": {
                "W1": weekly_structure,
                "D1": daily_structure,
                "H4": h4_structure,
                "H1": h1_structure
            }
        }

    # ── Elliott صحيح — أكمل التحليل الكامل ───

    from recommendation_engine.conflict_resolver import (
        resolve_timeframe_conflict,
        get_entry_signal,
    )
    conflict_result = resolve_timeframe_conflict(
        wave_map["W1"]["elliott"],
        wave_map["D1"]["elliott"],
        wave_map["H1"]["elliott"],
        h4_elliott = wave_map["H4"]["elliott"],
    )

    signal = build_signal(
        weekly_bias,
        daily_bias,
        h1_bias,
        confidence,
        wave_map["W1"]["elliott"]["pattern"],
        wave_map["D1"]["elliott"]["pattern"],
        wave_map["H1"]["elliott"]["pattern"],
        conflict_result = conflict_result,
        bos             = bos,
        h1_elliott      = wave_map["H1"]["elliott"],
    )

    recommendation = build_recommendation(
        trend          = trend,
        elliott        = elliott,
        bos            = bos,
        choch          = choch,
        volume         = volume,
        alignment      = alignment,
        wave_alignment = wave_alignment,
        confidence     = confidence,
        w1_elliott     = wave_map["W1"]["elliott"],
        d1_elliott     = wave_map["D1"]["elliott"],
        h1_elliott     = wave_map["H1"]["elliott"],
        h4_elliott     = wave_map["H4"]["elliott"],
    )

    # ── ATR لفريم H1 ──
    atr_h1 = calc_atr(timeframes.get("H1"), period=14)

    # ── pip multiplier ──
    pip_multiplier = get_pip_multiplier(symbol)

    # 🔴 تعديل حاسم: بناء wave_context من W1 و H1 بشكل منفصل
    # W1 wave_context للفهم الأساسي، H1 wave_context للإدخال والأهداف
    wave_context_w1 = build_wave_context(elliott)  # من W1
    wave_context_h1 = build_wave_context(wave_map["H1"]["elliott"])  # من H1

    trade_setup = build_trade_setup(
        recommendation,
        elliott,
        fib,
        pivots,
        wave_context_h1,  # ✅ استخدم H1 context (الصحيح!)
        current_price  = current_price,
        atr_h1         = atr_h1,
        pip_multiplier = pip_multiplier,
        h1_pivots      = wave_map["H1"]["pivots"],
        d1_pivots      = wave_map["D1"]["pivots"],
    )

    return {
        "entry"              : entry,
        "signal"             : signal,
        "elliott_rules"      : elliott_rules,
        "trend"              : trend,
        "trade_setup"        : trade_setup,
        "fib"                : fib,
        "volume"             : volume,
        "pivots"             : pivots,
        "wave"               : wave,
        "swings"             : swings,
        "wave_sequence"      : wave_sequence,
        "elliott"            : elliott,
        "confidence"         : confidence,
        "wave_score"         : wave_score,
        "wave_context"       : wave_context,
        "market_wave_context": market_wave_context,
        "wave_map"           : wave_map,
        "wave_alignment"     : wave_alignment,
        "timeframes"         : summary,
        "alignment"          : alignment,
        "advanced_alignment" : advanced,
        "bos"                : bos,
        "choch"              : choch,
        "recommendation"     : recommendation,
        "current_price"      : current_price,
        "timeframe_structure": {
            "W1": weekly_structure,
            "D1": daily_structure,
            "H4": h4_structure,
            "H1": h1_structure
        }
    }
