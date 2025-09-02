"""
PostgreSQL Database Manager
إدارة قاعدة البيانات لتخزين إحصائيات الاستخدام والمستخدمين
"""

import asyncio
import asyncpg
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    """مدير قاعدة البيانات PostgreSQL"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgres://mammal:vA2_oE4_iM7_qI2_gY1-@asia-east1-001.proxy.kinsta.app:30525/trnsalnat")
        self.pool = None
        
    async def initialize(self):
        """تهيئة اتصال قاعدة البيانات وإنشاء الجداول"""
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            
            # Create tables if they don't exist
            await self._create_tables()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def _create_tables(self):
        """إنشاء جداول قاعدة البيانات"""
        async with self.pool.acquire() as conn:
            # Users table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    language_code VARCHAR(10),
                    is_bot BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    total_files_processed INTEGER DEFAULT 0,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Translation history table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS translation_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    file_name VARCHAR(500),
                    file_size BIGINT,
                    file_type VARCHAR(50),
                    lines_count INTEGER,
                    processing_time_seconds REAL,
                    api_service VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'completed'
                )
            ''')
            
            # API usage statistics
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS api_usage (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    api_service VARCHAR(50),
                    request_type VARCHAR(100),
                    tokens_used INTEGER DEFAULT 0,
                    cost_estimate REAL DEFAULT 0.0,
                    response_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'success'
                )
            ''')
            
            # Rate limiting table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id BIGINT PRIMARY KEY,
                    hourly_count INTEGER DEFAULT 0,
                    daily_count INTEGER DEFAULT 0,
                    weekly_count INTEGER DEFAULT 0,
                    last_hourly_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_daily_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_weekly_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_blocked BOOLEAN DEFAULT FALSE,
                    block_reason VARCHAR(500),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Bot settings table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by BIGINT
                )
            ''')
            
            logger.info("Database tables created/verified successfully")
    
    async def get_or_create_user(self, user_id: int, user_data: Dict) -> Dict:
        """الحصول على المستخدم أو إنشاؤه إذا لم يكن موجوداً"""
        async with self.pool.acquire() as conn:
            # Try to get existing user
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", user_id
            )
            
            if user:
                # Update user activity
                await conn.execute(
                    "UPDATE users SET last_activity = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE user_id = $1",
                    user_id
                )
                return dict(user)
            else:
                # Create new user
                await conn.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, language_code)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        language_code = EXCLUDED.language_code,
                        updated_at = CURRENT_TIMESTAMP
                ''', user_id, user_data.get('username'), user_data.get('first_name'), 
                     user_data.get('last_name'), user_data.get('language_code'))
                
                # Get the created user
                user = await conn.fetchrow(
                    "SELECT * FROM users WHERE user_id = $1", user_id
                )
                logger.info(f"Created new user: {user_id}")
                return dict(user)
    
    async def record_translation(self, user_id: int, file_name: str, file_size: int, 
                               file_type: str, lines_count: int, processing_time: float,
                               api_service: str = "gemini") -> int:
        """تسجيل عملية ترجمة في قاعدة البيانات"""
        async with self.pool.acquire() as conn:
            # Record translation
            translation_id = await conn.fetchval('''
                INSERT INTO translation_history 
                (user_id, file_name, file_size, file_type, lines_count, processing_time_seconds, api_service)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            ''', user_id, file_name, file_size, file_type, lines_count, processing_time, api_service)
            
            # Update user stats
            await conn.execute('''
                UPDATE users SET 
                    total_files_processed = total_files_processed + 1,
                    last_activity = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
            ''', user_id)
            
            return translation_id
    
    async def record_api_usage(self, user_id: int, api_service: str, request_type: str,
                              tokens_used: int = 0, response_time_ms: int = 0,
                              status: str = "success") -> None:
        """تسجيل استخدام API"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO api_usage 
                (user_id, api_service, request_type, tokens_used, response_time_ms, status)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''', user_id, api_service, request_type, tokens_used, response_time_ms, status)
    
    async def get_user_rate_limits(self, user_id: int) -> Dict:
        """الحصول على حدود المعدل للمستخدم"""
        async with self.pool.acquire() as conn:
            # Get or create rate limit record
            rate_limit = await conn.fetchrow(
                "SELECT * FROM rate_limits WHERE user_id = $1", user_id
            )
            
            if not rate_limit:
                # Create new rate limit record
                await conn.execute('''
                    INSERT INTO rate_limits (user_id) VALUES ($1)
                ''', user_id)
                
                rate_limit = await conn.fetchrow(
                    "SELECT * FROM rate_limits WHERE user_id = $1", user_id
                )
            
            # Check if resets are needed
            now = datetime.now()
            rate_limit_dict = dict(rate_limit)
            
            # Reset hourly count if needed
            if now - rate_limit['last_hourly_reset'] >= timedelta(hours=1):
                await conn.execute('''
                    UPDATE rate_limits SET 
                        hourly_count = 0, 
                        last_hourly_reset = CURRENT_TIMESTAMP
                    WHERE user_id = $1
                ''', user_id)
                rate_limit_dict['hourly_count'] = 0
            
            # Reset daily count if needed
            if now - rate_limit['last_daily_reset'] >= timedelta(days=1):
                await conn.execute('''
                    UPDATE rate_limits SET 
                        daily_count = 0, 
                        last_daily_reset = CURRENT_TIMESTAMP
                    WHERE user_id = $1
                ''', user_id)
                rate_limit_dict['daily_count'] = 0
            
            # Reset weekly count if needed
            if now - rate_limit['last_weekly_reset'] >= timedelta(weeks=1):
                await conn.execute('''
                    UPDATE rate_limits SET 
                        weekly_count = 0, 
                        last_weekly_reset = CURRENT_TIMESTAMP
                    WHERE user_id = $1
                ''', user_id)
                rate_limit_dict['weekly_count'] = 0
            
            return rate_limit_dict
    
    async def update_rate_limits(self, user_id: int) -> None:
        """تحديث حدود المعدل بعد معالجة ملف"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE rate_limits SET 
                    hourly_count = hourly_count + 1,
                    daily_count = daily_count + 1,
                    weekly_count = weekly_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
            ''', user_id)
    
    async def get_user_statistics(self, user_id: int) -> Dict:
        """الحصول على إحصائيات المستخدم"""
        async with self.pool.acquire() as conn:
            # Get user info
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", user_id
            )
            
            if not user:
                return {}
            
            # Get translation statistics
            translation_stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_translations,
                    SUM(lines_count) as total_lines_translated,
                    AVG(processing_time_seconds) as avg_processing_time,
                    MAX(created_at) as last_translation
                FROM translation_history 
                WHERE user_id = $1
            ''', user_id)
            
            # Get API usage statistics
            api_stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_api_calls,
                    SUM(tokens_used) as total_tokens,
                    AVG(response_time_ms) as avg_response_time
                FROM api_usage 
                WHERE user_id = $1
            ''', user_id)
            
            # Get rate limits
            rate_limits = await self.get_user_rate_limits(user_id)
            
            return {
                'user_info': dict(user),
                'translation_stats': dict(translation_stats) if translation_stats else {},
                'api_stats': dict(api_stats) if api_stats else {},
                'rate_limits': rate_limits
            }
    
    async def get_admin_statistics(self) -> Dict:
        """الحصول على إحصائيات عامة للإدارة"""
        async with self.pool.acquire() as conn:
            # Total users
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            
            # Active users (last 24 hours)
            active_users = await conn.fetchval('''
                SELECT COUNT(*) FROM users 
                WHERE last_activity >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
            ''')
            
            # Translation statistics
            translation_stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_translations,
                    SUM(lines_count) as total_lines,
                    AVG(processing_time_seconds) as avg_processing_time
                FROM translation_history
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            ''')
            
            # API usage by service
            api_usage_by_service = await conn.fetch('''
                SELECT 
                    api_service,
                    COUNT(*) as usage_count,
                    AVG(response_time_ms) as avg_response_time
                FROM api_usage
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
                GROUP BY api_service
            ''')
            
            # Top users
            top_users = await conn.fetch('''
                SELECT 
                    u.user_id,
                    u.username,
                    u.first_name,
                    COUNT(th.id) as files_translated
                FROM users u
                LEFT JOIN translation_history th ON u.user_id = th.user_id
                WHERE th.created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                GROUP BY u.user_id, u.username, u.first_name
                ORDER BY files_translated DESC
                LIMIT 10
            ''')
            
            return {
                'total_users': total_users,
                'active_users_24h': active_users,
                'translation_stats': dict(translation_stats) if translation_stats else {},
                'api_usage_by_service': [dict(row) for row in api_usage_by_service],
                'top_users': [dict(row) for row in top_users]
            }
    
    async def is_user_blocked(self, user_id: int) -> tuple[bool, str]:
        """فحص ما إذا كان المستخدم محظوراً"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT is_blocked, block_reason FROM rate_limits WHERE user_id = $1",
                user_id
            )
            
            if result and result['is_blocked']:
                return True, result['block_reason'] or "No reason provided"
            
            return False, ""
    
    async def block_user(self, user_id: int, reason: str, blocked_by: int) -> None:
        """حظر مستخدم"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO rate_limits (user_id, is_blocked, block_reason, updated_at)
                VALUES ($1, TRUE, $2, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    is_blocked = TRUE,
                    block_reason = EXCLUDED.block_reason,
                    updated_at = CURRENT_TIMESTAMP
            ''', user_id, reason)
            
            logger.info(f"User {user_id} blocked by {blocked_by}: {reason}")
    
    async def unblock_user(self, user_id: int, unblocked_by: int) -> None:
        """إلغاء حظر مستخدم"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE rate_limits SET 
                    is_blocked = FALSE,
                    block_reason = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
            ''', user_id)
            
            logger.info(f"User {user_id} unblocked by {unblocked_by}")
    
    async def get_bot_setting(self, key: str) -> Optional[str]:
        """الحصول على إعداد من قاعدة البيانات"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT value FROM bot_settings WHERE key = $1", key
            )
            return result
    
    async def set_bot_setting(self, key: str, value: str, description: str = None, updated_by: int = None) -> None:
        """تعيين إعداد في قاعدة البيانات"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO bot_settings (key, value, description, updated_by)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    description = EXCLUDED.description,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = CURRENT_TIMESTAMP
            ''', key, value, description, updated_by)
    
    async def get_recent_translations(self, user_id: int = None, limit: int = 10) -> List[Dict]:
        """الحصول على الترجمات الأخيرة"""
        async with self.pool.acquire() as conn:
            if user_id:
                results = await conn.fetch('''
                    SELECT th.*, u.username, u.first_name
                    FROM translation_history th
                    JOIN users u ON th.user_id = u.user_id
                    WHERE th.user_id = $1
                    ORDER BY th.created_at DESC
                    LIMIT $2
                ''', user_id, limit)
            else:
                results = await conn.fetch('''
                    SELECT th.*, u.username, u.first_name
                    FROM translation_history th
                    JOIN users u ON th.user_id = u.user_id
                    ORDER BY th.created_at DESC
                    LIMIT $1
                ''', limit)
            
            return [dict(row) for row in results]
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> Dict:
        """تنظيف البيانات القديمة"""
        async with self.pool.acquire() as conn:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Clean old translation history
            deleted_translations = await conn.fetchval('''
                DELETE FROM translation_history 
                WHERE created_at < $1
                RETURNING COUNT(*)
            ''', cutoff_date)
            
            # Clean old API usage
            deleted_api_usage = await conn.fetchval('''
                DELETE FROM api_usage 
                WHERE created_at < $1
                RETURNING COUNT(*)
            ''', cutoff_date)
            
            logger.info(f"Cleaned up {deleted_translations} old translations and {deleted_api_usage} old API usage records")
            
            return {
                'deleted_translations': deleted_translations or 0,
                'deleted_api_usage': deleted_api_usage or 0,
                'cutoff_date': cutoff_date.isoformat()
            }
    
    async def close(self):
        """إغلاق اتصال قاعدة البيانات"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")

# إنشاء مثيل عام
db_manager = DatabaseManager()