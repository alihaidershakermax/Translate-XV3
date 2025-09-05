# نظام الترجمة الدفعي باستخدام Groq

نظام ترجمة مبسط يستخدم مكتبة Groq للترجمة الدفعية (batch translation) بدلاً من التدفق (streaming).

## المميزات

- ✅ **ترجمة دفعية**: إرسال النص ككتلة واحدة والحصول على الترجمة كاملة
- ✅ **بدون streaming**: لا تدفق سطر بسطر، بل ترجمة كاملة دفعة واحدة
- ✅ **دعم متعدد النماذج**: دعم نماذج Groq المختلفة
- ✅ **دعم متعدد اللغات**: ترجمة إلى لغات مختلفة
- ✅ **إدارة API**: إدارة متقدمة لمفاتيح API
- ✅ **سهولة الاستخدام**: واجهة بسيطة ومباشرة

## التثبيت

1. تأكد من تثبيت المكتبات المطلوبة:
```bash
pip install groq
```

2. احصل على مفتاح API من [Groq Console](https://console.groq.com/)

3. اضبط متغير البيئة:
```bash
export GROQ_API_KEY="your_api_key_here"
```

## الاستخدام السريع

### مثال 1: ترجمة نص بسيط

```python
import asyncio
from groq_batch_translator import GroqBatchTranslator

async def main():
    # إنشاء مثيل من المترجم
    translator = GroqBatchTranslator()
    
    # ترجمة نص واحد
    text = "Hello, how are you today?"
    translated = await translator.translate_text(text)
    print(f"المترجم: {translated}")

asyncio.run(main())
```

### مثال 2: ترجمة عدة أسطر

```python
async def translate_lines():
    translator = GroqBatchTranslator()
    
    lines = [
        "Good morning!",
        "How are you?",
        "Have a great day!"
    ]
    
    translated_lines = await translator.translate_lines(lines)
    
    for original, translated in translated_lines:
        print(f"الأصلي: {original}")
        print(f"المترجم: {translated}")
```

### مثال 3: ترجمة مستند كامل

```python
async def translate_document():
    translator = GroqBatchTranslator()
    
    document = """
    This is a complete document that needs translation.
    It contains multiple paragraphs and sentences.
    The entire document will be translated as one block.
    """
    
    translated_document = await translator.translate_document(document)
    print(translated_document)
```

## النماذج المدعومة

| النموذج | الوصف | الحد الأقصى للرموز |
|---------|--------|-------------------|
| `gemma2-9b-it` | نموذج سريع ومتقدم (افتراضي) | 8,192 |
| `llama3-8b-8192` | نموذج قوي للترجمة العامة | 8,192 |
| `mixtral-8x7b-32768` | نموذج متقدم للترجمة المعقدة | 32,768 |
| `llama3-70b-8192` | نموذج قوي جداً للترجمة الدقيقة | 8,192 |

### تغيير النموذج

```python
translator = GroqBatchTranslator()
translator.set_model("mixtral-8x7b-32768")
```

## اللغات المدعومة

- Arabic (العربية)
- English (الإنجليزية)
- French (الفرنسية)
- Spanish (الإسبانية)
- German (الألمانية)
- Italian (الإيطالية)
- Portuguese (البرتغالية)
- Russian (الروسية)
- Chinese (الصينية)
- Japanese (اليابانية)
- Korean (الكورية)

### تغيير اللغة المستهدفة

```python
translator = GroqBatchTranslator()
translator.set_target_language("French")
```

## تخصيص المعاملات

```python
# تغيير معاملات النموذج
translator.api_manager.set_parameters(
    temperature=0.5,    # الإبداع (0.0 - 1.0)
    max_tokens=4096,    # الحد الأقصى للرموز
    top_p=0.9          # التنويع (0.0 - 1.0)
)
```

## فحص حالة الخدمة

```python
translator = GroqBatchTranslator()
status = translator.get_status()

print(f"الخدمة متاحة: {status['available']}")
print(f"النموذج المستخدم: {status['model']}")
print(f"اللغة المستهدفة: {status['target_language']}")
```

## الحصول على المعلومات

```python
# النماذج المتاحة
models = translator.get_available_models()
print(models)

# اللغات المدعومة
languages = translator.get_supported_languages()
print(languages)
```

## الاختبار

لتشغيل الاختبارات:

```bash
python test_groq_batch.py
```

## الملفات

- `groq_batch_translator.py`: النظام الرئيسي للترجمة الدفعية
- `groq_config.py`: إعدادات التكوين والنماذج
- `test_groq_batch.py`: ملف الاختبارات
- `README_groq_batch.md`: هذا الملف

## الفرق عن الترجمة العادية

| الترجمة العادية | الترجمة الدفعية |
|------------------|------------------|
| تدفق سطر بسطر | كتلة واحدة |
| استدعاءات متعددة | استدعاء واحد |
| أبطأ | أسرع |
| سياق محدود | سياق أفضل |
| تكلفة أعلى | تكلفة أقل |

## نصائح للاستخدام الأمثل

1. **استخدم النماذج المناسبة**: 
   - `gemma2-9b-it` للنصوص البسيطة
   - `mixtral-8x7b-32768` للنصوص المعقدة

2. **اضبط المعاملات**:
   - `temperature=0.3` للترجمة الدقيقة
   - `temperature=0.7` للترجمة الإبداعية

3. **جمّع النصوص**: أرسل نصوص طويلة ككتلة واحدة للحصول على سياق أفضل

4. **راقب الاستخدام**: راقب حدود API لتجنب تجاوز الحدود

## استكشاف الأخطاء

### خطأ: "الخدمة غير متاحة"
- تأكد من تعيين `GROQ_API_KEY`
- تحقق من صحة مفتاح API

### خطأ: "النموذج غير مدعوم"
- استخدم النماذج المدعومة فقط
- راجع قائمة النماذج المتاحة

### خطأ: "اللغة غير مدعومة"
- استخدم اللغات المدعومة فقط
- راجع قائمة اللغات المتاحة

## الدعم

للمساعدة أو الإبلاغ عن مشاكل، يرجى مراجعة:
- [Groq Documentation](https://console.groq.com/docs)
- [Groq API Reference](https://console.groq.com/docs/quickstart)