#!/usr/bin/env python3
"""
Telegram Bot for PDF/Word Translation
Main entry point for the bot application.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from telegram.ext import Application
from telegram.error import Conflict

# Add this for Render port binding
import http.server
import socketserver
import threading

from config import Config
from bot_handlers import register_handlers
from database_manager import db_manager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variable to track the application
application = None

# Add this for Render port binding
def start_health_server():
    """Start a simple HTTP server for health checks on Render"""
    port = int(os.environ.get('PORT', 8080))
    
    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Healthy')
            else:
                self.send_response(404)
                self.end_headers()
    
    try:
        httpd = socketserver.TCPServer(("", port), HealthHandler)
        logger.info(f"Health check server started on port {port}")
        httpd.serve_forever()
    except Exception as e:
        logger.error(f"Failed to start health check server: {e}")

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, stopping bot...")
    if application:
        # Create a new event loop for shutdown if needed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(shutdown_application())
            else:
                loop.run_until_complete(shutdown_application())
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    sys.exit(0)

async def shutdown_application():
    """Shutdown the application gracefully."""
    global application
    if application:
        try:
            await application.stop()
            await application.shutdown()
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error shutting down application: {e}")

async def main():
    """Main function to start the bot."""
    global application
    
    try:
        # Initialize configuration
        config = Config()

        # Validate required environment variables
        if not config.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Initialize database
        await db_manager.initialize()
        logger.info("Database connection established")

        # Create bot application
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

        # Register all handlers
        register_handlers(application)

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info("Starting Telegram bot...")

        # Start the bot with proper error handling
        try:
            await application.initialize()
            await application.start()
            
            # Start polling with conflict handling (using correct parameters)
            await application.updater.start_polling(
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True,
                timeout=30  # Only use supported timeout parameter
            )
            
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
                
        except Conflict as e:
            logger.error(f"Conflict error: {e}")
            logger.info("Attempting to resolve conflict by waiting and retrying...")
            # Wait for a few seconds and try to recover
            await asyncio.sleep(5)
            # Try to stop the updater and restart
            try:
                if application.updater.running:
                    await application.updater.stop()
            except Exception as stop_error:
                logger.error(f"Error stopping updater: {stop_error}")
            
            # Retry starting the bot
            raise Exception("Conflict detected, restarting bot...")
            
        except asyncio.CancelledError:
            logger.info("Bot polling was cancelled")
        except Exception as e:
            logger.error(f"Error during bot operation: {e}")
            raise
        finally:
            # Clean shutdown
            try:
                if application and application.updater and application.updater.running:
                    await application.updater.stop()
                if application:
                    await application.stop()
                    await application.shutdown()
                await db_manager.close()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

def run_bot():
    """Entry point that properly handles the event loop."""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Start health check server in a separate thread for Render
            health_thread = threading.Thread(target=start_health_server, daemon=True)
            health_thread.start()
            
            # Check if we're in a deployment environment
            if os.getenv("REPLIT_DEPLOYMENT"):
                # Running in deployment mode
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            
            # Use asyncio.new_event_loop() to avoid conflicts
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(main())
                break  # If successful, break out of retry loop
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"Bot attempt {retry_count} failed: {e}")
                if retry_count < max_retries:
                    logger.info(f"Retrying in 10 seconds... ({retry_count}/{max_retries})")
                    time.sleep(10)
                else:
                    logger.error("Max retries reached. Exiting.")
                    sys.exit(1)
            finally:
                # Clean up the loop
                try:
                    pending_tasks = asyncio.all_tasks(loop)
                    for task in pending_tasks:
                        task.cancel()
                    
                    if pending_tasks:
                        loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
                        
                except Exception as e:
                    logger.error(f"Error cleaning up tasks: {e}")
                finally:
                    loop.close()
                    
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Retrying in 10 seconds... ({retry_count}/{max_retries})")
                time.sleep(10)
            else:
                logger.error("Max retries reached. Exiting.")
                sys.exit(1)

if __name__ == "__main__":
    run_bot()