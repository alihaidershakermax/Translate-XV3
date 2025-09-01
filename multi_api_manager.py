
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
    """مدير ترجمة متعدد مع إدارة مفاتيح API"""
    
    def __init__(self, api_keys: List[str], model: str = "gemini-2.5-flash"):
        self.api_keys = api_keys if api_keys else []
        self.model = model
        self.current_key_index = 0
        self.semaphore = asyncio.Semaphore(8)
        
        # Add keys to parent manager
        for i, key in enumerate(self.api_keys):
            multi_api_manager.add_api_key(key, f"Config_Key_{i+1}")
    
    async def translate_single_line(self, text: str) -> str:
        """ترجمة سطر واحد"""
        if not text or text.strip() == "":
            return ""
            
        async with self.semaphore:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    api_key = multi_api_manager.get_current_api_key()
                    if not api_key:
                        raise Exception("لا توجد مفاتيح API متاحة")
                    
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(self.model)
                    
                    prompt = f"""Translate the following English text to Arabic. Only return the Arabic translation, nothing else:

{text}"""
                    
                    response = await asyncio.wait_for(
                        asyncio.to_thread(model.generate_content, prompt),
                        timeout=30
                    )
                    
                    if response and response.text:
                        return response.text.strip()
                    else:
                        raise Exception("No response from API")
                        
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                        multi_api_manager.mark_key_failed(api_key, "Quota exceeded")
                        if attempt == max_retries - 1:
                            raise Exception("تم تجاوز حصة الترجمة لجميع المفاتيح")
                    else:
                        logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            raise e
                    
                    await asyncio.sleep(1)
            
            return text  # Return original if all attempts fail
    
    async def translate_lines_with_progress(self, lines: List[str], progress_callback: Callable = None) -> List[Tuple[str, str]]:
        """ترجمة عدة أسطر مع تحديث التقدم"""
        translated_pairs = []
        
        for i, line in enumerate(lines):
            if progress_callback:
                await progress_callback(i, len(lines), f"ترجمة السطر {i+1}")
            
            translated = await self.translate_single_line(line)
            translated_pairs.append((line, translated))
            
            # Small delay to avoid overwhelming the API
            if i % 5 == 0 and i > 0:
                await asyncio.sleep(0.2)
        
        if progress_callback:
            await progress_callback(len(lines), len(lines), "اكتملت الترجمة")
        
        return translated_pairs
    
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
