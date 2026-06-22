# gemini_engine/groq_analyzer.py
#
# تحليل التوصية باستخدام Groq (بديل مجاني وسريع لـ Gemini).
# يُرسل السياق الموجي الكامل (الموجات + التوافق + قواعد إليوت)
# وليس فقط ملخص التوصية النهائية.

import requests
from config.settings import GROQ_API_KEY

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"


def _format_wave_tf(tf_name: str, wave_data: dict) -> str:
    """
    يُنسّق بيانات إطار زمني واحد من wave_map (W1/D1/H1)
    بدون الـ pivots الخام (تجنباً لتضخيم الـ prompt).
    """
    elliott = wave_data.get("elliott", {})
    context = wave_data.get("context", {})

    return (
        f"  - النمط: {wave_data.get('wave_type', '—')}\n"
        f"  - الموجة الحالية: {elliott.get('current_wave', '—')}\n"
        f"  - الموجة التالية المتوقعة: {elliott.get('next_wave', '—')}\n"
        f"  - ثقة النمط: {elliott.get('confidence', '—')}%\n"
        f"  - السياق الدوري: {context.get('cycle', '—')} "
        f"(التالي المتوقع: {context.get('next_expected', '—')})"
    )


def _format_wave_sequence(wave_sequence: list) -> str:
    """
    يُنسّق تسلسل الموجات الخمس (wave_1 → wave_5) المُستخدم في تصنيف النمط.
    """
    if not wave_sequence:
        return "  لا يوجد تسلسل موجي متاح"

    lines = []
    for w in wave_sequence:
        lines.append(
            f"  {w.get('wave')}: {w.get('type')} @ {w.get('price')} "
            f"(index={w.get('index')})"
        )
    return "\n".join(lines)


def _build_prompt(symbol: str, result: dict) -> str:
    """
    يبني الـ prompt المُرسل إلى Groq، شاملاً:
    - ملخص التوصية النهائية (trade_setup)
    - تسلسل الموجات الخمس (wave_sequence)
    - حالة كل إطار زمني W1/D1/H1 (wave_map، بدون pivots خام)
    - تفاصيل توافق الموجات الكاملة (wave_alignment)
    - قواعد إليوت (elliott_rules)
    """
    setup          = result.get("trade_setup", {})
    recommendation = result.get("recommendation", {})
    wave_map       = result.get("wave_map", {})
    wave_alignment = result.get("wave_alignment", {})
    elliott_rules  = result.get("elliott_rules", {})
    wave_sequence  = result.get("wave_sequence", [])
    wave_context   = result.get("wave_context", {})

    direction       = setup.get("direction", "neutral")
    signal          = setup.get("signal", "NO_TRADE")
    entry           = setup.get("current_price")
    targets         = setup.get("targets", [])
    trade_stop      = setup.get("trade_stop")
    structural_stop = setup.get("structural_stop")
    catastrophic    = setup.get("catastrophic_stop")
    expected_wave   = setup.get("expected_wave")
    confidence      = result.get("confidence", 0)
    wave_score      = result.get("wave_score", 0)
    signal_mode     = recommendation.get("signal_mode", "")
    reasons         = recommendation.get("reasons", [])

    reasons_text = "\n".join(f"- {r}" for r in reasons)

    # ── تفاصيل توافق الفريمات الكاملة ──────────────
    alignment_details = wave_alignment.get("details", [])
    alignment_text = "\n".join(f"- {d}" for d in alignment_details)
    if not alignment_text:
        alignment_text = "لا توجد تفاصيل توافق"

    # ── حالة كل فريم (W1/D1/H4/H1) ──────────────────
    tf_sections = []
    for tf in ("W1", "D1", "H4", "H1"):
        tf_data = wave_map.get(tf)
        if tf_data:
            tf_sections.append(f"{tf}:\n{_format_wave_tf(tf, tf_data)}")
    tf_text = "\n\n".join(tf_sections)

    # ── قواعد إليوت ─────────────────────────────────
    rules_reasons = elliott_rules.get("reasons", [])
    rules_text = ", ".join(rules_reasons) if rules_reasons else "—"

    prompt = f"""
أنت محلل فني محترف متخصص في موجات إليوت (Elliott Wave) وهيكل السوق (Market Structure).

لديك تحليل موجي كامل متعدد الفريمات تم توليده بواسطة نظام تحليل كمي آلي،
بالإضافة إلى توصية التداول النهائية المُستخرجة منه. مهمتك:

1. اشرح الصورة الموجية الكاملة (W1 + D1 + H1) ببساطة، وكيف أدت إلى التوصية النهائية (4-6 جمل).
2. قيّم مدى تماسك التوافق بين الفريمات الأربعة (W1/D1/H4/H1) بناءً على تفاصيل alignment أدناه — هل هو توافق قوي حقاً أم هناك تضارب يستحق الانتباه؟ انتبه خاصة لدور H4 كفلتر تأكيد هيكلي بين D1 وH1.
3. أعطِ رأياً ثانياً مستقلاً في جودة التوصية، بالاستفادة من السياق الموجي الكامل وليس فقط الأرقام النهائية.
4. لا تُصدر توصية تداول جديدة أو تُغيّر الأرقام؛ فقط حلّل وعلّق.
5. كن صريحاً إن وجدت تناقضاً بين الفريمات أو ضعفاً في القواعد الموجية (elliott_rules).

═══════════════════════════════
السياق الموجي الكامل
═══════════════════════════════

تسلسل الموجات الخمس (الأساس الذي صُنّف عليه النمط):
{_format_wave_sequence(wave_sequence)}

السياق الموجي العام:
- الدورة الحالية: {wave_context.get('cycle', '—')}
- المتوقع لاحقاً: {wave_context.get('next_expected', '—')}

حالة كل إطار زمني:
{tf_text}

توافق الفريمات (Wave Alignment):
- متوافق: {wave_alignment.get('aligned', '—')}
- درجة التوافق: {wave_alignment.get('score', '—')}/100
تفاصيل التوافق:
{alignment_text}

درجة الموجة الإجمالية (Wave Score): {wave_score}/100

قواعد إليوت (Elliott Rules):
- صالحة: {elliott_rules.get('valid', '—')}
- الدرجة: {elliott_rules.get('score', '—')}/100
- الملاحظات: {rules_text}

═══════════════════════════════
التوصية النهائية المُستخرجة
═══════════════════════════════

الزوج: {symbol}
الاتجاه: {direction}
الإشارة: {signal}
وضع الإشارة: {signal_mode}
نسبة الثقة الكلية: {confidence}%

سعر الدخول الحالي: {entry}
الأهداف (TP): {targets}

SL تكتيكي (Trade Stop): {trade_stop}
SL هيكلي (Structural Stop): {structural_stop}
SL كارثي (Elliott Invalidation): {catastrophic}

الموجة المتوقعة التالية: {expected_wave}

أسباب التوصية من النظام:
{reasons_text}

═══════════════════════════════

أعطني الإجابة بصيغة:

📊 الصورة الموجية الكاملة:
<شرحك لـ W1/D1/H1 وكيف تشكلت التوصية>

🔗 تقييم التوافق بين الفريمات:
<تقييمك لقوة/ضعف alignment الحقيقي>

🔍 الرأي الثاني:
<رأيك المستقل في جودة التوصية ككل>

⚠️ نقاط يجب الانتباه لها:
<أهم نقطة أو نقطتين، أو "لا توجد ملاحظات إضافية">
""".strip()

    return prompt


def _clean_punctuation(text: str) -> str:
    """
    يستبدل علامات ترقيم غير عربية/إنجليزية (تظهر أحياناً من نماذج
    متعددة اللغات مثل الصينية) بمكافئها العربي أو الإنجليزي القياسي.
    """
    replacements = {
        "，": "، ",   # فاصلة صينية → فاصلة عربية
        "。": ". ",   # نقطة صينية → نقطة إنجليزية
        "；": "؛ ",   # فاصلة منقوطة صينية → عربية
        "：": ": ",   # نقطتان صينية → إنجليزية
        "（": "(",
        "）": ")",
        "！": "!",
        "？": "؟",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # تنظيف أي مسافات مضاعفة نتجت عن الاستبدال
    while "  " in text:
        text = text.replace("  ", " ")

    return text


def analyze_with_gemini(symbol: str, result: dict) -> str | None:
    """
    يرسل السياق الموجي الكامل + التوصية إلى Groq ويُرجع التحليل النصي.
    (الاسم محفوظ كـ analyze_with_gemini للتوافق مع main.py الحالي.)

    Returns:
        نص التحليل، أو None في حال الفشل أو عدم وجود توصية صالحة.
    """
    setup     = result.get("trade_setup", {})
    direction = setup.get("direction", "neutral")
    signal    = setup.get("signal", "NO_TRADE")

    if direction not in ("buy", "sell") or signal == "NO_TRADE":
        print("[Groq] لا توجد توصية لتحليلها")
        return None

    if not GROQ_API_KEY:
        print("[Groq] ⚠️ GROQ_API_KEY غير محدد في .env")
        return None

    prompt = _build_prompt(symbol, result)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type" : "application/json",
    }

    payload = {
        "model"      : GROQ_MODEL,
        "messages"   : [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "max_tokens" : 1000,
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            print(f"[Groq] ❌ فشل الطلب: {response.status_code} — {response.text}")
            return None

        data    = response.json()
        choices = data.get("choices", [])

        if not choices:
            print("[Groq] ⚠️ لم يُرجع Groq أي محتوى")
            return None

        text = choices[0].get("message", {}).get("content", "").strip()

        if not text:
            print("[Groq] ⚠️ المحتوى المُستلم فارغ")
            return None

        text = _clean_punctuation(text)

        print("[Groq] ✅ تم استلام التحليل (مع السياق الموجي الكامل)")
        return text

    except Exception as e:
        print(f"[Groq] ❌ خطأ في الاتصال: {e}")
        return None