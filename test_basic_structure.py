"""
اختبار البنية الأساسية للنظام بدون استيراد groq
"""

def test_config_import():
    """اختبار استيراد ملف التكوين"""
    try:
        from groq_config import GroqConfig
        print("✅ تم استيراد GroqConfig بنجاح")
        
        # اختبار الوظائف الأساسية
        models = GroqConfig.get_available_models()
        print(f"✅ النماذج المتاحة: {len(models)} نموذج")
        
        languages = GroqConfig.get_supported_languages()
        print(f"✅ اللغات المدعومة: {len(languages)} لغة")
        
        # اختبار التحقق من النماذج
        valid_model = GroqConfig.validate_model("gemma2-9b-it")
        invalid_model = GroqConfig.validate_model("invalid-model")
        print(f"✅ التحقق من النماذج: صحيح={valid_model}, خاطئ={invalid_model}")
        
        # اختبار التحقق من اللغات
        valid_lang = GroqConfig.validate_language("Arabic")
        invalid_lang = GroqConfig.validate_language("InvalidLanguage")
        print(f"✅ التحقق من اللغات: صحيح={valid_lang}, خاطئ={invalid_lang}")
        
        # اختبار prompt الترجمة
        prompt = GroqConfig.get_translation_prompt("Arabic")
        print(f"✅ prompt الترجمة: {prompt[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ فشل في استيراد GroqConfig: {e}")
        return False

def test_file_structure():
    """اختبار بنية الملفات"""
    import os
    
    required_files = [
        "groq_batch_translator.py",
        "groq_config.py",
        "test_groq_batch.py",
        "README_groq_batch.md"
    ]
    
    print("\n=== فحص الملفات المطلوبة ===")
    all_exist = True
    
    for file in required_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"✅ {file} ({size} bytes)")
        else:
            print(f"❌ {file} غير موجود")
            all_exist = False
    
    return all_exist

def test_syntax():
    """اختبار صحة الصيغة"""
    import ast
    
    files_to_check = [
        "groq_config.py",
        "groq_batch_translator.py"
    ]
    
    print("\n=== فحص صحة الصيغة ===")
    all_valid = True
    
    for file in files_to_check:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # تحليل الصيغة
            ast.parse(content)
            print(f"✅ {file} - صيغة صحيحة")
            
        except SyntaxError as e:
            print(f"❌ {file} - خطأ في الصيغة: {e}")
            all_valid = False
        except Exception as e:
            print(f"❌ {file} - خطأ آخر: {e}")
            all_valid = False
    
    return all_valid

def main():
    """تشغيل جميع الاختبارات"""
    print("=== اختبار البنية الأساسية لنظام الترجمة الدفعي ===\n")
    
    # اختبار استيراد التكوين
    config_ok = test_config_import()
    
    # اختبار بنية الملفات
    files_ok = test_file_structure()
    
    # اختبار صحة الصيغة
    syntax_ok = test_syntax()
    
    print("\n=== ملخص النتائج ===")
    print(f"التكوين: {'✅ نجح' if config_ok else '❌ فشل'}")
    print(f"الملفات: {'✅ نجح' if files_ok else '❌ فشل'}")
    print(f"الصيغة: {'✅ نجح' if syntax_ok else '❌ فشل'}")
    
    if config_ok and files_ok and syntax_ok:
        print("\n🎉 جميع الاختبارات نجحت! النظام جاهز للاستخدام.")
        print("\nملاحظة: لاستخدام النظام الكامل، تأكد من:")
        print("1. تثبيت مكتبة groq: pip install groq")
        print("2. تعيين متغير البيئة: export GROQ_API_KEY='your_key'")
    else:
        print("\n⚠️ بعض الاختبارات فشلت. يرجى مراجعة الأخطاء أعلاه.")

if __name__ == "__main__":
    main()