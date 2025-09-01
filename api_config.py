"""
API Configuration Module
Easy configuration file for changing API keys and settings
"""

import os
from typing import Optional

class APIConfig:
    """Centralized API configuration management."""
    
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """Load API configuration from environment variables or defaults."""
        
        # Telegram Bot Configuration
        self.telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
        
        # Google Gemini AI Configuration  
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model: str = "gemini-2.5-flash"  # Default model
        
        # Bot Settings
        self.max_file_size_mb: int = 50
        self.max_files_per_hour: int = 10
        self.translation_timeout: int = 300  # seconds
        
        # Document Settings
        self.default_font_size: int = 16
        self.title_font_size: int = 20
        self.developer_credit: str = "Developed by @dextermorgenk"
        
        # PDF Styling
        self.pdf_colors = {
            'primary': '#2E86AB',      # Blue
            'secondary': '#A23B72',    # Purple  
            'accent': '#F18F01',       # Orange
            'text': '#333333',         # Dark Gray
            'light_gray': '#F5F5F5',   # Light Gray
            'credit': '#808080'        # Gray
        }
        
        # Error messages in Arabic
        self.error_messages = {
            'file_too_large': 'الملف كبير جداً. الحد الأقصى 20 ميجابايت.',
            'no_text_found': 'لم يتم العثور على نص في الملف.',
            'translation_failed': 'فشل في الترجمة. يرجى المحاولة مرة أخرى.',
            'rate_limit': 'تم تجاوز الحد المسموح. يرجى الانتظار.',
            'invalid_format': 'تنسيق الملف غير مدعوم.'
        }
    
    def validate_config(self) -> bool:
        """Validate that required configuration is present."""
        if not self.telegram_bot_token:
            print("❌ TELEGRAM_BOT_TOKEN is not set!")
            return False
            
        if not self.gemini_api_key:
            print("❌ GEMINI_API_KEY is not set!")
            return False
            
        return True
    
    def get_welcome_message(self) -> str:
        """Get the bot welcome message in Arabic."""
        return f"""
🤖 **مرحباً بك في بوت الترجمة المطور!**

أرسل لي ملف PDF أو Word وسأترجمه من الإنجليزية إلى العربية بتنسيق جميل ونظيف.

📋 **الميزات:**
• ترجمة ذكية باستخدام الذكاء الاصطناعي
• دعم ملفات PDF و Word
• تنسيق جميل للنصوص العربية
• خيارات متعددة للتصدير

⚙️ **المواصفات:**
• الحد الأقصى للملف: {self.max_file_size_mb} ميجابايت
• الحد الأقصى: {self.max_files_per_hour} ملفات في الساعة

{self.developer_credit}

🚀 أرسل ملفك الآن للبدء!
        """

# Global config instance
api_config = APIConfig()