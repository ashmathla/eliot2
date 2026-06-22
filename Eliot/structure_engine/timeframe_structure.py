# structure_engine/timeframe_structure.py

from wave_engine.pivot_detector import (
    get_last_pivots
)

from wave_engine.swing_structure import (
    build_swing_sequence
)

from structure_engine.bos_detector import (
    detect_bos
)

from structure_engine.timeframe_choch import (
    detect_structure_choch
)

def analyze_structure(df):

    pivots = get_last_pivots(
        df
    )

    swings = build_swing_sequence(
        pivots
    )

    bos = detect_bos(
        swings
    )
    choch = detect_structure_choch(
    swings
    )

    return {

    "pivots": pivots,

    "swings": swings,

    "bos": bos,

    "choch": choch
    }