
"""
Local Translation Fallback System
نظام ترجمة محلي احتياطي عند فشل خدمات API الخارجية
"""

import logging
import asyncio
from typing import List, Tuple, Dict
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class LocalTranslator:
    """مترجم محلي احتياطي باستخدام قاموس مدمج"""
    
    def __init__(self):
        self.dictionary = {}
        self.phrase_dictionary = {}
        self.load_local_dictionary()
        
    def load_local_dictionary(self):
        """تحميل القاموس المحلي من ملف JSON"""
        try:
            # قاموس أساسي مدمج
            self.dictionary = {
                "hello": "مرحباً",
                "world": "عالم",
                "the": "الـ",
                "and": "و",
                "or": "أو",
                "in": "في",
                "on": "على",
                "at": "عند",
                "to": "إلى",
                "from": "من",
                "with": "مع",
                "by": "بواسطة",
                "for": "لـ",
                "of": "من",
                "is": "هو/هي",
                "are": "هم/هن",
                "was": "كان",
                "were": "كانوا",
                "be": "يكون",
                "been": "كان",
                "have": "لديه",
                "has": "لديه",
                "had": "كان لديه",
                "do": "يفعل",
                "does": "يفعل",
                "did": "فعل",
                "will": "سوف",
                "would": "سوف",
                "could": "يمكن",
                "should": "يجب",
                "may": "قد",
                "might": "ربما",
                "can": "يمكن",
                "must": "يجب",
                "not": "لا",
                "no": "لا",
                "yes": "نعم",
                "this": "هذا/هذه",
                "that": "ذلك/تلك",
                "these": "هؤلاء",
                "those": "أولئك",
                "what": "ماذا",
                "when": "متى",
                "where": "أين",
                "why": "لماذا",
                "how": "كيف",
                "who": "من",
                "which": "أي",
                "all": "جميع",
                "some": "بعض",
                "any": "أي",
                "many": "كثير",
                "much": "كثير",
                "few": "قليل",
                "little": "قليل",
                "more": "أكثر",
                "most": "معظم",
                "less": "أقل",
                "least": "الأقل",
                "good": "جيد",
                "better": "أفضل",
                "best": "الأفضل",
                "bad": "سيء",
                "worse": "أسوأ",
                "worst": "الأسوأ",
                "big": "كبير",
                "small": "صغير",
                "large": "كبير",
                "new": "جديد",
                "old": "قديم",
                "young": "شاب",
                "high": "عالي",
                "low": "منخفض",
                "long": "طويل",
                "short": "قصير",
                "wide": "واسع",
                "narrow": "ضيق",
                "thick": "سميك",
                "thin": "رفيع",
                "heavy": "ثقيل",
                "light": "خفيف",
                "hard": "صعب",
                "easy": "سهل",
                "difficult": "صعب",
                "simple": "بسيط",
                "complex": "معقد",
                "important": "مهم",
                "necessary": "ضروري",
                "possible": "ممكن",
                "impossible": "مستحيل",
                "true": "صحيح",
                "false": "خاطئ",
                "right": "صحيح",
                "wrong": "خاطئ",
                "correct": "صحيح",
                "incorrect": "غير صحيح",
                "same": "نفس",
                "different": "مختلف",
                "similar": "مشابه",
                "other": "آخر",
                "another": "آخر",
                "first": "أول",
                "last": "آخر",
                "next": "التالي",
                "previous": "السابق",
                "before": "قبل",
                "after": "بعد",
                "now": "الآن",
                "then": "ثم",
                "here": "هنا",
                "there": "هناك",
                "everywhere": "في كل مكان",
                "nowhere": "لا مكان",
                "somewhere": "مكان ما",
                "today": "اليوم",
                "tomorrow": "غداً",
                "yesterday": "أمس",
                "week": "أسبوع",
                "month": "شهر",
                "year": "سنة",
                "day": "يوم",
                "night": "ليلة",
                "morning": "صباح",
                "afternoon": "بعد الظهر",
                "evening": "مساء",
                "time": "وقت",
                "hour": "ساعة",
                "minute": "دقيقة",
                "second": "ثانية",
                "man": "رجل",
                "woman": "امرأة",
                "people": "الناس",
                "person": "شخص",
                "child": "طفل",
                "children": "أطفال",
                "family": "عائلة",
                "friend": "صديق",
                "work": "عمل",
                "job": "وظيفة",
                "business": "عمل تجاري",
                "company": "شركة",
                "money": "مال",
                "price": "سعر",
                "cost": "تكلفة",
                "buy": "يشتري",
                "sell": "يبيع",
                "pay": "يدفع",
                "give": "يعطي",
                "take": "يأخذ",
                "get": "يحصل على",
                "put": "يضع",
                "go": "يذهب",
                "come": "يأتي",
                "see": "يرى",
                "look": "ينظر",
                "watch": "يشاهد",
                "hear": "يسمع",
                "listen": "يستمع",
                "speak": "يتحدث",
                "talk": "يتكلم",
                "say": "يقول",
                "tell": "يخبر",
                "ask": "يسأل",
                "answer": "يجيب",
                "read": "يقرأ",
                "write": "يكتب",
                "learn": "يتعلم",
                "teach": "يعلم",
                "study": "يدرس",
                "know": "يعرف",
                "understand": "يفهم",
                "think": "يفكر",
                "believe": "يؤمن",
                "feel": "يشعر",
                "want": "يريد",
                "need": "يحتاج",
                "like": "يحب",
                "love": "يحب",
                "hate": "يكره",
                "hope": "يأمل",
                "wish": "يتمنى",
                "try": "يحاول",
                "help": "يساعد",
                "start": "يبدأ",
                "stop": "يتوقف",
                "end": "ينتهي",
                "finish": "ينهي",
                "continue": "يستمر",
                "change": "يغير",
                "turn": "يدير",
                "move": "يتحرك",
                "bring": "يجلب",
                "carry": "يحمل",
                "send": "يرسل",
                "receive": "يستقبل",
                "open": "يفتح",
                "close": "يغلق",
                "cut": "يقطع",
                "break": "يكسر",
                "fix": "يصلح",
                "build": "يبني",
                "make": "يصنع",
                "create": "يخلق",
                "destroy": "يدمر",
                "kill": "يقتل",
                "die": "يموت",
                "live": "يعيش",
                "eat": "يأكل",
                "drink": "يشرب",
                "sleep": "ينام",
                "wake": "يستيقظ",
                "walk": "يمشي",
                "run": "يجري",
                "drive": "يقود",
                "fly": "يطير",
                "swim": "يسبح",
                "play": "يلعب",
                "sing": "يغني",
                "dance": "يرقص",
                "laugh": "يضحك",
                "cry": "يبكي",
                "smile": "يبتسم",
                "sit": "يجلس",
                "stand": "يقف",
                "lie": "يكذب",
                "wait": "ينتظر",
                "stay": "يبقى",
                "leave": "يغادر",
                "arrive": "يصل",
                "enter": "يدخل",
                "exit": "يخرج",
                "return": "يعود",
                "visit": "يزور",
                "meet": "يقابل",
                "join": "ينضم",
                "follow": "يتبع",
                "lead": "يقود",
                "win": "يفوز",
                "lose": "يخسر",
                "find": "يجد",
                "lose": "يفقد",
                "keep": "يحتفظ",
                "hold": "يمسك",
                "catch": "يمسك",
                "throw": "يرمي",
                "push": "يدفع",
                "pull": "يسحب",
                "lift": "يرفع",
                "drop": "يسقط",
                "wear": "يلبس",
                "remove": "يزيل",
                "wash": "يغسل",
                "clean": "ينظف",
                "cook": "يطبخ",
                "serve": "يقدم",
                "order": "يطلب",
                "choose": "يختار",
                "decide": "يقرر",
                "agree": "يوافق",
                "disagree": "يختلف",
                "accept": "يقبل",
                "refuse": "يرفض",
                "allow": "يسمح",
                "forbid": "يمنع",
                "permit": "يسمح",
                "deny": "ينكر",
                "admit": "يعترف",
                "confirm": "يؤكد",
                "cancel": "يلغي",
                "book": "يحجز",
                "reserve": "يحجز",
                "plan": "يخطط",
                "prepare": "يحضر",
                "organize": "ينظم",
                "arrange": "يرتب",
                "manage": "يدير",
                "control": "يتحكم",
                "operate": "يشغل",
                "use": "يستخدم",
                "apply": "يطبق",
                "employ": "يوظف",
                "hire": "يوظف",
                "fire": "يطرد",
                "quit": "يستقيل",
                "retire": "يتقاعد",
                "graduate": "يتخرج",
                "marry": "يتزوج",
                "divorce": "يطلق"
            }
            
            # عبارات شائعة
            self.phrase_dictionary = {
                "how are you": "كيف حالك",
                "thank you": "شكراً لك",
                "you're welcome": "عفواً",
                "excuse me": "عذراً",
                "i'm sorry": "أنا آسف",
                "good morning": "صباح الخير",
                "good evening": "مساء الخير",
                "good night": "تصبح على خير",
                "see you later": "أراك لاحقاً",
                "nice to meet you": "سعيد بلقائك",
                "what's your name": "ما اسمك",
                "my name is": "اسمي",
                "where are you from": "من أين أنت",
                "i am from": "أنا من",
                "how old are you": "كم عمرك",
                "i am": "أنا",
                "you are": "أنت",
                "he is": "هو",
                "she is": "هي",
                "we are": "نحن",
                "they are": "هم",
                "what time is it": "كم الساعة",
                "it is": "إنه",
                "where is": "أين",
                "here is": "هنا",
                "there is": "هناك",
                "how much": "كم",
                "how many": "كم عدد",
                "i want": "أريد",
                "i need": "أحتاج",
                "i like": "أحب",
                "i don't like": "لا أحب",
                "i love": "أحب",
                "i hate": "أكره",
                "i think": "أعتقد",
                "i believe": "أؤمن",
                "i know": "أعرف",
                "i don't know": "لا أعرف",
                "i understand": "أفهم",
                "i don't understand": "لا أفهم",
                "please": "من فضلك",
                "can you": "هل يمكنك",
                "could you": "هل يمكنك",
                "would you": "هل تريد",
                "will you": "هل ستقوم",
                "let's go": "هيا بنا",
                "let me": "دعني",
                "wait for me": "انتظرني",
                "come here": "تعال هنا",
                "go there": "اذهب هناك",
                "sit down": "اجلس",
                "stand up": "قف",
                "turn on": "شغل",
                "turn off": "أطفئ",
                "open the door": "افتح الباب",
                "close the window": "أغلق النافذة",
                "turn left": "انعطف يساراً",
                "turn right": "انعطف يميناً",
                "go straight": "امش مستقيماً",
                "stop here": "توقف هنا",
                "be careful": "كن حذراً",
                "take care": "اعتن بنفسك",
                "good luck": "حظاً سعيداً",
                "congratulations": "مبروك",
                "happy birthday": "عيد ميلاد سعيد",
                "merry christmas": "عيد ميلاد مجيد",
                "happy new year": "سنة جديدة سعيدة"
            }
            
            # محاولة تحميل قاموس إضافي من ملف
            dictionary_file = Path("local_dictionary.json")
            if dictionary_file.exists():
                with open(dictionary_file, 'r', encoding='utf-8') as f:
                    additional_dict = json.load(f)
                    self.dictionary.update(additional_dict.get('words', {}))
                    self.phrase_dictionary.update(additional_dict.get('phrases', {}))
                    
            logger.info(f"تم تحميل {len(self.dictionary)} كلمة و {len(self.phrase_dictionary)} عبارة في القاموس المحلي")
            
        except Exception as e:
            logger.warning(f"خطأ في تحميل القاموس المحلي: {e}")
    
    async def translate_text(self, text: str) -> str:
        """ترجمة النص باستخدام القاموس المحلي"""
        if not text or not text.strip():
            return text
            
        try:
            original_text = text.strip()
            lower_text = original_text.lower()
            
            # البحث في عبارات كاملة أولاً
            for phrase, translation in self.phrase_dictionary.items():
                if phrase in lower_text:
                    lower_text = lower_text.replace(phrase, translation)
            
            # ترجمة كلمة بكلمة
            words = lower_text.split()
            translated_words = []
            
            for word in words:
                # إزالة علامات الترقيم
                clean_word = word.strip('.,!?;:"()[]{}').lower()
                
                if clean_word in self.dictionary:
                    # الاحتفاظ بعلامات الترقيم
                    punctuation = word[len(clean_word):]
                    translated_words.append(self.dictionary[clean_word] + punctuation)
                else:
                    # إذا لم توجد ترجمة، احتفظ بالكلمة الأصلية
                    translated_words.append(word)
            
            return " ".join(translated_words)
            
        except Exception as e:
            logger.error(f"خطأ في الترجمة المحلية: {e}")
            return text
    
    async def translate_lines(self, lines: List[str]) -> List[Tuple[str, str]]:
        """ترجمة عدة أسطر باستخدام القاموس المحلي"""
        translated_pairs = []
        
        for line in lines:
            if line.strip():
                translated = await self.translate_text(line)
                translated_pairs.append((line, translated))
            else:
                translated_pairs.append((line, ""))
        
        return translated_pairs
    
    def add_translation(self, english: str, arabic: str, is_phrase: bool = False):
        """إضافة ترجمة جديدة للقاموس"""
        if is_phrase:
            self.phrase_dictionary[english.lower()] = arabic
        else:
            self.dictionary[english.lower()] = arabic
    
    def save_dictionary(self):
        """حفظ القاموس في ملف"""
        try:
            dictionary_data = {
                'words': self.dictionary,
                'phrases': self.phrase_dictionary
            }
            
            with open("local_dictionary.json", 'w', encoding='utf-8') as f:
                json.dump(dictionary_data, f, ensure_ascii=False, indent=2)
                
            logger.info("تم حفظ القاموس المحلي")
            
        except Exception as e:
            logger.error(f"خطأ في حفظ القاموس: {e}")

# إنشاء مثيل عام
local_translator = LocalTranslator()
