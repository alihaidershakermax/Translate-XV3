
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
        """ترجمة سطر واحد - محسّن للأداء مع دعم Groq"""
        if not text or text.strip() == "":
            return ""
        
        # Skip very short or non-meaningful text
        clean_text = text.strip()
        if len(clean_text) < 2 or clean_text.isdigit():
            return clean_text
            
        async with self.semaphore:
            max_retries = 2  # Reduced retries for single lines
            
            # Try Gemini first
            for attempt in range(max_retries):
                try:
                    api_key = multi_api_manager.get_current_api_key()
                    if not api_key:
                        # If no Gemini keys available, try Groq
                        logger.info("No Gemini keys available, trying Groq")
                        return await self.translate_with_groq(clean_text)
                    
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(self.model)
                    
                    # Shorter, more efficient prompt
                    prompt = f"Translate to Arabic: {clean_text}"
                    
                    response = await asyncio.wait_for(
                        asyncio.to_thread(model.generate_content, prompt),
                        timeout=20  # Reduced timeout for single lines
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
                            # Try Groq as fallback
                            logger.info("All Gemini keys exhausted, trying Groq")
                            return await self.translate_with_groq(clean_text)
                    else:
                        logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            # Try Groq before returning original
                            groq_result = await self.translate_with_groq(clean_text)
                            return groq_result if groq_result != clean_text else clean_text
                    
                    await asyncio.sleep(0.5)  # Shorter delay
            
            return clean_text  # Return original if all attempts fail
    
    async def translate_lines_with_progress(self, lines: List[str], progress_callback: Callable = None) -> List[Tuple[str, str]]:
        """ترجمة عدة أسطر مع تحديث التقدم - إصدار محسّن للدفعات"""
        # Use batch translation for better API efficiency
        return await self.translate_batch_with_progress(lines, progress_callback)
    
    async def translate_batch_with_groq(self, lines: List[str], progress_callback: Callable = None) -> List[Tuple[str, str]]:
        """ترجمة دفعية باستخدام Groq"""
        if not self.groq_client or not lines:
            return [(line, line) for line in lines]
        
        try:
            if progress_callback:
                await progress_callback(0, 100, "ترجمة باستخدام Groq")
            
            # Prepare the batch text
            batch_text = ""
            for i, line in enumerate(lines):
                if line.strip():
                    batch_text += f"{i+1}. {line.strip()}\n"
            
            messages = [
                {
                    "role": "user",
                    "content": f"""Translate the following numbered English lines to Arabic. 
Keep the exact same numbering format and return only the Arabic translations with their numbers:

{batch_text}

Important: Keep the same line numbers (1., 2., 3., etc.) and translate only the text content."""
                }
            ]
            
            if progress_callback:
                await progress_callback(50, 100, "إرسال للـ Groq")
            
            completion = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.groq_model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
                top_p=1,
                stream=False
            )
            
            if completion.choices and completion.choices[0].message.content:
                translated_text = completion.choices[0].message.content.strip()
                translated_pairs = self._parse_batch_translation(lines, translated_text)
                
                if progress_callback:
                    await progress_callback(100, 100, "اكتملت الترجمة باستخدام Groq")
                
                return translated_pairs
            else:
                return [(line, line) for line in lines]
                
        except Exception as e:
            logger.error(f"Groq batch translation failed: {e}")
            return [(line, line) for line in lines]

    async def translate_batch_with_progress(self, lines: List[str], progress_callback: Callable = None) -> List[Tuple[str, str]]:
        """ترجمة النص كدفعة واحدة لتقليل استهلاك API مع دعم Groq"""
        if not lines:
            return []
        
        try:
            if progress_callback:
                await progress_callback(0, 100, "تحضير النص للترجمة")
            
            # Prepare the batch text with numbering
            batch_text = ""
            for i, line in enumerate(lines):
                if line.strip():  # Skip empty lines
                    batch_text += f"{i+1}. {line.strip()}\n"
            
            if progress_callback:
                await progress_callback(20, 100, "إرسال النص للذكاء الاصطناعي")
            
            # Try Gemini first
            max_retries = 3
            translated_text = None
            
            for attempt in range(max_retries):
                try:
                    api_key = multi_api_manager.get_current_api_key()
                    if not api_key:
                        # No Gemini keys available, try Groq
                        logger.info("No Gemini keys available, trying Groq for batch translation")
                        return await self.translate_batch_with_groq(lines, progress_callback)
                    
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(self.model)
                    
                    prompt = f"""Translate the following numbered English lines to Arabic. 
Keep the exact same numbering format and return only the Arabic translations with their numbers:

{batch_text}

Important: Keep the same line numbers (1., 2., 3., etc.) and translate only the text content."""
                    
                    if progress_callback:
                        await progress_callback(40 + (attempt * 20), 100, f"محاولة ترجمة رقم {attempt + 1}")
                    
                    response = await asyncio.wait_for(
                        asyncio.to_thread(model.generate_content, prompt),
                        timeout=60  # Increased timeout for batch processing
                    )
                    
                    if response and response.text:
                        translated_text = response.text.strip()
                        break
                    else:
                        raise Exception("No response from API")
                        
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                        multi_api_manager.mark_key_failed(api_key, "Quota exceeded")
                        if attempt == max_retries - 1:
                            # Try Groq as fallback
                            logger.info("All Gemini keys exhausted, trying Groq for batch translation")
                            return await self.translate_batch_with_groq(lines, progress_callback)
                    else:
                        logger.warning(f"Batch translation attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            # Try Groq before falling back to line-by-line
                            groq_result = await self.translate_batch_with_groq(lines, progress_callback)
                            if groq_result:
                                return groq_result
                            # Final fallback to line-by-line translation
                            return await self.translate_lines_fallback(lines, progress_callback)
                    
                    await asyncio.sleep(1)
            
            if progress_callback:
                await progress_callback(80, 100, "معالجة النص المترجم")
            
            # Parse the translated response
            translated_pairs = self._parse_batch_translation(lines, translated_text)
            
            if progress_callback:
                await progress_callback(100, 100, "اكتملت الترجمة")
            
            return translated_pairs
            
        except Exception as e:
            logger.error(f"Batch translation failed: {e}")
            # Try Groq before final fallback
            groq_result = await self.translate_batch_with_groq(lines, progress_callback)
            if groq_result:
                return groq_result
            # Final fallback to line-by-line translation
            return await self.translate_lines_fallback(lines, progress_callback)
    
    def _parse_batch_translation(self, original_lines: List[str], translated_text: str) -> List[Tuple[str, str]]:
        """تحليل النص المترجم وإقرانه بالنص الأصلي"""
        translated_pairs = []
        translated_lines = translated_text.split('\n')
        
        # Create a mapping from line numbers to translations
        translation_map = {}
        for line in translated_lines:
            line = line.strip()
            if line and '. ' in line:
                try:
                    # Extract number and translation
                    parts = line.split('. ', 1)
                    if len(parts) == 2:
                        line_num = int(parts[0])
                        translation = parts[1].strip()
                        translation_map[line_num - 1] = translation  # Convert to 0-based index
                except (ValueError, IndexError):
                    continue
        
        # Match original lines with translations
        for i, original_line in enumerate(original_lines):
            if original_line.strip():  # Non-empty line
                if i in translation_map:
                    translated_pairs.append((original_line, translation_map[i]))
                else:
                    # If translation not found, keep original
                    translated_pairs.append((original_line, original_line))
            else:
                # Empty line
                translated_pairs.append((original_line, ""))
        
        return translated_pairs
    
    async def translate_lines_fallback(self, lines: List[str], progress_callback: Callable = None) -> List[Tuple[str, str]]:
        """طريقة احتياطية - ترجمة سطر بسطر (النظام القديم)"""
        logger.info("Using fallback line-by-line translation")
        translated_pairs = []
        
        for i, line in enumerate(lines):
            if progress_callback:
                await progress_callback(i, len(lines), f"ترجمة السطر {i+1} (نظام احتياطي)")
            
            translated = await self.translate_single_line(line)
            translated_pairs.append((line, translated))
            
            # Small delay to avoid overwhelming the API
            if i % 3 == 0 and i > 0:
                await asyncio.sleep(0.3)
        
        if progress_callback:
            await progress_callback(len(lines), len(lines), "اكتملت الترجمة (نظام احتياطي)")
        
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
