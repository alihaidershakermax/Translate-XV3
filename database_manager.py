"""
MongoDB Database Manager
إدارة قاعدة البيانات لتخزين إحصائيات الاستخدام والمستخدمين
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import urllib.parse

logger = logging.getLogger(__name__)

class DatabaseManager:
    """مدير قاعدة البيانات MongoDB"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "mongodb://localhost:27017/telegram_bot")
        self.client = None
        self.db = None
        
    async def initialize(self):
        """تهيئة اتصال قاعدة البيانات وإنشاء الجداول"""
        try:
            # Create MongoDB client
            self.client = AsyncIOMotorClient(self.database_url)
            self.db = self.client.get_default_database()
            
            # Create indexes if they don't exist
            await self._create_indexes()
            logger.info("MongoDB initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def _create_indexes(self):
        """إنشاء فهارس قاعدة البيانات"""
        # Users collection indexes
        await self.db.users.create_index("user_id", unique=True)
        await self.db.users.create_index("username")
        await self.db.users.create_index("last_activity")
        
        # Translation history indexes
        await self.db.translation_history.create_index("user_id")
        await self.db.translation_history.create_index("created_at")
        await self.db.translation_history.create_index([("user_id", 1), ("created_at", -1)])
        
        # API usage indexes
        await self.db.api_usage.create_index("user_id")
        await self.db.api_usage.create_index("created_at")
        await self.db.api_usage.create_index("api_service")
        
        # Rate limits indexes
        await self.db.rate_limits.create_index("user_id", unique=True)
        
        logger.info("Database indexes created successfully")
    
    async def get_or_create_user(self, user_id: int, user_data: Dict) -> Dict:
        """الحصول على المستخدم أو إنشاؤه إذا لم يكن موجوداً"""
        # Try to get existing user
        user = await self.db.users.find_one({"user_id": user_id})
        
        if user:
            # Update user activity
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"last_activity": datetime.now(), "updated_at": datetime.now()}}
            )
            return user
        else:
            # Create new user document
            user_doc = {
                "user_id": user_id,
                "username": user_data.get('username'),
                "first_name": user_data.get('first_name'),
                "last_name": user_data.get('last_name'),
                "language_code": user_data.get('language_code'),
                "is_bot": user_data.get('is_bot', False),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "is_active": True,
                "total_files_processed": 0,
                "last_activity": datetime.now()
            }
            
            await self.db.users.insert_one(user_doc)
            logger.info(f"Created new user: {user_id}")
            return user_doc
    
    async def record_translation(self, user_id: int, file_name: str, file_size: int, 
                               file_type: str, lines_count: int, processing_time: float,
                               api_service: str = "gemini") -> str:
        """تسجيل عملية ترجمة في قاعدة البيانات"""
        # Record translation
        translation_doc = {
            "user_id": user_id,
            "file_name": file_name,
            "file_size": file_size,
            "file_type": file_type,
            "lines_count": lines_count,
            "processing_time_seconds": processing_time,
            "api_service": api_service,
            "created_at": datetime.now(),
            "status": "completed"
        }
        
        result = await self.db.translation_history.insert_one(translation_doc)
        
        # Update user stats
        await self.db.users.update_one(
            {"user_id": user_id},
            {
                "$inc": {"total_files_processed": 1},
                "$set": {"last_activity": datetime.now(), "updated_at": datetime.now()}
            }
        )
        
        return str(result.inserted_id)
    
    async def record_api_usage(self, user_id: int, api_service: str, request_type: str,
                              tokens_used: int = 0, response_time_ms: int = 0,
                              status: str = "success") -> None:
        """تسجيل استخدام API"""
        api_usage_doc = {
            "user_id": user_id,
            "api_service": api_service,
            "request_type": request_type,
            "tokens_used": tokens_used,
            "response_time_ms": response_time_ms,
            "status": status,
            "created_at": datetime.now()
        }
        
        await self.db.api_usage.insert_one(api_usage_doc)
    
    async def get_user_rate_limits(self, user_id: int) -> Dict:
        """الحصول على حدود المعدل للمستخدم"""
        # Get or create rate limit record
        rate_limit = await self.db.rate_limits.find_one({"user_id": user_id})
        
        if not rate_limit:
            # Create new rate limit record
            rate_limit_doc = {
                "user_id": user_id,
                "hourly_count": 0,
                "daily_count": 0,
                "weekly_count": 0,
                "last_hourly_reset": datetime.now(),
                "last_daily_reset": datetime.now(),
                "last_weekly_reset": datetime.now(),
                "is_blocked": False,
                "block_reason": None,
                "updated_at": datetime.now()
            }
            
            await self.db.rate_limits.insert_one(rate_limit_doc)
            rate_limit = rate_limit_doc
        
        # Check if resets are needed
        now = datetime.now()
        rate_limit_updated = False
        
        # Reset hourly count if needed
        if now - rate_limit['last_hourly_reset'] >= timedelta(hours=1):
            await self.db.rate_limits.update_one(
                {"user_id": user_id},
                {"$set": {"hourly_count": 0, "last_hourly_reset": datetime.now()}}
            )
            rate_limit['hourly_count'] = 0
            rate_limit_updated = True
        
        # Reset daily count if needed
        if now - rate_limit['last_daily_reset'] >= timedelta(days=1):
            await self.db.rate_limits.update_one(
                {"user_id": user_id},
                {"$set": {"daily_count": 0, "last_daily_reset": datetime.now()}}
            )
            rate_limit['daily_count'] = 0
            rate_limit_updated = True
        
        # Reset weekly count if needed
        if now - rate_limit['last_weekly_reset'] >= timedelta(weeks=1):
            await self.db.rate_limits.update_one(
                {"user_id": user_id},
                {"$set": {"weekly_count": 0, "last_weekly_reset": datetime.now()}}
            )
            rate_limit['weekly_count'] = 0
            rate_limit_updated = True
        
        if rate_limit_updated:
            # Refresh the document after updates
            rate_limit = await self.db.rate_limits.find_one({"user_id": user_id})
        
        return rate_limit
    
    async def update_rate_limits(self, user_id: int) -> None:
        """تحديث حدود المعدل بعد معالجة ملف"""
        await self.db.rate_limits.update_one(
            {"user_id": user_id},
            {
                "$inc": {
                    "hourly_count": 1,
                    "daily_count": 1,
                    "weekly_count": 1
                },
                "$set": {"updated_at": datetime.now()}
            }
        )
    
    async def get_user_statistics(self, user_id: int) -> Dict:
        """الحصول على إحصائيات المستخدم"""
        # Get user info
        user = await self.db.users.find_one({"user_id": user_id})
        
        if not user:
            return {}
        
        # Get translation statistics
        translation_pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": None,
                    "total_translations": {"$sum": 1},
                    "total_lines_translated": {"$sum": "$lines_count"},
                    "avg_processing_time": {"$avg": "$processing_time_seconds"}
                }
            }
        ]
        
        translation_stats_cursor = self.db.translation_history.aggregate(translation_pipeline)
        translation_stats_list = await translation_stats_cursor.to_list(length=1)
        translation_stats = translation_stats_list[0] if translation_stats_list else {}
        
        # Get API usage statistics
        api_pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": None,
                    "total_api_calls": {"$sum": 1},
                    "total_tokens": {"$sum": "$tokens_used"},
                    "avg_response_time": {"$avg": "$response_time_ms"}
                }
            }
        ]
        
        api_stats_cursor = self.db.api_usage.aggregate(api_pipeline)
        api_stats_list = await api_stats_cursor.to_list(length=1)
        api_stats = api_stats_list[0] if api_stats_list else {}
        
        # Get rate limits
        rate_limits = await self.get_user_rate_limits(user_id)
        
        # Get last translation
        last_translation = await self.db.translation_history.find_one(
            {"user_id": user_id},
            sort=[("created_at", -1)]
        )
        
        if translation_stats:
            translation_stats["last_translation"] = last_translation["created_at"] if last_translation else None
        
        return {
            'user_info': user,
            'translation_stats': translation_stats,
            'api_stats': api_stats,
            'rate_limits': rate_limits
        }
    
    async def get_admin_statistics(self) -> Dict:
        """الحصول على إحصائيات عامة للإدارة"""
        # Total users
        total_users = await self.db.users.count_documents({})
        
        # Active users (last 24 hours)
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        active_users = await self.db.users.count_documents({
            "last_activity": {"$gte": twenty_four_hours_ago}
        })
        
        # Translation statistics (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        translation_pipeline = [
            {"$match": {"created_at": {"$gte": thirty_days_ago}}},
            {
                "$group": {
                    "_id": None,
                    "total_translations": {"$sum": 1},
                    "total_lines": {"$sum": "$lines_count"},
                    "avg_processing_time": {"$avg": "$processing_time_seconds"}
                }
            }
        ]
        
        translation_stats_cursor = self.db.translation_history.aggregate(translation_pipeline)
        translation_stats_list = await translation_stats_cursor.to_list(length=1)
        translation_stats = translation_stats_list[0] if translation_stats_list else {}
        
        # API usage by service (last 24 hours)
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        api_usage_by_service_pipeline = [
            {"$match": {"created_at": {"$gte": twenty_four_hours_ago}}},
            {
                "$group": {
                    "_id": "$api_service",
                    "usage_count": {"$sum": 1},
                    "avg_response_time": {"$avg": "$response_time_ms"}
                }
            }
        ]
        
        api_usage_cursor = self.db.api_usage.aggregate(api_usage_by_service_pipeline)
        api_usage_by_service = await api_usage_cursor.to_list(length=None)
        
        # Top users (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        top_users_pipeline = [
            {"$match": {"created_at": {"$gte": thirty_days_ago}}},
            {
                "$group": {
                    "_id": "$user_id",
                    "files_translated": {"$sum": 1}
                }
            },
            {"$sort": {"files_translated": -1}},
            {"$limit": 10}
        ]
        
        top_users_cursor = self.db.translation_history.aggregate(top_users_pipeline)
        top_users_list = await top_users_cursor.to_list(length=None)
        
        # Get user details for top users
        top_users = []
        for user_stat in top_users_list:
            user = await self.db.users.find_one({"user_id": user_stat["_id"]})
            if user:
                top_users.append({
                    "user_id": user["user_id"],
                    "username": user.get("username"),
                    "first_name": user.get("first_name"),
                    "files_translated": user_stat["files_translated"]
                })
        
        return {
            'total_users': total_users,
            'active_users_24h': active_users,
            'translation_stats': translation_stats,
            'api_usage_by_service': api_usage_by_service,
            'top_users': top_users
        }
    
    async def is_user_blocked(self, user_id: int) -> tuple[bool, str]:
        """فحص ما إذا كان المستخدم محظوراً"""
        result = await self.db.rate_limits.find_one({"user_id": user_id})
        
        if result and result.get('is_blocked'):
            return True, result.get('block_reason') or "No reason provided"
        
        return False, ""
    
    async def block_user(self, user_id: int, reason: str, blocked_by: int) -> None:
        """حظر مستخدم"""
        await self.db.rate_limits.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "is_blocked": True,
                    "block_reason": reason,
                    "updated_at": datetime.now()
                }
            },
            upsert=True
        )
        
        logger.info(f"User {user_id} blocked by {blocked_by}: {reason}")
    
    async def unblock_user(self, user_id: int, unblocked_by: int) -> None:
        """إلغاء حظر مستخدم"""
        await self.db.rate_limits.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "is_blocked": False,
                    "block_reason": None,
                    "updated_at": datetime.now()
                }
            }
        )
        
        logger.info(f"User {user_id} unblocked by {unblocked_by}")
    
    async def get_bot_setting(self, key: str) -> Optional[str]:
        """الحصول على إعداد من قاعدة البيانات"""
        result = await self.db.bot_settings.find_one({"key": key})
        return result["value"] if result else None
    
    async def set_bot_setting(self, key: str, value: str, description: str = None, updated_by: int = None) -> None:
        """تعيين إعداد في قاعدة البيانات"""
        bot_setting_doc = {
            "key": key,
            "value": value,
            "description": description,
            "updated_by": updated_by,
            "updated_at": datetime.now()
        }
        
        await self.db.bot_settings.update_one(
            {"key": key},
            {"$set": bot_setting_doc},
            upsert=True
        )
    
    async def get_recent_translations(self, user_id: int = None, limit: int = 10) -> List[Dict]:
        """الحصول على الترجمات الأخيرة"""
        query = {}
        if user_id:
            query["user_id"] = user_id
            
        cursor = self.db.translation_history.find(query).sort("created_at", -1).limit(limit)
        results = await cursor.to_list(length=limit)
        
        # Add user info to each translation
        for translation in results:
            user = await self.db.users.find_one({"user_id": translation["user_id"]})
            if user:
                translation["username"] = user.get("username")
                translation["first_name"] = user.get("first_name")
        
        return results
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> Dict:
        """تنظيف البيانات القديمة"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Clean old translation history
        deleted_translations = await self.db.translation_history.delete_many({
            "created_at": {"$lt": cutoff_date}
        })
        
        # Clean old API usage
        deleted_api_usage = await self.db.api_usage.delete_many({
            "created_at": {"$lt": cutoff_date}
        })
        
        logger.info(f"Cleaned up {deleted_translations.deleted_count} old translations and {deleted_api_usage.deleted_count} old API usage records")
        
        return {
            'deleted_translations': deleted_translations.deleted_count,
            'deleted_api_usage': deleted_api_usage.deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
    
    async def close(self):
        """إغلاق اتصال قاعدة البيانات"""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")

# إنشاء مثيل عام
db_manager = DatabaseManager()