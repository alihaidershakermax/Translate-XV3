"""
Groq Batch Translation System
نظام ترجمة مبسط باستخدام Groq API Manager للترجمة الدفعية
"""

import logging
import asyncio
import os
from typing import List, Tuple, Optional
from groq import Groq
from groq_config import GroqConfig

logger = logging.getLogger(__name__)

class GroqAPIManager:
    """مدير API لـ Groq للاستدعاء المباشر بدون streaming"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        تهيئة مدير Groq API
        
        Args:
            api_key: مفتاح API لـ Groq (اختياري، يمكن الحصول عليه من متغير البيئة)
        """
        self.api_key = api_key or GroqConfig.get_api_key()
        self.client = None
        self.model = GroqConfig.DEFAULT_MODEL
        self.temperature = GroqConfig.DEFAULT_TEMPERATURE
        self.max_tokens = GroqConfig.DEFAULT_MAX_TOKENS
        self.top_p = GroqConfig.DEFAULT_TOP_P
        
        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info("تم تهيئة عميل Groq بنجاح")
            except Exception as e:
                logger.error(f"فشل في تهيئة عميل Groq: {e}")
        else:
            logger.warning("لم يتم العثور على مفتاح GROQ_API_KEY")
    
    def set_model(self, model_name: str):
        """تغيير النموذج المستخدم"""
        if GroqConfig.validate_model(model_name):
            self.model = model_name
            # تحديث max_tokens حسب النموذج
            model_config = GroqConfig.get_model_config(model_name)
            self.max_tokens = min(self.max_tokens, model_config["max_tokens"])
            logger.info(f"تم تغيير النموذج إلى: {model_name}")
        else:
            logger.warning(f"النموذج {model_name} غير مدعوم")
    
    def set_parameters(self, temperature: float = None, max_tokens: int = None, top_p: float = None):
        """تغيير معاملات النموذج"""
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            model_config = GroqConfig.get_model_config(self.model)
            self.max_tokens = min(max_tokens, model_config["max_tokens"])
        if top_p is not None:
            self.top_p = top_p
        logger.info(f"تم تحديث المعاملات: temp={self.temperature}, max_tokens={self.max_tokens}, top_p={self.top_p}")
    
    async def translate_text_batch(self, text: str, target_language: str = "Arabic") -> str:
        """
        ترجمة النص ككتلة واحدة (بدون streaming)
        
        Args:
            text: النص المراد ترجمته
            target_language: اللغة المستهدفة (افتراضي: Arabic)
            
        Returns:
            النص المترجم
        """
        if not self.client or not text.strip():
            return text
        
        try:
            # إنشاء رسالة الترجمة باستخدام prompt محسن
            prompt = GroqConfig.get_translation_prompt(target_language)
            messages = [
                {
                    "role": "user",
                    "content": f"{prompt}\n\n{text.strip()}"
                }
            ]
            
            # استدعاء API بدون streaming
            completion = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                stream=False  # مهم: بدون streaming
            )
            
            if completion.choices and completion.choices[0].message.content:
                translated_text = completion.choices[0].message.content.strip()
                logger.info(f"تمت الترجمة بنجاح: {len(text)} حرف -> {len(translated_text)} حرف")
                return translated_text
            else:
                logger.warning("لم يتم الحصول على ترجمة من API")
                return text
                
        except Exception as e:
            logger.error(f"فشل في الترجمة باستخدام Groq: {e}")
            return text
    
    async def translate_lines_batch(self, lines: List[str], target_language: str = "Arabic") -> List[Tuple[str, str]]:
        """
        ترجمة عدة أسطر ككتلة واحدة
        
        Args:
            lines: قائمة الأسطر المراد ترجمتها
            target_language: اللغة المستهدفة
            
        Returns:
            قائمة من tuples تحتوي على (النص الأصلي, النص المترجم)
        """
        if not lines:
            return []
        
        try:
            # دمج جميع الأسطر في نص واحد
            combined_text = "\n".join(lines)
            
            # ترجمة النص ككتلة واحدة
            translated_text = await self.translate_text_batch(combined_text, target_language)
            
            # تقسيم النص المترجم إلى أسطر
            translated_lines = translated_text.split("\n")
            
            # إنشاء النتيجة
            result = []
            for i, original_line in enumerate(lines):
                translated_line = translated_lines[i] if i < len(translated_lines) else original_line
                result.append((original_line, translated_line))
            
            logger.info(f"تمت ترجمة {len(lines)} سطر بنجاح")
            return result
            
        except Exception as e:
            logger.error(f"فشل في ترجمة الأسطر: {e}")
            # إرجاع النص الأصلي في حالة الفشل
            return [(line, line) for line in lines]
    
    async def translate_paragraph(self, paragraph: str, target_language: str = "Arabic") -> str:
        """
        ترجمة فقرة كاملة ككتلة واحدة
        
        Args:
            paragraph: الفقرة المراد ترجمتها
            target_language: اللغة المستهدفة
            
        Returns:
            الفقرة المترجمة
        """
        return await self.translate_text_batch(paragraph, target_language)
    
    def is_available(self) -> bool:
        """التحقق من توفر الخدمة"""
        return self.client is not None and self.api_key is not None
    
    def get_status(self) -> dict:
        """الحصول على حالة الخدمة"""
        return {
            "available": self.is_available(),
            "model": self.model,
            "api_key_set": bool(self.api_key),
            "client_initialized": self.client is not None,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p
        }
    
    def get_available_models(self) -> dict:
        """الحصول على النماذج المتاحة"""
        return GroqConfig.AVAILABLE_MODELS.copy()
    
    def get_supported_languages(self) -> dict:
        """الحصول على اللغات المدعومة"""
        return GroqConfig.get_supported_languages()


class GroqBatchTranslator:
    """مترجم دفعي مبسط باستخدام Groq"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        تهيئة المترجم الدفعي
        
        Args:
            api_key: مفتاح API لـ Groq
        """
        self.api_manager = GroqAPIManager(api_key)
        self.target_language = "Arabic"
    
    async def translate_text(self, text: str) -> str:
        """
        ترجمة نص واحد
        
        Args:
            text: النص المراد ترجمته
            
        Returns:
            النص المترجم
        """
        return await self.api_manager.translate_text_batch(text, self.target_language)
    
    async def translate_lines(self, lines: List[str]) -> List[Tuple[str, str]]:
        """
        ترجمة قائمة من الأسطر
        
        Args:
            lines: قائمة الأسطر المراد ترجمتها
            
        Returns:
            قائمة من tuples تحتوي على (النص الأصلي, النص المترجم)
        """
        return await self.api_manager.translate_lines_batch(lines, self.target_language)
    
    async def translate_document(self, document_text: str) -> str:
        """
        ترجمة مستند كامل ككتلة واحدة
        
        Args:
            document_text: نص المستند المراد ترجمته
            
        Returns:
            المستند المترجم
        """
        return await self.api_manager.translate_text_batch(document_text, self.target_language)
    
    def set_target_language(self, language: str):
        """تغيير اللغة المستهدفة"""
        if GroqConfig.validate_language(language):
            self.target_language = language
            logger.info(f"تم تغيير اللغة المستهدفة إلى: {language}")
        else:
            logger.warning(f"اللغة {language} غير مدعومة")
    
    def get_available_models(self) -> dict:
        """الحصول على النماذج المتاحة"""
        return self.api_manager.get_available_models()
    
    def get_supported_languages(self) -> dict:
        """الحصول على اللغات المدعومة"""
        return self.api_manager.get_supported_languages()
    
    def set_model(self, model_name: str):
        """تغيير النموذج المستخدم"""
        self.api_manager.set_model(model_name)
    
    def get_status(self) -> dict:
        """الحصول على حالة المترجم"""
        status = self.api_manager.get_status()
        status["target_language"] = self.target_language
        return status


# مثال على الاستخدام
async def main():
    """مثال على استخدام المترجم الدفعي"""
    
    # إنشاء مثيل من المترجم
    translator = GroqBatchTranslator()
    
    # التحقق من حالة الخدمة
    status = translator.get_status()
    print(f"حالة الخدمة: {status}")
    
    if not status["available"]:
        print("الخدمة غير متاحة. تأكد من تعيين GROQ_API_KEY")
        return
    
    # مثال 1: ترجمة نص واحد
    text = "Hello, how are you today? I hope you are doing well."
    translated = await translator.translate_text(text)
    print(f"النص الأصلي: {text}")
    print(f"النص المترجم: {translated}")
    print("-" * 50)
    
    # مثال 2: ترجمة عدة أسطر
    lines = [
        "Good morning!",
        "How are you?",
        "Have a great day!"
    ]
    translated_lines = await translator.translate_lines(lines)
    print("ترجمة الأسطر:")
    for original, translated in translated_lines:
        print(f"الأصلي: {original}")
        print(f"المترجم: {translated}")
        print("-" * 30)
    
    # مثال 3: ترجمة فقرة كاملة
    paragraph = """
    This is a sample paragraph that contains multiple sentences.
    It demonstrates how the batch translation works.
    The entire paragraph is sent as one block to the API.
    """
    translated_paragraph = await translator.translate_document(paragraph)
    print("ترجمة الفقرة:")
    print(f"الأصلي:\n{paragraph}")
    print(f"المترجم:\n{translated_paragraph}")


if __name__ == "__main__":
    # تشغيل المثال
    asyncio.run(main())