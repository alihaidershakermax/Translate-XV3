"""
إعدادات تكوين Groq API
"""

import os
from typing import Dict, List

class GroqConfig:
    """إعدادات تكوين Groq API"""
    
    # النماذج المتاحة
    AVAILABLE_MODELS = {
        "gemma2-9b-it": {
            "name": "Gemma 2 9B Instruct",
            "max_tokens": 8192,
            "description": "نموذج سريع ومتقدم للترجمة"
        },
        "llama3-8b-8192": {
            "name": "Llama 3 8B",
            "max_tokens": 8192,
            "description": "نموذج قوي للترجمة العامة"
        },
        "mixtral-8x7b-32768": {
            "name": "Mixtral 8x7B",
            "max_tokens": 32768,
            "description": "نموذج متقدم للترجمة المعقدة"
        },
        "llama3-70b-8192": {
            "name": "Llama 3 70B",
            "max_tokens": 8192,
            "description": "نموذج قوي جداً للترجمة الدقيقة"
        }
    }
    
    # الإعدادات الافتراضية
    DEFAULT_MODEL = "gemma2-9b-it"
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_MAX_TOKENS = 2048
    DEFAULT_TOP_P = 1.0
    
    # اللغات المدعومة
    SUPPORTED_LANGUAGES = {
        "Arabic": "العربية",
        "English": "الإنجليزية",
        "French": "الفرنسية",
        "Spanish": "الإسبانية",
        "German": "الألمانية",
        "Italian": "الإيطالية",
        "Portuguese": "البرتغالية",
        "Russian": "الروسية",
        "Chinese": "الصينية",
        "Japanese": "اليابانية",
        "Korean": "الكورية"
    }
    
    @classmethod
    def get_api_key(cls) -> str:
        """الحصول على مفتاح API من متغيرات البيئة"""
        return os.getenv("GROQ_API_KEY", "")
    
    @classmethod
    def get_model_config(cls, model_name: str) -> Dict:
        """الحصول على إعدادات نموذج معين"""
        return cls.AVAILABLE_MODELS.get(model_name, cls.AVAILABLE_MODELS[cls.DEFAULT_MODEL])
    
    @classmethod
    def get_available_models(cls) -> List[str]:
        """الحصول على قائمة النماذج المتاحة"""
        return list(cls.AVAILABLE_MODELS.keys())
    
    @classmethod
    def get_supported_languages(cls) -> Dict[str, str]:
        """الحصول على اللغات المدعومة"""
        return cls.SUPPORTED_LANGUAGES.copy()
    
    @classmethod
    def validate_model(cls, model_name: str) -> bool:
        """التحقق من صحة اسم النموذج"""
        return model_name in cls.AVAILABLE_MODELS
    
    @classmethod
    def validate_language(cls, language: str) -> bool:
        """التحقق من صحة اللغة"""
        return language in cls.SUPPORTED_LANGUAGES
    
    @classmethod
    def get_translation_prompt(cls, target_language: str) -> str:
        """الحصول على prompt الترجمة للغة المستهدفة"""
        language_name = cls.SUPPORTED_LANGUAGES.get(target_language, target_language)
        return f"Translate the following English text to {target_language} ({language_name}). Return only the {target_language} translation without any explanations or additional text:"