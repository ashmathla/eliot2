# wave_engine/wave_role.py

def get_wave_role(elliott: dict) -> str:

    pattern = elliott.get("pattern", "")
    current = elliott.get("current_wave", "")
    next_wave = elliott.get("next_wave", "")

    # impulse انتهى
    if (
        "impulse" in pattern
        and current == "wave_5"
        and next_wave == "wave_A"
    ):
        return "impulse_completed"

    # impulse ما زال مستمراً
    if "impulse" in pattern:
        return "impulse_active"

    # ABC انتهت
    if (
        pattern == "ABC"
        and current == "wave_C"
    ):
        return "correction_completed"

    # ABC ما زالت مستمرة
    if pattern == "ABC":
        return "correction_active"

    return "unknown"