# config/settings.py

import os
from dotenv import load_dotenv

load_dotenv()

# ── الزوج المراد تحليله ───────────────────────────
SYMBOL = os.getenv("SYMBOL", "USDCHF").upper().strip()

TIMEFRAMES = {
    "W1": "W1",
    "D1": "D1",
    "H1": "H1"
}

CANDLE_LIMIT = 500

EMA_PERIOD = 200

# ── تليغرام ───────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Groq (تحليل نصي بديل لـ Gemini) ───────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")