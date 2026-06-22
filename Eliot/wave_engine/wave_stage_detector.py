from wave_engine.wave_sequencer import (
    build_wave_sequence
)


def detect_wave_stage(swings):

    sequence = build_wave_sequence(swings)

    if not sequence:
        return {
            "current_wave": "unknown",
            "next_wave": "unknown",
            "confidence": 0
        }

    last_wave = sequence[-1]

    if last_wave["wave"] == "wave_5":

        wave5_index = last_wave["index"]

        future_swings = [
            s for s in swings
            if s["index"] > wave5_index
        ]

        # لا يوجد شيء بعد الخامسة
        if len(future_swings) == 0:

            return {
                "current_wave": "wave_5",
                "next_wave": "wave_A",
                "confidence": 80
            }

        # بدأ التصحيح (wave_A جارية)
        if len(future_swings) == 1:

            return {
                "current_wave": "wave_A",
                "next_wave": "wave_B",
                "confidence": 80
            }

        # لدينا A و B (wave_B جارية)
        if len(future_swings) == 2:

            return {
                "current_wave": "wave_B",
                "next_wave": "wave_C",
                "confidence": 80
            }

        # لدينا A B C (wave_C جارية أو مكتملة)
        return {
            "current_wave": "wave_C",
            "next_wave": "trend_resumption",
            "confidence": 80
        }

    # إذا وصلنا هنا، فنحن في تصحيح (ABC)
    # أي تصحيح بعد impulse يبدأ بـ wave_A (ليس wave_C مباشرة)
    
    return {
        "current_wave": "wave_A",
        "next_wave": "wave_B",
        "confidence": 70
    }
