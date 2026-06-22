# main.py

from pprint import pprint

from config.settings import SYMBOL
from config.settings import CANDLE_LIMIT

from data_engine.mt5_connector import (
    connect_mt5,
    shutdown_mt5
)

from analysis_engine.market_analyzer import (
    analyze_market
)

from telegram_bot.telegram_bot import send_signal
from gemini_engine.groq_analyzer import analyze_with_gemini


def main():

    if not connect_mt5():
        return

    result = analyze_market(
        SYMBOL,
        CANDLE_LIMIT
    )

    print("\n========== ELLIOTT ==========")
    pprint(result["elliott"])

    print("\n========== SIGNAL ==========")
    pprint(result["signal"])

    print("\n========== ELLIOTT RULES ==========")
    pprint(result["elliott_rules"])

    print("\n========== WAVE SCORE ==========")
    pprint(result["wave_score"])

    print("\n========== WAVE CONTEXT ==========")
    pprint(result["wave_context"])

    print("\n========== WAVE ALIGNMENT ==========")
    pprint(result["wave_alignment"])

    print("\n========== WAVE MAP ==========")
    pprint(result["wave_map"])

    print("\n========== CONFIDENCE ==========")
    pprint(result["confidence"])

    print("\n========== RECOMMENDATION ==========")
    pprint(result["recommendation"])

    print("\n========== TRADE SETUP ==========")
    pprint(result["trade_setup"])

    # ── تحليل Groq (شرح + رأي ثاني) ────────────────
    print("\n========== AI ANALYSIS (Groq) ==========")
    ai_text = analyze_with_gemini(SYMBOL, result)
    if ai_text:
        print(ai_text)

    # ── إرسال التوصية + التحليل إلى تليغرام ────────
    print("\n========== SENDING TO TELEGRAM ==========")
    sent = send_signal(SYMBOL, result, gemini_text=ai_text)
    print("Sent result:", sent)

    shutdown_mt5()


if __name__ == "__main__":
    main()