"""
Utility functions for the Telegram bot.
Includes file cleanup, rate limiting, and other helper functions.
"""

import logging
import asyncio
import os
import json
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with user tracking capabilities."""
    
    def __init__(self, max_per_hour: int):
        self.max_per_hour = max_per_hour
        self.user_requests: Dict[int, List[datetime]] = {}
    
    def can_process(self, user_id: int) -> bool:
        """Check if user can process a file."""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # Clean old requests
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id] 
                if req_time > one_hour_ago
            ]
        
        # Check limit
        user_count = len(self.user_requests.get(user_id, []))
        return user_count < self.max_per_hour
    
    def record_processing(self, user_id: int):
        """Record a file processing for a user."""
        now = datetime.now()
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        self.user_requests[user_id].append(now)
    
    def get_user_count(self, user_id: int) -> int:
        """Get current hourly count for a user."""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        if user_id not in self.user_requests:
            return 0
        
        # Clean old requests and count
        valid_requests = [
            req_time for req_time in self.user_requests[user_id] 
            if req_time > one_hour_ago
        ]
        self.user_requests[user_id] = valid_requests
        return len(valid_requests)
    
    def get_next_reset_time(self, user_id: int) -> datetime:
        """Get the time when the user's hourly limit resets."""
        if user_id not in self.user_requests or not self.user_requests[user_id]:
            return None
        
        # Find the oldest request in the current hour
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        valid_requests = [
            req_time for req_time in self.user_requests[user_id] 
            if req_time > one_hour_ago
        ]
        
        if not valid_requests:
            return None
        
        oldest_request = min(valid_requests)
        return oldest_request + timedelta(hours=1)


class DailyRateLimiter:
    """Daily rate limiter with user tracking capabilities."""
    
    def __init__(self, max_per_day: int):
        self.max_per_day = max_per_day
        self.user_requests: Dict[int, List[datetime]] = {}
        self.data_file = Path("daily_usage.json")
        self._load_data()
    
    def _load_data(self):
        """Load daily usage data from file."""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert timestamps back to datetime objects
                    for user_id, timestamps in data.items():
                        self.user_requests[int(user_id)] = [
                            datetime.fromisoformat(ts) for ts in timestamps
                        ]
        except Exception as e:
            logger.warning(f"Failed to load daily usage data: {e}")
    
    def _save_data(self):
        """Save daily usage data to file."""
        try:
            # Convert datetime objects to ISO format strings
            data = {}
            for user_id, timestamps in self.user_requests.items():
                data[str(user_id)] = [ts.isoformat() for ts in timestamps]
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save daily usage data: {e}")
    
    def can_process(self, user_id: int) -> bool:
        """Check if user can process a file today."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Clean old requests (older than today)
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id] 
                if req_time >= today_start
            ]
        
        # Check limit
        user_count = len(self.user_requests.get(user_id, []))
        return user_count < self.max_per_day
    
    def record_processing(self, user_id: int):
        """Record a file processing for a user."""
        now = datetime.now()
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        self.user_requests[user_id].append(now)
        self._save_data()
    
    def get_user_count(self, user_id: int) -> int:
        """Get current daily count for a user."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if user_id not in self.user_requests:
            return 0
        
        # Clean old requests and count
        valid_requests = [
            req_time for req_time in self.user_requests[user_id] 
            if req_time >= today_start
        ]
        self.user_requests[user_id] = valid_requests
        return len(valid_requests)
    
    def get_next_reset_time(self, user_id: int) -> datetime:
        """Get the time when the user's daily limit resets (next midnight)."""
        now = datetime.now()
        tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return tomorrow_start


class FileCleanupManager:
    """Manages cleanup of temporary files."""

    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir

    async def cleanup_files(self, file_paths: list):
        """Clean up a list of temporary files."""
        for file_path in file_paths:
            try:
                if isinstance(file_path, (str, Path)):
                    path_obj = Path(file_path)
                    if path_obj.exists():
                        path_obj.unlink()
                        logger.info(f"Cleaned up file: {path_obj}")
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file_path}: {e}")

    async def cleanup_old_files(self, hours_old: int = 24):
        """Clean up files older than specified hours."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_old)

            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        logger.info(f"Cleaned up old file: {file_path}")

        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")


class DailyRateLimiter:
    """Manages daily rate limiting for users."""

    def __init__(self, max_files_per_day: int = 3):
        self.max_files_per_day = max_files_per_day
        self.data_file = Path("daily_usage.json")
        self.user_requests: Dict[int, Dict] = self._load_data()

    def _load_data(self) -> Dict[int, Dict]:
        """Load user data from file."""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Convert string keys back to int
                    return {int(k): v for k, v in data.items()}
            return {}
        except Exception as e:
            logger.error(f"Failed to load daily usage data: {e}")
            return {}

    def _save_data(self):
        """Save user data to file."""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.user_requests, f)
        except Exception as e:
            logger.error(f"Failed to save daily usage data: {e}")

    def _clean_old_data(self):
        """Clean data older than 24 hours."""
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')

        for user_id in list(self.user_requests.keys()):
            user_data = self.user_requests[user_id]
            if user_data.get('date') != today:
                # Reset data for new day
                self.user_requests[user_id] = {
                    'date': today,
                    'count': 0,
                    'requests': []
                }

    def can_process(self, user_id: int) -> bool:
        """Check if user can process another file today."""
        self._clean_old_data()

        if user_id not in self.user_requests:
            today = datetime.now().strftime('%Y-%m-%d')
            self.user_requests[user_id] = {
                'date': today,
                'count': 0,
                'requests': []
            }

        current_count = self.user_requests[user_id]['count']
        return current_count < self.max_files_per_day

    def record_processing(self, user_id: int):
        """Record a processing request for a user."""
        self._clean_old_data()

        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().isoformat()

        if user_id not in self.user_requests:
            self.user_requests[user_id] = {
                'date': today,
                'count': 0,
                'requests': []
            }

        self.user_requests[user_id]['count'] += 1
        self.user_requests[user_id]['requests'].append(now)
        self._save_data()

    def get_remaining_quota(self, user_id: int) -> int:
        """Get remaining quota for user today."""
        self._clean_old_data()

        if user_id not in self.user_requests:
            return self.max_files_per_day

        current_count = self.user_requests[user_id]['count']
        return max(0, self.max_files_per_day - current_count)

    def get_usage_info(self, user_id: int) -> str:
        """Get usage information for user."""
        remaining = self.get_remaining_quota(user_id)
        used = self.max_files_per_day - remaining

        return f"""
📊 **استخدامك اليومي:**
• استخدمت: {used}/{self.max_files_per_day} ملفات
• متبقي لك: {remaining} ملفات
• سيتم إعادة تعيين الحد غداً
        """


class RateLimiter:
    """Manages hourly rate limiting for users (legacy support)."""

    def __init__(self, max_files_per_hour: int = 10):
        self.max_files_per_hour = max_files_per_hour
        self.user_requests: Dict[int, list] = {}

    def can_process(self, user_id: int) -> bool:
        """Check if user can process another file."""
        now = datetime.now()

        # Clean old requests (older than 1 hour)
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id]
                if now - req_time < timedelta(hours=1)
            ]

        # Check current request count
        current_requests = len(self.user_requests.get(user_id, []))
        return current_requests < self.max_files_per_hour

    def record_processing(self, user_id: int):
        """Record a processing request for a user."""
        now = datetime.now()

        if user_id not in self.user_requests:
            self.user_requests[user_id] = []

        self.user_requests[user_id].append(now)

    def get_remaining_quota(self, user_id: int) -> int:
        """Get remaining quota for user."""
        now = datetime.now()

        if user_id not in self.user_requests:
            return self.max_files_per_hour

        # Clean old requests
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if now - req_time < timedelta(hours=1)
        ]

        current_requests = len(self.user_requests[user_id])
        return max(0, self.max_files_per_hour - current_requests)


class TextProcessor:
    """Helper functions for text processing."""

    @staticmethod
    def split_long_text(text: str, max_length: int = 30000) -> List[str]:
        """Split long text into chunks while preserving sentence boundaries."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = ""
        sentences = text.split('. ')

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= max_length:
                if current_chunk:
                    current_chunk += '. ' + sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text content."""
        # Remove excessive whitespace
        text = ' '.join(text.split())

        # Remove special characters that might cause issues
        text = text.replace('\x00', '')  # Remove null bytes
        # Remove specific unwanted text
        text = text.replace("غللا ةيئانث ةمجرت", "")
        text = text.replace("Word", "")

        return text.strip()

    @staticmethod
    def is_english_text(text: str) -> bool:
        """Simple check to determine if text is primarily English."""
        try:
            # Count ASCII characters
            ascii_count = sum(1 for char in text if ord(char) < 128)
            total_chars = len(text)

            if total_chars == 0:
                return False

            # If more than 80% ASCII, consider it English
            return (ascii_count / total_chars) > 0.8

        except Exception:
            return True  # Default to English on error


async def periodic_cleanup_task(cleanup_manager: FileCleanupManager):
    """Periodic task to clean up old files."""
    while True:
        try:
            await cleanup_manager.cleanup_old_files(max_age_hours=24)
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Periodic cleanup task failed: {e}")
            await asyncio.sleep(3600)  # Continue on error