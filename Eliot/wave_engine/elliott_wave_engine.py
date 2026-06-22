# wave_engine/elliott_wave_engine.py
"""
Elliott Wave Pattern Detection with Phase System.

CHANGE LOG (this revision):
- detect_elliott_pattern now accepts `parent_direction` and forwards it
  to classify_wave (the actual source of truth for the opposite-direction
  check), instead of relying on string-matching parent_pattern.
- The "is this impulse actually opposite to the parent" check is folded
  directly into the impulse branch (no more dead code after an early
  return).
- correction_start (now produced by classify_wave when pattern == "ABC")
  is forwarded into detect_correction instead of being re-derived.
- منع التناقض بين Pattern و Wave (bullish_impulse + wave_C → ABC)
- ✅ استيراد detect_wave_stage من wave_stage_detector (حذف الـ stub)
"""

from wave_engine.wave_classifier import classify_wave
from wave_engine.correction_detector import detect_correction
from wave_engine.wave_stage_detector import detect_wave_stage


def _build_impulse_result(pattern, sequence, classification):
    stage = detect_wave_stage(sequence)
    current_wave = stage["current_wave"]
    next_wave = stage["next_wave"]
    
    # منع التناقض: إذا كان pattern impulse لكن أنت في ABC
    # غيّر pattern إلى ABC وسيأتي phase صحيح من detect_correction
    if (
        pattern in ("bullish_impulse", "bearish_impulse")
        and
        current_wave in ("wave_A", "wave_B", "wave_C")
    ):
        pattern = "ABC"
    
    phase = "impulse_completed" if current_wave == "wave_5" else "impulse_ongoing"
    return {
        "pattern": pattern,
        "current_wave": current_wave,
        "next_wave": next_wave,
        "phase": phase,
        "subwave": None,
        "confidence": int((classification["confidence"] + stage["confidence"]) / 2),
    }


def _build_correction_result(correction):
    if not correction or correction.get("correction_type") in (None, "unknown"):
        return None
    current_wave = correction["current_wave"]
    subwave = correction.get("subwave")
    next_wave = correction["next_expected"]
    phase = (
        "correction_completed"
        if (current_wave == "wave_C" and subwave == "wave_5")
        else "correction_ongoing"
    )
    return {
        "pattern": correction["correction_type"],
        "current_wave": current_wave,
        "next_wave": next_wave,
        "phase": phase,
        "subwave": subwave,
        "confidence": correction["confidence"],
    }


def detect_elliott_pattern(sequence, parent_pattern=None, parent_direction=None):
    """
    كشف نمط إليوت مع الحماية من التناقضات
    
    ✅ يستخدم detect_wave_stage من wave_stage_detector.py (لا stub)
    """
    classification = classify_wave(
        sequence, parent_pattern=parent_pattern, parent_direction=parent_direction
    )
    pattern = classification["pattern"]

    if pattern in ("bullish_impulse", "bearish_impulse"):
        return _build_impulse_result(pattern, sequence, classification)

    # pattern == "ABC" (or any future correction-candidate label)
    correction_start = classification.get("correction_start")
    correction = detect_correction(
        sequence, parent_pattern=parent_pattern, correction_start=correction_start
    )
    correction_result = _build_correction_result(correction)
    if correction_result is not None:
        return correction_result

    return {
        "pattern": "unknown",
        "current_wave": "unknown",
        "next_wave": "unknown",
        "phase": "unknown",
        "subwave": None,
        "confidence": 0,
    }
