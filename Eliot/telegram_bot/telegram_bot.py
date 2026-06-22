# telegram_bot/telegram_bot.py

import requests
from config.settings import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def _format_signal(symbol: str, result: dict, gemini_text: str | None = None) -> str | None:
    """
    يُنسّق نتيجة التحليل كرسالة توصية جاهزة للإرسال،
    مع إلحاق تحليل Gemini (إن وُجد) في نهاية الرسالة.
    """
    setup          = result.get("trade_setup", {})
    recommendation = result.get("recommendation", {})

    direction = setup.get("direction", "neutral")
    signal    = setup.get("signal", "NO_TRADE")

    if direction not in ("buy", "sell") or signal == "NO_TRADE":
        return None

    action = "🟢 BUY" if direction == "buy" else "🔴 SELL"

    entry = setup.get("current_price")

    targets  = setup.get("targets", [])
    tp_lines = ""
    for i, tp in enumerate(targets, 1):
        tp_lines += f"TP{i}: {tp}\n"
    if not tp_lines:
        tp_lines = "—\n"

    trade_stop      = setup.get("trade_stop")
    structural_stop = setup.get("structural_stop")
    catastrophic    = setup.get("catastrophic_stop")
    expected_wave   = setup.get("expected_wave", "—")

    signal_mode = recommendation.get("signal_mode", "")
    mode_label  = {
        "CONFIRMED" : "✅ مؤكد — Elliott + BOS",
        "AGGRESSIVE": "⚠️ استباقي — Elliott فقط",
        "EARLY"     : "🔍 مبكر — انتظر تأكيد",
    }.get(signal_mode, signal_mode)

    # ── دور H4 (فلتر التأكيد الهيكلي) — يُعرض فقط إن تم فحصه ──
    h4_role  = recommendation.get("h4_role", "not_checked")
    h4_line  = ""
    if h4_role != "not_checked":
        h4_label = {
            "full"   : "✅ H4 يؤكد بقوة كاملة",
            "partial": "🟡 H4 تصحيح/غير حاسم — تأكيد جزئي",
        }.get(h4_role, h4_role)
        h4_line = f"H4 Filter:  {h4_label}\n"

    confidence = result.get("confidence", 0)

    msg = f"""
{action} {symbol.upper()}

Entry:  {entry}

{tp_lines}
SL (Trade):      {trade_stop}
SL (Structure):  {structural_stop}

Elliott Invalidation:
{catastrophic}

Expected Next Wave:
{expected_wave}

━━━━━━━━━━━━━━
{h4_line}Mode:       {mode_label}
Confidence: {confidence}%
Signal:     {signal}
""".strip()

    if gemini_text:
        msg += f"\n\n━━━━━━━━━━━━━━\n🤖 Gemini Analysis\n━━━━━━━━━━━━━━\n{gemini_text}"

    return msg


def send_signal(symbol: str, result: dict, gemini_text: str | None = None) -> bool:
    """
    يُرسل التوصية (مع تحليل Gemini الاختياري) إلى تليغرام.

    ملاحظة: تليغرام يحدد طول الرسالة بـ 4096 حرف. إذا تجاوزت الرسالة
    هذا الحد بسبب نص Gemini، تُقسَّم إلى رسالتين.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] ⚠️ TOKEN أو CHAT_ID غير محدد في .env")
        return False

    message = _format_signal(symbol, result, gemini_text=gemini_text)

    if message is None:
        print("[Telegram] لا توجد توصية للإرسال")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    # ── تقسيم الرسالة إذا تجاوزت حد تليغرام (4096 حرف) ──
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]

    all_sent = True
    for chunk in chunks:
        data = {
            "chat_id"  : TELEGRAM_CHAT_ID,
            "text"     : chunk,
        }
        try:
            response = requests.post(url, data=data, timeout=10)
            if response.status_code != 200:
                print(f"[Telegram] ❌ فشل الإرسال: {response.text}")
                all_sent = False
        except Exception as e:
            print(f"[Telegram] ❌ خطأ في الاتصال: {e}")
            all_sent = False

    if all_sent:
        print(f"[Telegram] ✅ تم إرسال التوصية: {symbol}")

    return all_sent