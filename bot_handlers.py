"""
Telegram bot handlers module.
Contains all bot command and message handlers.
"""

import logging
import asyncio
from pathlib import Path
import tempfile
import uuid
from typing import Dict, Set
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from telegram.constants import ChatAction

from config import Config
from file_handlers import FileProcessor
from translator import GeminiTranslator
from document_generator import WordDocumentGenerator
from utils import RateLimiter, DailyRateLimiter, FileCleanupManager
from ui_config import ui_config
from multi_api_manager import multi_api_manager, MultiGeminiTranslatorManager
from database_manager import db_manager


logger = logging.getLogger(__name__)


class BotHandlers:
    """Handles all bot interactions and message processing."""

    def __init__(self, config: Config):
        """Initialize the bot handlers with necessary components."""
        self.config = config
        self.file_processor = FileProcessor()
        # Initialize multi_api_manager with config which contains the list of API keys
        self.translator = GeminiTranslator(config.GEMINI_API_KEY, config.GEMINI_MODEL) # Still keep one as default
        self.translator_manager = MultiGeminiTranslatorManager(config.GEMINI_API_KEYS, config.GEMINI_MODEL)

        self.document_generator = WordDocumentGenerator()
        self.cleanup_manager = FileCleanupManager(config.TEMP_DIR)
        self.rate_limiter = RateLimiter(config.RATE_LIMIT_PER_USER) # Per-hour rate limiter
        self.daily_limiter = DailyRateLimiter(config.DAILY_RATE_LIMIT_PER_USER) # Daily rate limiter

        # Track active translations to prevent concurrent processing
        self.active_translations: Set[int] = set()

        # Store user files temporarily for format selection
        self.user_files: Dict[int, Dict] = {}

    async def _update_progress(self, update: Update, message_id: int, current: int, total: int, description: str):
        """Update progress message with real percentage and estimated time."""
        try:
            percentage = int((current / total) * 100) if total > 0 else 0

            # Calculate estimated time
            estimated_time = self._calculate_estimated_time(current, total, description)

            progress_text = f"""
🔄 **جاري المعالجة...**

📊 **التقدم:** {percentage}%

📋 **المرحلة:** {description}
📈 **المعالج:** {current}/{total}

⏰ **الوقت المتوقع:** {estimated_time}

⏳ يرجى الانتظار...
            """

            await update.get_bot().edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=progress_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to update progress: {e}")

    def _calculate_estimated_time(self, current: int, total: int, description: str) -> str:
        """Calculate estimated time based on current progress and stage."""
        if current == 0:
            if "استخراج" in description:
                return "~30 ثانية"
            elif "ترجمة" in description:
                # Estimate ~3 seconds per line
                estimated_seconds = total * 3
                if estimated_seconds < 60:
                    return f"~{estimated_seconds} ثانية"
                else:
                    minutes = estimated_seconds // 60
                    return f"~{minutes} دقيقة"
            elif "إنشاء" in description:
                return "~20 ثانية"
            else:
                return "~1 دقيقة"

        # Calculate based on progress
        if current >= total:
            return "اكتمل"

        remaining = total - current
        if "ترجمة" in description:
            remaining_seconds = remaining * 3
            if remaining_seconds < 60:
                return f"~{remaining_seconds} ثانية"
            else:
                minutes = remaining_seconds // 60
                return f"~{minutes} دقيقة"
        elif "إنشاء" in description:
            return "~10 ثواني"
        else:
            return "قريباً"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        try:
            user = update.effective_user
            logger.info(f"User {user.id} ({user.username}) started the bot")

            welcome_message = """
🎉 أهلاً بك في بوت الترجمة!
تطوير: @dextermorgenk

🚀 كل ما عليك فعله:

1. أرسل الملف الذي تريد ترجمته.

2. اختر نمط الترجمة الذي يعجبك.

😎 نصيحة صديق: لا ترسل ملفات كثيرة مرة واحدة، حتى يبقى البوت سعيدًا ويعمل بسرعة!

هيا نبدأ، جرب إرسال ملفك الأول الآن! ✨
            """

            await update.message.reply_text(welcome_message)

        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ Sorry, an error occurred. Please try again.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        try:
            help_message = """
📖 **Detailed Help - Translation Bot**

🔧 **How it works:**
1. **Upload**: Send a PDF or Word document
2. **Processing**: I extract text content from your file
3. **Translation**: Each line is translated English → Arabic using AI
4. **Output**: You receive a Word document with both languages

📋 **Supported file types:**
• PDF documents (.pdf) - up to 20MB
• Microsoft Word (.doc, .docx) - up to 20MB

⚠️ **Important notes:**
• Only English text will be translated to Arabic
• Images and complex formatting may not be preserved
• Large files may take several minutes to process
• Rate limit: 10 files per hour per user

🚫 **Limitations:**
• OCR (image text recognition) not yet supported
• Only text content is extracted
• Maximum 30,000 characters per document

❓ **Troubleshooting:**
• File too large? Try splitting it into smaller parts
• No text extracted? Ensure your document contains readable text
• Translation failed? Try again in a few minutes

💡 **Tips:**
• Clear, well-formatted documents work best
• Avoid files with only images or scanned content
• Wait for processing to complete before sending another file

🔄 **Commands:**
/start - Welcome message
/help - This help information
/status - Check bot and API status
/font_size - Control font sizes in documents
• **حد الاستخدام اليومي:** 50 ملفاً في اليوم
• **معالجة سريعة:** بدون تأخيرات غير ضرورية
• **بدون اشتراك إجباري:** استخدم البوت مباشرة
            """

            await update.message.reply_text(help_message)

        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await update.message.reply_text("❌ Sorry, an error occurred. Please try again.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command - Check bot and API status."""
        try:
            user = update.effective_user
            logger.info(f"User {user.id} ({user.username}) requested status")

            if self.can_view_all_users(user.id):
                # Admin/Owner view - show comprehensive stats
                await self._show_admin_status(update, context)
            else:
                # Regular user view - show personal stats only
                await self._show_user_status(update, context, user.id)

        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text("❌ حدث خطأ في فحص الحالة. يرجى المحاولة مرة أخرى.")

    async def _show_admin_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show comprehensive status for admins/owners."""
        # Check bot status
        bot_status = "🟢 متصل ويعمل بشكل طبيعي"
        api_status = "🔍 جاري فحص حالة API..."

        # Get API manager status
        api_manager_status = multi_api_manager.get_status()

        status_message = f"""
👑 **حالة البوت - عرض الأدمن**

🤖 **حالة البوت:** {bot_status}

🔧 **حالة مفاتيح API:**
• إجمالي المفاتيح: {api_manager_status['total_keys']}
• المفاتيح النشطة: {api_manager_status['active_keys']}

⚡ **الأداء الحالي:**
• المترجمات النشطة: {len(self.active_translations)}
• الملفات المؤقتة: {len(self.user_files)}

📊 **إحصائيات النظام:**
• الملفات المدعومة: PDF, DOC, DOCX
• الحد الأقصى للملف: 50 ميجابايت
• الحد الأقصى: 10 ملفات/ساعة للمستخدم

تطوير: @dextermorgenk
        """

        # Send initial status
        message = await update.message.reply_text(status_message)

        # Test API connection
        try:
            test_result = await self.translator_manager.translate_single_line("Hello")
            if test_result and test_result != "Hello":
                api_status = "🟢 Google Gemini API متصل ويعمل"
            else:
                api_status = "🟡 Google Gemini API متصل لكن قد يكون هناك مشاكل"
        except Exception as api_error:
            error_str = str(api_error)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                api_status = "🔴 تم تجاوز حصة الترجمة اليومية"
            else:
                api_status = "🔴 Google Gemini API غير متاح"

        # Update with API test results
        updated_status = f"""
👑 **حالة البوت - عرض الأدمن**

🤖 **حالة البوت:** {bot_status}
🔧 **حالة API:** {api_status}

🗝️ **تفاصيل مفاتيح API:**
• إجمالي المفاتيح: {api_manager_status['total_keys']}
• المفاتيح النشطة: {api_manager_status['active_keys']}

⚡ **الأداء الحالي:**
• المترجمات النشطة: {len(self.active_translations)}
• الملفات المؤقتة: {len(self.user_files)}

📊 **إحصائيات النظام:**
• الملفات المدعومة: PDF, DOC, DOCX
• الحد الأقصى للملف: 50 ميجابايت
• الحد الأقصى: 10 ملفات/ساعة للمستخدم

تطوير: @dextermorgenk
        """

        await message.edit_text(updated_status)

    async def _show_user_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Show personal status for regular users."""
        # Get user's daily usage
        user_daily_count = self.daily_limiter.get_user_count(user_id)
        user_hourly_count = self.rate_limiter.get_user_count(user_id)

        # Calculate time until next reset
        next_hourly_reset = self.rate_limiter.get_next_reset_time(user_id)
        next_daily_reset = self.daily_limiter.get_next_reset_time(user_id)

        # Format reset times
        hourly_reset_str = next_hourly_reset.strftime("%H:%M:%S") if next_hourly_reset else "متاح الآن"
        daily_reset_str = next_daily_reset.strftime("%H:%M:%S") if next_daily_reset else "متاح الآن"

        status_message = f"""
👤 **حالتك الشخصية**

📈 **استخدامك اليوم:**
• الملفات المترجمة: {user_daily_count}/50
• المتبقي: {50 - user_daily_count} ملف

⏱️ **استخدامك الساعي:**
• الملفات المترجمة: {user_hourly_count}/10
• المتبقي: {10 - user_hourly_count} ملف

🔄 **أوقات التجديد:**
• التجديد الساعي: {hourly_reset_str}
• التجديد اليومي: {daily_reset_str}

📊 **حدودك:**
• الحد الأقصى للملف: 50 ميجابايت
• الحد الساعي: 10 ملفات
• الحد اليومي: 50 ملف

تطوير: @dextermorgenk
        """

        await update.message.reply_text(status_message)

    async def commands_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /commands command - Show all available commands."""
        try:
            user = update.effective_user
            logger.info(f"User {user.id} ({user.username}) requested commands list")

            commands_message = """
📋 **قائمة الأوامر المتاحة**

🚀 **الأوامر الأساسية:**
/start - رسالة الترحيب وبدء استخدام البوت
/help - معلومات تفصيلية ومساعدة شاملة
/status - فحص حالة البوت و Google Gemini API
/commands - عرض هذه القائمة
/font_size - للتحكم بحجم الخط في المستندات
• **حد الاستخدام اليومي:** 50 ملفاً في اليوم
• **معالجة سريعة:** تحسينات في الأداء
• **سهولة الاستخدام:** بدون قيود اشتراك

📄 **كيفية الاستخدام:**
1. أرسل ملف PDF أو Word للبوت
2. انتظر استخراج النص وتحضير الخيارات
3. اختر نمط الملف المطلوب (Word أو PDF ثنائي اللغة)
4. انتظر انتهاء الترجمة وتحميل الملف

⚙️ **المواصفات التقنية:**
• أنواع الملفات: .pdf, .doc, .docx
• الحد الأقصى: 50 ميجابايت
• معدل الاستخدام: 10 ملفات في الساعة
• اللغات: إنجليزي ← عربي

💡 **نصائح:**
• تأكد من وضوح النص في الملف
• تجنب الملفات التي تحتوي على صور فقط
• انتظر انتهاء معالجة ملف قبل إرسال آخر

🔧 تطوير: @dextermorgenk

هل تحتاج مساعدة إضافية؟ استخدم الأمر /help للحصول على تفاصيل أكثر!
            """

            await update.message.reply_text(commands_message)

        except Exception as e:
            logger.error(f"Error in commands command: {e}")
            await update.message.reply_text("❌ حدث خطأ في عرض الأوامر. يرجى المحاولة مرة أخرى.")

    async def font_size_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /font_size command - Control font sizes in documents."""
        try:
            user = update.effective_user
            logger.info(f"User {user.id} ({user.username}) requested font size settings")

            # Check if user provided a size argument
            if context.args and len(context.args) > 0:
                try:
                    new_size = int(context.args[0])
                    if ui_config.set_font_size(new_size):
                        size_message = f"""
✅ **تم تغيير حجم الخط بنجاح!**

📏 **الحجم الجديد:** {new_size}pt
📄 **سيطبق على:** المستندات الجديدة فقط

💡 **نصيحة:** الحجم المثالي بين 14-20pt
                        """
                    else:
                        size_message = """
❌ **حجم خط غير صالح!**

📏 **النطاق المسموح:** 10-24pt
📋 **مثال:** `/font_size 18`

💡 استخدم `/font_size` بدون رقم لمعرفة الحجم الحالي
                        """
                except ValueError:
                    size_message = """
❌ **يرجى إدخال رقم صحيح!**

📋 **مثال:** `/font_size 18`
📏 **النطاق المسموح:** 10-24pt
                    """
            else:
                # Show current font size and options
                current_size = ui_config.get_font_size()
                size_message = f"""
⚙️ **إعدادات حجم الخط**

📏 **الحجم الحالي:** {current_size}pt

🔧 **لتغيير الحجم:**
`/font_size [الحجم]`

📋 **أمثلة:**
• `/font_size 14` - خط صغير
• `/font_size 16` - خط متوسط (افتراضي)
• `/font_size 18` - خط كبير
• `/font_size 20` - خط كبير جداً

📏 **النطاق المسموح:** 10-24pt
💡 **ملاحظة:** سيطبق على المستندات الجديدة فقط
                """

            await update.message.reply_text(size_message)

        except Exception as e:
            logger.error(f"Error in font_size command: {e}")
            await update.message.reply_text("❌ حدث خطأ في إعدادات الخط. يرجى المحاولة مرة أخرى.")

    async def check_channel_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Checks if the user is subscribed to the required channel."""
        user_id = update.effective_user.id
        channel_username = self.config.CHANNEL_USERNAME # Assuming this is set in config.py

        # Removed mandatory channel subscription check
        logger.info(f"Skipping mandatory channel subscription check for user {user_id}")
        return True


    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads."""
        user_id = update.effective_user.id

        try:
            # Check if user is blocked
            is_blocked, block_reason = await db_manager.is_user_blocked(user_id)
            if is_blocked:
                await update.message.reply_text(f"❌ تم حظرك من استخدام البوت\nالسبب: {block_reason}")
                return

            # Check channel subscription first
            if not await self.check_channel_subscription(update, context):
                return

            # Check if user is already processing a file
            if user_id in self.active_translations:
                await update.message.reply_text(
                    "⏳ You already have a file being processed. Please wait for it to complete."
                )
                return

            # Check daily rate limits
            if not self.daily_limiter.can_process(user_id):
                await update.message.reply_text(
                    "🚫 Daily limit exceeded. You can process up to 3 files per day. Please try again tomorrow."
                )
                return

            document = update.message.document

            # Validate file
            if not self._validate_document(document):
                await update.message.reply_text(
                    "❌ ملف غير صالح. يرجى إرسال مستند PDF أو Word (.pdf, .doc, .docx) أقل من 50 ميجابايت."
                )
                return

            # Add user to active translations
            self.active_translations.add(user_id)

            try:
                await self._show_format_options(update, context, document)
            finally:
                # Remove user from active translations if no format selection pending
                if user_id not in self.user_files:
                    self.active_translations.discard(user_id)

        except Exception as e:
            logger.error(f"Error handling document from user {user_id}: {e}")
            await update.message.reply_text(
                "❌ An error occurred while processing your document. Please try again."
            )
            self.active_translations.discard(user_id)

    async def _show_format_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, document):
        """Show format selection options to user."""
        user_id = update.effective_user.id

        try:
            # Initialize progress
            processing_msg = await update.message.reply_text("🔄 جاري التحضير...")

            # Step 1: Download file
            await self._update_progress(update, processing_msg.message_id, 1, 3, "تحميل الملف")
            file_path = await self._download_file(document, context)

            # Step 2: Extract text
            await self._update_progress(update, processing_msg.message_id, 2, 3, "استخراج النص من الملف (تصفية أرقام الصفحات)")
            text_lines = await self.file_processor.extract_text_from_file(file_path)

            # Step 3: Finalize preparation
            await self._update_progress(update, processing_msg.message_id, 3, 3, "تحضير خيارات التنسيق")

            if not text_lines:
                await processing_msg.edit_text("❌ لم يتم العثور على نص في الملف.")
                return

            # Store file info for later processing
            self.user_files[user_id] = {
                'file_path': file_path,
                'text_lines': text_lines,
                'original_filename': document.file_name,
                'processing_msg_id': processing_msg.message_id
            }

            # Create inline keyboard with format options - bilingual only
            keyboard = [
                [
                    InlineKeyboardButton("📄 Word ثنائي اللغة", callback_data="bilingual_word"),
                    InlineKeyboardButton("📑 PDF ثنائي اللغة", callback_data="bilingual_pdf")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await processing_msg.edit_text(
                f"✅ تم استخراج {len(text_lines)} سطر من النص\n\n🎯 اختر تنسيق الملف المطلوب:",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error showing format options for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ حدث خطأ أثناء تحضير الملف. يرجى المحاولة مرة أخرى."
            )
            self.active_translations.discard(user_id)

    async def handle_format_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle format selection from inline keyboard."""
        query = update.callback_query
        user_id = update.effective_user.id

        try:
            await query.answer()

            if user_id not in self.user_files:
                await query.edit_message_text("❌ انتهت صلاحية الطلب. يرجى إرسال الملف مرة أخرى.")
                return

            file_info = self.user_files[user_id]
            format_type = query.data.replace('format_', '')

            # Validate format selection - bilingual only
            valid_formats = ['bilingual_word', 'bilingual_pdf']
            if format_type not in valid_formats:
                await query.edit_message_text("❌ تنسيق غير صالح. يرجى اختيار تنسيق ثنائي اللغة.")
                return

            # Start processing
            await query.edit_message_text("🔄 جاري الترجمة والتحويل...")

            await self._process_document_with_format(
                query, context, file_info, format_type
            )

        except Exception as e:
            logger.error(f"Error handling format selection for user {user_id}: {e}")
            await query.edit_message_text(
                "❌ حدث خطأ أثناء المعالجة. يرجى المحاولة مرة أخرى."
            )
        finally:
            # Cleanup
            if user_id in self.user_files:
                del self.user_files[user_id]
            self.active_translations.discard(user_id)

    async def _process_document_with_format(self, query, context, file_info: dict, format_type: str):
        """Process document with selected format with real progress tracking."""
        user_id = query.from_user.id
        total_lines = len(file_info['text_lines'])

        temp_files = [file_info['file_path']]

        try:
            # Step 1: Initialize processing
            await self._update_progress_query_real(query, 0, total_lines, "تحضير المعالجة")
            await asyncio.sleep(0.2)

            # Step 2: Start translation with real progress
            # Use the multi-API translator manager
            translated_pairs = await self.translator_manager.translate_lines_with_progress(
                file_info['text_lines'],
                lambda current, total, status: self._update_progress_query_real(query, current, total, status)
            )

            # Step 3: Generate document
            await self._update_progress_query_real(query, total_lines, total_lines, "إنشاء المستند المنسق")

            if format_type == 'bilingual_word':
                output_path = self.config.get_temp_file_path(f"bilingual_{uuid.uuid4().hex}.docx")
                await self.document_generator.create_bilingual_document(
                    translated_pairs, output_path, file_info['original_filename']
                )
                caption = "✅ تمت الترجمة! ملف Word ثنائي اللغة"
                filename = f"bilingual_{file_info['original_filename']}.docx"

            elif format_type == 'bilingual_pdf':
                output_path = self.config.get_temp_file_path(f"bilingual_{uuid.uuid4().hex}.pdf")
                await self.document_generator.create_bilingual_pdf(
                    translated_pairs, output_path, file_info['original_filename']
                )
                caption = "✅ تمت الترجمة! ملف PDF ثنائي اللغة"
                filename = f"bilingual_{file_info['original_filename']}.pdf"

            temp_files.append(output_path)

            # Step 4: Prepare for sending
            await self._update_progress_query_real(query, total_lines, total_lines, "تحضير الملف للإرسال")

            # Step 5: Send the document
            await self._update_progress_query_real(query, total_lines, total_lines, "إرسال الملف المترجم")

            with open(output_path, 'rb') as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=filename,
                    caption=caption
                )

            # Delete the processing message
            await query.delete_message()

            # Update daily rate limiter
            self.daily_limiter.record_processing(user_id)

            logger.info(f"Successfully processed document for user {user_id} in format {format_type}")

        except Exception as e:
            logger.error(f"Document processing failed for user {user_id}: {e}")
            error_msg = str(e)

            # Check if it's a quota error
            if "حصة الترجمة" in error_msg or "quota" in error_msg.lower():
                await query.edit_message_text(
                    "❌ **تم تجاوز حصة الترجمة اليومية**\n\n"
                    "🔄 يرجى المحاولة غداً أو الاتصال بالمطور لترقية الخطة.\n\n"
                    "💡 **نصيحة:** يمكنك تقسيم الملف إلى أجزاء أصغر."
                )
            else:
                await query.edit_message_text(
                    f"❌ فشل في المعالجة: {error_msg}\n\nيرجى المحاولة مرة أخرى."
                )
        finally:
            # Clean up temporary files
            await self.cleanup_manager.cleanup_files(temp_files)

    async def _update_progress_query_real(self, query, current: int, total: int, status: str):
        """Update progress for callback query with real percentage and estimated time."""
        try:
            percentage = int((current / total) * 100) if total > 0 else 0

            # Calculate estimated time
            estimated_time = self._calculate_estimated_time(current, total, status)

            progress_text = f"""🔄 **جاري المعالجة...**

📊 **التقدم:** {percentage}%

📋 **المرحلة:** {status}
📈 **المعالج:** {current}/{total}

⏰ **الوقت المتوقع:** {estimated_time}

⏳ يرجى الانتظار..."""

            await query.edit_message_text(
                text=progress_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to update progress: {e}")

    async def _update_progress_query(self, query, current_step: int, total_steps: int, status: str):
        """Update progress for callback query with percentage."""
        try:
            percentage = int((current_step / total_steps) * 100)
            progress_text = f"🔄 **جاري المعالجة...**\n\n📊 **التقدم:** {percentage}%\n\n📋 **المرحلة:** {status}"

            await query.edit_message_text(
                text=progress_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to update progress: {e}")

    async def _process_document_old(self, update: Update, context: ContextTypes.DEFAULT_TYPE, document):
        user_id = update.effective_user.id

        # Send initial processing message
        processing_msg = await update.message.reply_text("📄 Processing your document...")

        temp_files = []

        try:
            # Send typing action
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

            # Download the file
            await processing_msg.edit_text("📥 Downloading file...")
            file_path = await self._download_file(document, context)
            temp_files.append(file_path)

            # Extract text
            await processing_msg.edit_text("📝 Extracting text content...")
            text_lines = await self.file_processor.extract_text_from_file(file_path)

            if not text_lines:
                await processing_msg.edit_text("❌ No text content found in the document.")
                return

            # Translate text
            await processing_msg.edit_text(f"🔄 Translating {len(text_lines)} lines of text...")
            translated_pairs = await self.translator.translate_lines(text_lines)

            # Generate output document
            await processing_msg.edit_text("📋 Generating translated document...")
            output_path = self.config.get_temp_file_path(f"translated_{uuid.uuid4().hex}.docx")
            temp_files.append(output_path)

            await self.document_generator.create_bilingual_document(
                translated_pairs,
                output_path,
                document.file_name
            )

            # Send the document
            await processing_msg.edit_text("📤 Sending translated document...")

            with open(output_path, 'rb') as doc_file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=doc_file,
                    filename=f"translated_{document.file_name}.docx",
                    caption="✅ Translation completed! Your bilingual document is ready."
                )

            # Delete the processing message
            await processing_msg.delete()

            # Update rate limiter
            self.rate_limiter.record_processing(user_id)

            logger.info(f"Successfully processed document for user {user_id}")

        except Exception as e:
            logger.error(f"Document processing failed for user {user_id}: {e}")
            await processing_msg.edit_text(
                f"❌ Processing failed: {str(e)}\n\nPlease try again or contact support."
            )
        finally:
            # Clean up temporary files
            await self.cleanup_manager.cleanup_files(temp_files)

    async def _download_file(self, document, context) -> Path:
        """Download the uploaded file to temporary storage."""
        try:
            # Generate unique filename
            file_extension = Path(document.file_name).suffix
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = self.config.get_temp_file_path(unique_filename)

            # Download file
            file_obj = await context.bot.get_file(document.file_id)
            await file_obj.download_to_drive(file_path)

            logger.info(f"Downloaded file: {document.file_name} -> {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"File download failed: {e}")
            raise Exception("Failed to download file")

    def _validate_document(self, document) -> bool:
        """Validate the uploaded document."""
        try:
            # Check file size
            if document.file_size > self.config.MAX_FILE_SIZE:
                return False

            # Check file extension
            file_extension = Path(document.file_name).suffix.lower()
            if file_extension not in self.config.SUPPORTED_FORMATS:
                return False

            return True

        except Exception as e:
            logger.error(f"Document validation failed: {e}")
            return False

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages."""
        try:
            await update.message.reply_text(
                "📄 Please send me a PDF or Word document to translate.\n\n"
                "Use /help for more information about supported formats."
            )
        except Exception as e:
            logger.error(f"Error handling text message: {e}")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle bot errors."""
        try:
            logger.error(f"Bot error: {context.error}")

            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ An unexpected error occurred. Please try again later."
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

    async def dev_api_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Developer command to check the status of all configured API keys."""
        user = update.effective_user
        if not self.can_use_dev_commands(user.id):
            await update.message.reply_text("❌ غير مصرح لك باستخدام هذا الأمر.")
            return

        status_message = "Checking API key statuses...\n\n"
        all_keys = self.translator_manager.get_all_keys()

        if not all_keys:
            status_message += "No API keys configured."
        else:
            for i, key in enumerate(all_keys):
                try:
                    # Use the manager to check status of each key
                    key_status = await self.translator_manager.check_key_status(key)
                    status_message += f"Key {i+1}: {key[:4]}...{key[-4:]} - {key_status}\n"
                except Exception as e:
                    status_message += f"Key {i+1}: {key[:4]}...{key[-4:]} - Error checking status: {str(e)}\n"

        await update.message.reply_text(status_message)

    async def dev_add_key_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Developer command to add a new API key."""
        user = update.effective_user
        if not self.can_use_dev_commands(user.id):
            await update.message.reply_text("❌ غير مصرح لك باستخدام هذا الأمر.")
            return

        if not context.args:
            await update.message.reply_text("الاستخدام: /dev_add_key <مفتاح_API_الجديد>")
            return

        new_key = context.args[0]
        if self.translator_manager.add_key(new_key):
            # Update config with the new key (this might need persistence)
            self.config.GEMINI_API_KEYS.append(new_key)
            await update.message.reply_text(f"API key {new_key[:4]}...{new_key[-4:]} added successfully.")
        else:
            await update.message.reply_text("Failed to add API key. It might already exist or be invalid.")

    async def dev_remove_key_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dev_remove_key command - Remove an API key (developer only)."""
        try:
            user_id = update.effective_user.id
            if user_id not in self.config.DEVELOPER_IDS:
                await update.message.reply_text("❌ هذا الأمر مخصص للمطورين فقط")
                return

            if not context.args:
                await update.message.reply_text("❌ يرجى تحديد اسم المفتاح\nمثال: `/dev_remove_key Secondary_2`")
                return

            key_name = context.args[0]
            success = multi_api_manager.remove_api_key(key_name)

            if success:
                await update.message.reply_text(f"✅ تم حذف المفتاح: {key_name}")
            else:
                await update.message.reply_text(f"❌ لم يتم العثور على المفتاح: {key_name}")

        except Exception as e:
            logger.error(f"Error in dev_remove_key command: {e}")
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def dev_db_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dev_db_stats command - Show database statistics (developer only)."""
        try:
            user_id = update.effective_user.id
            if user_id not in self.config.DEVELOPER_IDS:
                await update.message.reply_text("❌ هذا الأمر مخصص للمطورين فقط")
                return

            stats = await db_manager.get_admin_statistics()

            # Format API usage by service
            api_usage_text = ""
            for service in stats['api_usage_by_service']:
                api_usage_text += f"• {service['api_service']}: {service['usage_count']} طلب (متوسط الاستجابة: {service['avg_response_time']:.1f}ms)\n"

            # Format top users
            top_users_text = ""
            for user in stats['top_users'][:5]:
                username = user['username'] or f"User_{user['user_id']}"
                top_users_text += f"• {username}: {user['files_translated']} ملف\n"

            message = f"""
📊 **إحصائيات قاعدة البيانات**

👥 **المستخدمون:**
• إجمالي المسجلين: {stats['total_users']}
• نشطون (24 ساعة): {stats['active_users_24h']}

📝 **الترجمات (آخر 30 يوم):**
• إجمالي الملفات: {stats['translation_stats'].get('total_translations', 0)}
• إجمالي الأسطر: {stats['translation_stats'].get('total_lines', 0)}
• متوسط وقت المعالجة: {stats['translation_stats'].get('avg_processing_time', 0):.1f}s

🔧 **استخدام API (آخر 24 ساعة):**
{api_usage_text or "لا توجد بيانات"}

🏆 **أكثر المستخدمين نشاطاً:**
{top_users_text or "لا توجد بيانات"}
            """

            await update.message.reply_text(message)

        except Exception as e:
            logger.error(f"Error in dev_db_stats command: {e}")
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def dev_user_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dev_user_info command - Get detailed user information (developer only)."""
        try:
            user_id = update.effective_user.id
            if user_id not in self.config.DEVELOPER_IDS:
                await update.message.reply_text("❌ هذا الأمر مخصص للمطورين فقط")
                return

            if not context.args:
                await update.message.reply_text("❌ يرجى تحديد معرف المستخدم\nمثال: `/dev_user_info 123456789`")
                return

            try:
                target_user_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً")
                return

            stats = await db_manager.get_user_statistics(target_user_id)

            if not stats:
                await update.message.reply_text("❌ المستخدم غير موجود في قاعدة البيانات")
                return

            user_info = stats['user_info']
            translation_stats = stats['translation_stats']
            rate_limits = stats['rate_limits']

            message = f"""
👤 **معلومات المستخدم {target_user_id}**

📋 **البيانات الأساسية:**
• الاسم: {user_info.get('first_name', '')} {user_info.get('last_name', '') or ''}
• اسم المستخدم: @{user_info.get('username', 'غير محدد')}
• تاريخ التسجيل: {user_info.get('created_at', '').strftime('%Y-%m-%d %H:%M') if user_info.get('created_at') else 'غير محدد'}
• آخر نشاط: {user_info.get('last_activity', '').strftime('%Y-%m-%d %H:%M') if user_info.get('last_activity') else 'غير محدد'}

📊 **إحصائيات الترجمة:**
• إجمالي الملفات: {translation_stats.get('total_translations', 0)}
• إجمالي الأسطر المترجمة: {translation_stats.get('total_lines_translated', 0)}
• متوسط وقت المعالجة: {translation_stats.get('avg_processing_time', 0):.1f}s

⏱️ **الحدود الحالية:**
• استخدام ساعي: {rate_limits.get('hourly_count', 0)}/10
• استخدام يومي: {rate_limits.get('daily_count', 0)}/50
• الحالة: {'محظور' if rate_limits.get('is_blocked') else 'نشط'}
            """

            await update.message.reply_text(message)

        except Exception as e:
            logger.error(f"Error in dev_user_info command: {e}")
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def dev_block_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dev_block_user command - Block a user (developer only)."""
        try:
            user_id = update.effective_user.id
            if user_id not in self.config.DEVELOPER_IDS:
                await update.message.reply_text("❌ هذا الأمر مخصص للمطورين فقط")
                return

            if len(context.args) < 2:
                await update.message.reply_text("❌ يرجى تحديد معرف المستخدم والسبب\nمثال: `/dev_block_user 123456789 spam`")
                return

            try:
                target_user_id = int(context.args[0])
                reason = " ".join(context.args[1:])
            except ValueError:
                await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً")
                return

            await db_manager.block_user(target_user_id, reason, user_id)
            await update.message.reply_text(f"✅ تم حظر المستخدم {target_user_id}\nالسبب: {reason}")

        except Exception as e:
            logger.error(f"Error in dev_block_user command: {e}")
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def dev_unblock_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dev_unblock_user command - Unblock a user (developer only)."""
        try:
            user_id = update.effective_user.id
            if user_id not in self.config.DEVELOPER_IDS:
                await update.message.reply_text("❌ هذا الأمر مخصص للمطورين فقط")
                return

            if not context.args:
                await update.message.reply_text("❌ يرجى تحديد معرف المستخدم\nمثال: `/dev_unblock_user 123456789`")
                return

            try:
                target_user_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً")
                return

            await db_manager.unblock_user(target_user_id, user_id)
            await update.message.reply_text(f"✅ تم إلغاء حظر المستخدم {target_user_id}")

        except Exception as e:
            logger.error(f"Error in dev_unblock_user command: {e}")
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    def is_bot_owner(self, user_id: int) -> bool:
        """Check if the user is the bot owner."""
        return user_id == self.config.BOT_OWNER_ID

    def is_admin(self, user_id: int) -> bool:
        """Check if the user is an admin."""
        return user_id in self.config.ADMIN_IDS

    def is_developer(self, user_id: int) -> bool:
        """Check if the user is a developer."""
        return user_id in self.config.DEVELOPER_IDS

    def can_use_dev_commands(self, user_id: int) -> bool:
        """Check if user can use developer commands."""
        return self.is_bot_owner(user_id) or self.is_developer(user_id)

    def can_view_all_users(self, user_id: int) -> bool:
        """Check if user can view all users status."""
        return self.is_bot_owner(user_id) or self.is_admin(user_id)


def register_handlers(application):
    """Register all bot handlers."""
    from config import Config

    config = Config()
    bot_handlers = BotHandlers(config)

    # Add handlers to application
    application.add_handler(CommandHandler("start", bot_handlers.start_command))
    application.add_handler(CommandHandler("help", bot_handlers.help_command))
    application.add_handler(CommandHandler("status", bot_handlers.status_command))
    application.add_handler(CommandHandler("commands", bot_handlers.commands_command))
    application.add_handler(CommandHandler("font_size", bot_handlers.font_size_command))

    # Document handler
    application.add_handler(MessageHandler(filters.Document.ALL, bot_handlers.handle_document))
    # Text message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.handle_text_message))

    # Callback query handler for format selection
    application.add_handler(CallbackQueryHandler(bot_handlers.handle_format_selection, pattern='^(bilingual_word|bilingual_pdf)$'))

    # Error handler
    application.add_error_handler(bot_handlers.error_handler)

    # Developer commands
    application.add_handler(CommandHandler("dev_api_status", bot_handlers.dev_api_status_command))
    application.add_handler(CommandHandler("dev_add_key", bot_handlers.dev_add_key_command))
    application.add_handler(CommandHandler("dev_remove_key", bot_handlers.dev_remove_key_command))
    application.add_handler(CommandHandler("dev_db_stats", bot_handlers.dev_db_stats_command))
    application.add_handler(CommandHandler("dev_user_info", bot_handlers.dev_user_info_command))
    application.add_handler(CommandHandler("dev_block_user", bot_handlers.dev_block_user_command))
    application.add_handler(CommandHandler("dev_unblock_user", bot_handlers.dev_unblock_user_command))