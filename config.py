"""
Configuration module for the Telegram bot.
Handles environment variables and application settings.
"""

import os
import tempfile
from pathlib import Path
from api_config import api_config


class Config:
    """Configuration class for bot settings."""
    
    def __init__(self):
        # Load from centralized API config
        self.api_config = api_config
        
        # Telegram Bot Configuration
        self.TELEGRAM_BOT_TOKEN = self.api_config.telegram_bot_token
        
        # Google Gemini API Configuration
        self.GEMINI_API_KEY = self.api_config.gemini_api_key
        self.GEMINI_MODEL = self.api_config.gemini_model
        
        # Multiple API Keys support
        self.GEMINI_API_KEYS = self._load_multiple_keys()
        
        # Bot roles configuration
        self.BOT_OWNER_ID = 2018954602  # Bot owner (you)
        self.ADMIN_IDS = [2018954602]  # Bot admins (can view all users status)
        self.DEVELOPER_IDS = [2018954602]  # Developers (can use dev commands)
        
        # File handling configuration  
        self.MAX_FILE_SIZE = 50 * 1024 * 1024  # Increased to 50MB
        self.SUPPORTED_FORMATS = ['.pdf', '.doc', '.docx']
        self.TEMP_DIR = Path(tempfile.gettempdir()) / "telegram_bot"
        self.TEMP_DIR.mkdir(exist_ok=True)
        
        # Translation configuration
        self.MAX_TEXT_LENGTH = 30000  # Maximum characters per translation request
        self.TRANSLATION_TIMEOUT = self.api_config.translation_timeout
        
        # Rate limiting
        self.MAX_CONCURRENT_TRANSLATIONS = 5
        self.RATE_LIMIT_PER_USER = self.api_config.max_files_per_hour
        self.DAILY_RATE_LIMIT_PER_USER = 50  # Increased daily limit
        
        # Channel settings (disabled - no mandatory subscription)
        self.CHANNEL_USERNAME = None  # Mandatory subscription disabled
        
        # Database configuration
        self.DATABASE_URL = os.getenv("DATABASE_URL", "postgres://koi:oU1-vG4+vO4+hU4=oJ4+@asia-east1-001.proxy.kinsta.app:30318/teenage-aqua-reptile")
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    def get_temp_file_path(self, filename: str) -> Path:
        """Generate a temporary file path."""
        return self.TEMP_DIR / filename
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        return self.api_config.validate_config()
    
    def _load_multiple_keys(self) -> list:
        """Load multiple API keys from environment variables."""
        keys = []
        
        # Add primary key
        if self.GEMINI_API_KEY:
            keys.append(self.GEMINI_API_KEY)
        
        # Add additional keys (GEMINI_API_KEY_2, GEMINI_API_KEY_3, etc.)
        for i in range(2, 10):
            key = os.getenv(f"GEMINI_API_KEY_{i}", "")
            if key:
                keys.append(key)
        
        return keys
    
    def get_welcome_message(self) -> str:
        """Get the welcome message from API config."""
        return self.api_config.get_welcome_message()
