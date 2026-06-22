# wave_engine/wave_context.py

def build_wave_context(elliott):
    """
    Builds the wave context with next expected wave
    مع دعم موجات ABC الكاملة
    """
    
    context = {
        "pattern": elliott.get("pattern"),
        "current_wave": elliott.get("current_wave"),
        "next_expected": None,
        "cycle": None,
        "confidence": elliott.get("confidence", 0)
    }

    current_wave = elliott.get("current_wave")
    pattern = elliott.get("pattern")

    # 🔵 تحديد الموجة التالية حسب الموجة الحالية (impulse)
    if current_wave == "wave_1":
        context["next_expected"] = "wave_2"
        context["cycle"] = "impulse"
    elif current_wave == "wave_2":
        context["next_expected"] = "wave_3"
        context["cycle"] = "impulse"
    elif current_wave == "wave_3":
        context["next_expected"] = "wave_4"
        context["cycle"] = "impulse"
    elif current_wave == "wave_4":
        context["next_expected"] = "wave_5"
        context["cycle"] = "impulse"
    elif current_wave == "wave_5":
        context["next_expected"] = "wave_A"
        context["cycle"] = "correction"
    
    # 🟠 ABC pattern (تصحيح كامل)
    elif current_wave == "wave_A":
        context["next_expected"] = "wave_B"
        context["cycle"] = "correction"
        context["pattern_type"] = "ABC_ongoing"
    elif current_wave == "wave_B":
        context["next_expected"] = "wave_C"
        context["cycle"] = "correction"
        context["pattern_type"] = "ABC_ongoing"
    elif current_wave == "wave_C":
        context["next_expected"] = "trend_resumption"
        context["cycle"] = "correction"
        context["pattern_type"] = "ABC_completed" if pattern in ("zigzag", "flat", "triangle") else None
    
    else:
        context["next_expected"] = "unknown"
        context["cycle"] = "unknown"

    return context
