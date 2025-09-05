"""
مثال عملي على استخدام نظام الترجمة الدفعي باستخدام Groq
"""

import asyncio
import os
from groq_batch_translator import GroqBatchTranslator

async def example_simple_translation():
    """مثال على الترجمة البسيطة"""
    print("=== مثال 1: الترجمة البسيطة ===")
    
    # إنشاء مثيل من المترجم
    translator = GroqBatchTranslator()
    
    # التحقق من حالة الخدمة
    status = translator.get_status()
    print(f"حالة الخدمة: {status['available']}")
    
    if not status['available']:
        print("⚠️ الخدمة غير متاحة. تأكد من تعيين GROQ_API_KEY")
        return
    
    # ترجمة نص بسيط
    text = "Hello, how are you today? I hope you are doing well."
    print(f"النص الأصلي: {text}")
    
    try:
        translated = await translator.translate_text(text)
        print(f"النص المترجم: {translated}")
        print("✅ نجحت الترجمة!\n")
    except Exception as e:
        print(f"❌ فشلت الترجمة: {e}\n")

async def example_batch_translation():
    """مثال على الترجمة الدفعية"""
    print("=== مثال 2: الترجمة الدفعية ===")
    
    translator = GroqBatchTranslator()
    
    if not translator.get_status()['available']:
        print("⚠️ الخدمة غير متاحة")
        return
    
    # قائمة النصوص للترجمة
    texts = [
        "Good morning!",
        "How are you doing today?",
        "I hope you have a wonderful day!",
        "Thank you for your time.",
        "See you later!"
    ]
    
    print("النصوص الأصلية:")
    for i, text in enumerate(texts, 1):
        print(f"{i}. {text}")
    
    try:
        # ترجمة جميع النصوص كدفعة واحدة
        translated_pairs = await translator.translate_lines(texts)
        
        print("\nالنتائج المترجمة:")
        for i, (original, translated) in enumerate(translated_pairs, 1):
            print(f"{i}. الأصلي: {original}")
            print(f"   المترجم: {translated}")
        
        print("✅ نجحت الترجمة الدفعية!\n")
    except Exception as e:
        print(f"❌ فشلت الترجمة الدفعية: {e}\n")

async def example_document_translation():
    """مثال على ترجمة مستند كامل"""
    print("=== مثال 3: ترجمة مستند كامل ===")
    
    translator = GroqBatchTranslator()
    
    if not translator.get_status()['available']:
        print("⚠️ الخدمة غير متاحة")
        return
    
    # مستند للترجمة
    document = """
    Welcome to our company!
    
    We are pleased to introduce our new product line.
    Our products are designed with the latest technology
    and manufactured with the highest quality standards.
    
    We believe in providing excellent customer service
    and building long-term relationships with our clients.
    
    Thank you for choosing us!
    """
    
    print("المستند الأصلي:")
    print(document.strip())
    
    try:
        # ترجمة المستند ككتلة واحدة
        translated_document = await translator.translate_document(document)
        
        print("\nالمستند المترجم:")
        print(translated_document.strip())
        print("✅ نجحت ترجمة المستند!\n")
    except Exception as e:
        print(f"❌ فشلت ترجمة المستند: {e}\n")

async def example_different_models():
    """مثال على استخدام نماذج مختلفة"""
    print("=== مثال 4: النماذج المختلفة ===")
    
    translator = GroqBatchTranslator()
    
    if not translator.get_status()['available']:
        print("⚠️ الخدمة غير متاحة")
        return
    
    # الحصول على النماذج المتاحة
    models = translator.get_available_models()
    print("النماذج المتاحة:")
    for model_id, info in models.items():
        print(f"- {model_id}: {info['name']} ({info['description']})")
    
    # نص للاختبار
    test_text = "This is a test of different models for translation quality."
    print(f"\nالنص للاختبار: {test_text}")
    
    # اختبار نماذج مختلفة
    test_models = ["gemma2-9b-it", "llama3-8b-8192"]
    
    for model in test_models:
        if model in models:
            print(f"\n--- اختبار النموذج: {model} ---")
            try:
                translator.set_model(model)
                translated = await translator.translate_text(test_text)
                print(f"النتيجة: {translated}")
            except Exception as e:
                print(f"❌ فشل مع النموذج {model}: {e}")

async def example_different_languages():
    """مثال على ترجمة إلى لغات مختلفة"""
    print("\n=== مثال 5: اللغات المختلفة ===")
    
    translator = GroqBatchTranslator()
    
    if not translator.get_status()['available']:
        print("⚠️ الخدمة غير متاحة")
        return
    
    # الحصول على اللغات المدعومة
    languages = translator.get_supported_languages()
    print("اللغات المدعومة:")
    for lang_code, lang_name in languages.items():
        print(f"- {lang_code}: {lang_name}")
    
    # نص للاختبار
    test_text = "Hello, how are you today?"
    print(f"\nالنص للاختبار: {test_text}")
    
    # اختبار لغات مختلفة
    test_languages = ["French", "Spanish", "German"]
    
    for language in test_languages:
        if language in languages:
            print(f"\n--- الترجمة إلى: {language} ---")
            try:
                translator.set_target_language(language)
                translated = await translator.translate_text(test_text)
                print(f"النتيجة: {translated}")
            except Exception as e:
                print(f"❌ فشل مع اللغة {language}: {e}")

async def main():
    """تشغيل جميع الأمثلة"""
    print("🚀 بدء أمثلة نظام الترجمة الدفعي باستخدام Groq\n")
    
    # التحقق من وجود مفتاح API
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("⚠️ تحذير: لم يتم العثور على GROQ_API_KEY")
        print("للاستخدام الكامل، اضبط متغير البيئة:")
        print("export GROQ_API_KEY='your_api_key_here'")
        print("\nسيتم تشغيل الأمثلة مع رسائل تحذيرية...\n")
    
    # تشغيل الأمثلة
    await example_simple_translation()
    await example_batch_translation()
    await example_document_translation()
    await example_different_models()
    await example_different_languages()
    
    print("🎉 انتهت جميع الأمثلة!")
    print("\nللمزيد من المعلومات، راجع README_groq_batch.md")

if __name__ == "__main__":
    asyncio.run(main())