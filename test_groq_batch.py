"""
اختبار نظام الترجمة الدفعي باستخدام Groq
"""

import asyncio
import os
from groq_batch_translator import GroqBatchTranslator

async def test_batch_translation():
    """اختبار الترجمة الدفعية"""
    
    print("=== اختبار نظام الترجمة الدفعي باستخدام Groq ===\n")
    
    # إنشاء مثيل من المترجم
    translator = GroqBatchTranslator()
    
    # التحقق من حالة الخدمة
    status = translator.get_status()
    print(f"حالة الخدمة: {status}\n")
    
    if not status["available"]:
        print("❌ الخدمة غير متاحة!")
        print("تأكد من تعيين متغير البيئة GROQ_API_KEY")
        print("مثال: export GROQ_API_KEY='your_api_key_here'")
        return
    
    print("✅ الخدمة متاحة!\n")
    
    # اختبار 1: ترجمة نص بسيط
    print("--- اختبار 1: ترجمة نص بسيط ---")
    simple_text = "Hello, how are you today?"
    try:
        translated = await translator.translate_text(simple_text)
        print(f"النص الأصلي: {simple_text}")
        print(f"النص المترجم: {translated}")
        print("✅ نجح الاختبار\n")
    except Exception as e:
        print(f"❌ فشل الاختبار: {e}\n")
    
    # اختبار 2: ترجمة عدة أسطر
    print("--- اختبار 2: ترجمة عدة أسطر ---")
    lines = [
        "Good morning!",
        "How are you doing?",
        "Have a wonderful day!",
        "See you later!"
    ]
    try:
        translated_lines = await translator.translate_lines(lines)
        print("النتائج:")
        for i, (original, translated) in enumerate(translated_lines, 1):
            print(f"{i}. الأصلي: {original}")
            print(f"   المترجم: {translated}")
        print("✅ نجح الاختبار\n")
    except Exception as e:
        print(f"❌ فشل الاختبار: {e}\n")
    
    # اختبار 3: ترجمة فقرة طويلة
    print("--- اختبار 3: ترجمة فقرة طويلة ---")
    long_paragraph = """
    This is a comprehensive test of the batch translation system.
    It includes multiple sentences to demonstrate how the system handles
    longer text blocks. The entire paragraph is sent as one unit to the API,
    which should provide better context and more coherent translation.
    This approach is more efficient than translating sentence by sentence.
    """
    try:
        translated_paragraph = await translator.translate_document(long_paragraph)
        print("الفقرة الأصلية:")
        print(long_paragraph.strip())
        print("\nالفقرة المترجمة:")
        print(translated_paragraph.strip())
        print("✅ نجح الاختبار\n")
    except Exception as e:
        print(f"❌ فشل الاختبار: {e}\n")
    
    # اختبار 4: ترجمة نص تقني
    print("--- اختبار 4: ترجمة نص تقني ---")
    technical_text = """
    The API provides batch translation capabilities for processing large amounts of text.
    It uses advanced machine learning models to ensure accurate translations.
    The system supports multiple languages and can handle various text formats.
    """
    try:
        translated_technical = await translator.translate_text(technical_text)
        print("النص التقني الأصلي:")
        print(technical_text.strip())
        print("\nالنص التقني المترجم:")
        print(translated_technical.strip())
        print("✅ نجح الاختبار\n")
    except Exception as e:
        print(f"❌ فشل الاختبار: {e}\n")
    
    print("=== انتهى الاختبار ===")

async def test_with_different_models():
    """اختبار مع نماذج مختلفة"""
    
    print("\n=== اختبار مع نماذج مختلفة ===\n")
    
    translator = GroqBatchTranslator()
    
    if not translator.get_status()["available"]:
        print("❌ الخدمة غير متاحة للاختبار")
        return
    
    # قائمة النماذج المتاحة
    models = [
        "gemma2-9b-it",
        "llama3-8b-8192",
        "mixtral-8x7b-32768"
    ]
    
    test_text = "Hello, this is a test of different models for translation."
    
    for model in models:
        print(f"--- اختبار النموذج: {model} ---")
        try:
            translator.set_model(model)
            translated = await translator.translate_text(test_text)
            print(f"النص الأصلي: {test_text}")
            print(f"المترجم: {translated}")
            print("✅ نجح الاختبار\n")
        except Exception as e:
            print(f"❌ فشل الاختبار مع النموذج {model}: {e}\n")

if __name__ == "__main__":
    print("بدء اختبار نظام الترجمة الدفعي...")
    
    # تشغيل الاختبارات
    asyncio.run(test_batch_translation())
    asyncio.run(test_with_different_models())