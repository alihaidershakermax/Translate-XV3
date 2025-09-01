
"""
UI Configuration Module
Controls font sizes, text styling, and display settings for the bot
"""

class UIConfig:
    """Configuration for UI elements and text styling."""
    
    def __init__(self):
        # Font sizes (in points)
        self.FONT_SIZES = {
            'small': 12,
            'medium': 16,
            'large': 20,
            'extra_large': 24,
            'header': 18
        }
        
        # Current font size setting (can be changed)
        self.current_font_size = self.FONT_SIZES['medium']
        self.current_arabic_font_size = self.FONT_SIZES['large']
        
        # PDF styling
        self.PDF_STYLES = {
            'title_size': 20,
            'header_size': 14,
            'english_size': 14,
            'arabic_size': 18,
            'spacing': 10
        }
        
        # Word document styling  
        self.WORD_STYLES = {
            'title_size': 18,
            'english_size': 14,
            'arabic_size': 18,
            'spacing': 8
        }
        
        # Text to remove from translations
        self.UNWANTED_TEXTS = [
            "ةغللا ةيئانث ةمجرت",
            "ترجمة ثنائية اللغة",
            "Translation Document",
            "Bilingual Translation"
        ]
        
        # Developer channel settings
        self.DEVELOPER_CHANNEL = "@dextermorgenk"  # Replace with actual channel username
        self.CHANNEL_ID = -1001234567890  # Replace with actual channel ID
        
        # Rate limiting
        self.DAILY_FILE_LIMIT = 3  # 3 files per day
        
    def get_font_size(self, size_name: str = 'medium') -> int:
        """Get font size by name."""
        return self.FONT_SIZES.get(size_name, self.FONT_SIZES['medium'])
    
    def set_font_size(self, size_name: str):
        """Set current font size."""
        if size_name in self.FONT_SIZES:
            self.current_font_size = self.FONT_SIZES[size_name]
    
    def clean_text(self, text: str) -> str:
        """Remove unwanted text from translations."""
        cleaned_text = text
        for unwanted in self.UNWANTED_TEXTS:
            cleaned_text = cleaned_text.replace(unwanted, "")
        return cleaned_text.strip()
    
    def get_welcome_message(self) -> str:
        """Get welcome message with subscription requirement."""
        return f"""
🎉 أهلاً بك في بوت الترجمة المطور!
تطوير: {self.DEVELOPER_CHANNEL}

📢 **للاستفادة من البوت:**
1. اشترك في قناة المطور: {self.DEVELOPER_CHANNEL}
2. أرسل الملف الذي تريد ترجمته

⚠️ **مهم:** يجب الاشتراك في القناة لاستخدام البوت

📊 **حدودك اليومية:**
• {self.DAILY_FILE_LIMIT} ملفات كحد أقصى يومياً
• حجم الملف: حتى 50 ميجابايت

🚀 ابدأ بالاشتراك ثم أرسل ملفك!
        """

# Global UI config instance
ui_config = UIConfig()
"""
UI Configuration module for font size settings.
"""

class UIConfig:
    """Configuration class for UI settings."""
    
    def __init__(self):
        # Font sizes for documents
        self.current_arabic_font_size = 16
        self.current_english_font_size = 14
        
        # PDF specific styles
        self.PDF_STYLES = {
            'arabic_size': 18,
            'english_size': 14,
            'spacing': 12
        }
    
    def set_font_size(self, size: int):
        """Set the Arabic font size for documents."""
        if 10 <= size <= 24:
            self.current_arabic_font_size = size
            self.PDF_STYLES['arabic_size'] = size + 2  # PDF slightly larger
            return True
        return False
    
    def get_font_size(self):
        """Get current Arabic font size."""
        return self.current_arabic_font_size

# Global UI configuration instance
ui_config = UIConfig()
