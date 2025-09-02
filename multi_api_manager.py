"""
Multi-API Key Manager
يدير عدة مفاتيح API لتجنب تجاوز حدود الطلبات
"""

import logging
import asyncio
import random
from typing import List, Optional, Tuple, Callable
import os
import json
from datetime import datetime, timedelta
import google.generativeai as genai
from groq import Groq

logger = logging.getLogger(__name__)

class MultiAPIManager:
    """مدير متعدد مفاتيح API مع تحويل تلقائي عند تجاوز الحدود"""

    def __init__(self):
        self.api_keys: List[dict] = []
        self.current_key_index = 0
        self.failed_keys = set()
        self.load_api_keys()

    def load_api_keys(self):
        """تحميل مفاتيح API من متغيرات البيئة"""
        # تحميل المفتاح الأساسي
        primary_key = os.getenv("GEMINI_API_KEY", "")
        if primary_key:
            self.api_keys.append({
                'key': primary_key,
                'name': 'Primary',
                'usage_count': 0,
                'last_used': None,
                'is_active': True
            })

        # تحميل مفاتيح إضافية (GEMINI_API_KEY_2, GEMINI_API_KEY_3, إلخ)
        for i in range(2, 10):  # يدعم حتى 9 مفاتيح
            key = os.getenv(f"GEMINI_API_KEY_{i}", "")
            if key:
                self.api_keys.append({
                    'key': key,
                    'name': f'Secondary_{i}',
                    'usage_count': 0,
                    'last_used': None,
                    'is_active': True
                })

        logger.info(f"تم تحميل {len(self.api_keys)} مفتاح API")

    def get_current_api_key(self) -> Optional[str]:
        """الحصول على مفتاح API الحالي"""
        if not self.api_keys:
            return None

        active_keys = [k for k in self.api_keys if k['is_active']]
        if not active_keys:
            # إعادة تفعيل جميع المفاتيح إذا فشلت كلها
            for key in self.api_keys:
                key['is_active'] = True
            active_keys = self.api_keys

        # اختيار مفتاح عشوائي من المفاتيح النشطة
        selected_key = random.choice(active_keys)
        selected_key['usage_count'] += 1
        selected_key['last_used'] = datetime.now()

        return selected_key['key']

    def mark_key_failed(self, api_key: str, error_message: str):
        """تمييز مفتاح API كفاشل مؤقتاً"""
        for key_info in self.api_keys:
            if key_info['key'] == api_key:
                key_info['is_active'] = False
                logger.warning(f"تم تعطيل مفتاح {key_info['name']} مؤقتاً: {error_message}")

                # إعادة تفعيل المفتاح بعد 5 دقائق
                asyncio.create_task(self._reactivate_key_after_delay(key_info, 300))
                break

    async def _reactivate_key_after_delay(self, key_info: dict, delay_seconds: int):
        """إعادة تفعيل مفتاح API بعد فترة انتظار"""
        await asyncio.sleep(delay_seconds)
        key_info['is_active'] = True
        logger.info(f"تم إعادة تفعيل مفتاح {key_info['name']}")

    def get_status(self) -> dict:
        """الحصول على حالة جميع مفاتيح API"""
        status = {
            'total_keys': len(self.api_keys),
            'active_keys': len([k for k in self.api_keys if k['is_active']]),
            'keys_info': []
        }

        for i, key_info in enumerate(self.api_keys):
            masked_key = key_info['key'][:10] + "..." + key_info['key'][-5:] if len(key_info['key']) > 15 else "***"
            status['keys_info'].append({
                'name': key_info['name'],
                'key': masked_key,
                'active': key_info['is_active'],
                'usage_count': key_info['usage_count'],
                'last_used': key_info['last_used'].strftime('%H:%M:%S') if key_info['last_used'] else 'لم يُستخدم'
            })

        return status

    def add_api_key(self, api_key: str, name: str = None) -> bool:
        """إضافة مفتاح API جديد"""
        if not name:
            name = f"Manual_{len(self.api_keys) + 1}"

        # التحقق من عدم وجود المفتاح مسبقاً
        for existing_key in self.api_keys:
            if existing_key['key'] == api_key:
                return False

        self.api_keys.append({
            'key': api_key,
            'name': name,
            'usage_count': 0,
            'last_used': None,
            'is_active': True
        })

        logger.info(f"تم إضافة مفتاح API جديد: {name}")
        return True

    def remove_api_key(self, key_name: str) -> bool:
        """حذف مفتاح API"""
        for i, key_info in enumerate(self.api_keys):
            if key_info['name'] == key_name:
                del self.api_keys[i]
                logger.info(f"تم حذف مفتاح API: {key_name}")
                return True
        return False

class MultiGeminiTranslatorManager:
    """مدير ترجمة متعدد مع إدارة مفاتيح API ودعم Groq كخدمة احتياطية"""

    def __init__(self, api_keys: List[str], model: str = "gemini-2.5-flash"):
        self.api_keys = api_keys if api_keys else []
        self.model = model
        self.current_key_index = 0
        self.semaphore = asyncio.Semaphore(8)

        # Groq configuration
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_model = "gemma2-9b-it"
        self.groq_client = None

        if self.groq_api_key:
            try:
                self.groq_client = Groq(api_key=self.groq_api_key)
                logger.info("Groq client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")

        # Add keys to parent manager
        for i, key in enumerate(self.api_keys):
            multi_api_manager.add_api_key(key, f"Config_Key_{i+1}")

    async def translate_with_groq(self, text: str) -> str:
        """ترجمة باستخدام Groq كخدمة احتياطية"""
        if not self.groq_client or not text.strip():
            return text

        try:
            messages = [
                {
                    "role": "user",
                    "content": f"Translate the following English text to Arabic. Return only the Arabic translation without any explanations:\n\n{text.strip()}"
                }
            ]

            completion = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.groq_model,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
                top_p=1,
                stream=False
            )

            if completion.choices and completion.choices[0].message.content:
                return completion.choices[0].message.content.strip()
            else:
                return text

        except Exception as e:
            logger.error(f"Groq translation failed: {e}")
            return text

    async def translate_single_line(self, text: str) -> str:
        """ترجمة سطر واحد باستخدام القاموس المحلي"""
        if not text or text.strip() == "":
            return ""
            
        try:
            # Use local translator instead of external APIs
            from local_translator import LocalTranslator
            local_translator = LocalTranslator()
            translated = await local_translator.translate_text(text)
            return translated
        except Exception as e:
            logger.error(f"Local translation failed: {e}")
            return text

    async def translate_lines_with_progress(self, lines: List[str], progress_callback: Callable = None) -> List[Tuple[str, str]]:
        """ترجمة عدة أسطر باستخدام القاموس المحلي"""
        try:
            if progress_callback:
                await progress_callback(0, 100, "بدء الترجمة باستخدام القاموس المحلي")

            # Use local translator instead of external APIs
            from local_translator import LocalTranslator
            local_translator = LocalTranslator()
            result = await local_translator.translate_lines(lines)

            if progress_callback:
                await progress_callback(100, 100, "اكتملت الترجمة باستخدام القاموس المحلي")

            return result
        except Exception as e:
            logger.error(f"Local batch translation failed: {e}")
            # Return original text as fallback
            return [(line, line) for line in lines]

    async def translate_batch_with_groq(self, lines: List[str], progress_callback: Callable = None) -> List[Tuple[str, str]]:
        """ترجمة دفعية باستخدام القاموس المحلي"""
        try:
            if progress_callback:
                await progress_callback(0, 100, "بدء الترجمة باستخدام القاموس المحلي")

            # Use local translator instead of external APIs
            from local_translator import LocalTranslator
            local_translator = LocalTranslator()
            result = await local_translator.translate_lines(lines)

            if progress_callback:
                await progress_callback(100, 100, "اكتملت الترجمة باستخدام القاموس المحلي")

            return result
        except Exception as e:
            logger.error(f"Local batch translation failed: {e}")
            # Return original text as fallback
            return [(line, line) for line in lines]

    async def translate_batch_with_progress(self, lines: List[str], progress_callback: Callable = None) -> List[Tuple[str, str]]:
        """ترجمة النص باستخدام القاموس المحلي"""
        try:
            if progress_callback:
                await progress_callback(0, 100, "بدء الترجمة باستخدام القاموس المحلي")

            # Use local translator instead of external APIs
            from local_translator import LocalTranslator
            local_translator = LocalTranslator()
            result = await local_translator.translate_lines(lines)

            if progress_callback:
                await progress_callback(100, 100, "اكتملت الترجمة باستخدام القاموس المحلي")

            return result
        except Exception as e:
            logger.error(f"Local batch translation failed: {e}")
            # Return original text as fallback
            return [(line, line) for line in lines]

    async def translate_lines_fallback(self, lines: List[str], progress_callback: Callable = None) -> List[Tuple[str, str]]:
        """طريقة احتياطية - ترجمة باستخدام القاموس المحلي"""
        logger.info("Using local dictionary translation")
        try:
            if progress_callback:
                await progress_callback(0, len(lines), "بدء الترجمة باستخدام القاموس المحلي")

            # Use local translator instead of external APIs
            from local_translator import LocalTranslator
            local_translator = LocalTranslator()
            result = await local_translator.translate_lines(lines)

            if progress_callback:
                await progress_callback(len(lines), len(lines), "اكتملت الترجمة باستخدام القاموس المحلي")

            return result
        except Exception as e:
            logger.error(f"Local fallback translation failed: {e}")
            # Return original text as fallback
            return [(line, line) for line in lines]

    def get_all_keys(self) -> List[str]:
        """الحصول على جميع مفاتيح API"""
        return [key_info['key'] for key_info in multi_api_manager.api_keys]

    async def check_key_status(self, api_key: str) -> str:
        """فحص حالة مفتاح API"""
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.model)

            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, "Hello"),
                timeout=10
            )

            if response and response.text:
                return "يعمل بشكل طبيعي"
            else:
                return "لا يستجيب"

        except Exception as e:
            return f"خطأ: {str(e)}"

    def add_key(self, api_key: str) -> bool:
        """إضافة مفتاح API جديد"""
        return multi_api_manager.add_api_key(api_key, f"Manual_{len(multi_api_manager.api_keys) + 1}")

    def remove_key(self, api_key: str) -> bool:
        """حذف مفتاح API"""
        for key_info in multi_api_manager.api_keys:
            if key_info['key'] == api_key:
                return multi_api_manager.remove_api_key(key_info['name'])
        return False

# إنشاء مثيل عام
multi_api_manager = MultiAPIManager()