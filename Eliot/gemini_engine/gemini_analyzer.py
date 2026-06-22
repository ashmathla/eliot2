# gemini_engine/gemini_analyzer.py

import requests
from config.settings import GEMINI_API_KEY

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL   = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


def _build_prompt(symbol: str, result: dict) -> str:
    """
    يبني الـ prompt المُرسل لـ Gemini بناءً على نتيجة analyze_market.
    """
    setup          = result.get("trade_setup", {})
    recommendation = result.get("recommendation", {})

    direction       = setup.get("direction", "neutral")
    signal          = setup.get("signal", "NO_TRADE")
    entry           = setup.get("current_price")
    targets         = setup.get("targets", [])
    trade_stop      = setup.get("trade_stop")
    structural_stop = setup.get("structural_stop")
    catastrophic    = setup.get("catastrophic_stop")
    expected_wave   = setup.get("expected_wave")
    confidence      = result.get("confidence", 0)
    signal_mode     = recommendation.get("signal_mode", "")
    reasons         = recommendation.get("reasons", [])

    reasons_text = "\n".join(f"- {r}" for r in reasons)

    prompt = f"""
أنت محلل فني محترف متخصص في موجات إليوت (Elliott Wave) وهيكل السوق (Market Structure).

لديك توصية تداول آلية تم توليدها بواسطة نظام تحليل كمي. مهمتك:

1. اشرح هذه التوصية بلغة عربية واضحة وبسيطة لمتداول متوسط الخبرة (3-4 جمل فقط).
2. أعطِ رأياً ثانياً مستقلاً: هل ترى التوصية منطقية فنياً بناءً على المعطيات؟ هل هناك مخاطر أو نقاط ضعف لم يذكرها النظام؟
3. لا تُصدر توصية تداول جديدة أو تُغيّر الأرقام؛ فقط علّق على جودة وقوة التوصية الحالية.
4. كن صريحاً إن كانت الثقة منخفضة أو المخاطرة مرتفعة.

بيانات التوصية:

الزوج: {symbol}
الاتجاه: {direction}
الإشارة: {signal}
وضع الإشارة: {signal_mode}
نسبة الثقة: {confidence}%

سعر الدخول الحالي: {entry}
الأهداف (TP): {targets}

SL تكتيكي (Trade Stop): {trade_stop}
SL هيكلي (Structural Stop): {structural_stop}
SL كارثي (Elliott Invalidation): {catastrophic}

الموجة المتوقعة التالية: {expected_wave}

أسباب التوصية من النظام:
{reasons_text}

أعطني الإجابة بصيغة:

📝 الشرح:
<شرحك هنا>

🔍 الرأي الثاني:
<رأيك هنا>

⚠️ نقاط يجب الانتباه لها:
<نقطة أو نقطتين كحد أقصى، أو "لا توجد ملاحظات إضافية">
""".strip()

    return prompt


def analyze_with_gemini(symbol: str, result: dict) -> str | None:
    """
    يرسل التوصية إلى Gemini ويُرجع التحليل النصي.

    Returns:
        نص التحليل، أو None في حال الفشل أو عدم وجود توصية صالحة.
    """
    setup     = result.get("trade_setup", {})
    direction = setup.get("direction", "neutral")
    signal    = setup.get("signal", "NO_TRADE")

    if direction not in ("buy", "sell") or signal == "NO_TRADE":
        print("[Gemini] لا توجد توصية لتحليلها")
        return None

    if not GEMINI_API_KEY:
        print("[Gemini] ⚠️ GEMINI_API_KEY غير محدد في .env")
        return None

    prompt = _build_prompt(symbol, result)

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 600,
        }
    }

    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"

    try:
        response = requests.post(url, json=payload, timeout=20)

        if response.status_code != 200:
            print(f"[Gemini] ❌ فشل الطلب: {response.status_code} — {response.text}")
            return None

        data = response.json()
        candidates = data.get("candidates", [])

        if not candidates:
            print("[Gemini] ⚠️ لم يُرجع Gemini أي محتوى")
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        text  = "".join(p.get("text", "") for p in parts).strip()

        if not text:
            print("[Gemini] ⚠️ المحتوى المُستلم فارغ")
            return None

        print("[Gemini] ✅ تم استلام التحليل")
        return text

    except Exception as e:
        print(f"[Gemini] ❌ خطأ في الاتصال: {e}")
        return None