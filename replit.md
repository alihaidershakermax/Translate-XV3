# PDF/Word Translation Bot

## Overview

This project is a Telegram bot that translates PDF and Word documents from English to Arabic using Google's Gemini AI API. The bot accepts document uploads, extracts text content, translates it using AI, and returns a formatted bilingual Word document containing both the original English text and Arabic translations side-by-side.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Components

**Bot Framework**: Built using the `python-telegram-bot` library for handling Telegram API interactions, command processing, and file uploads. The bot uses an event-driven architecture with separate handlers for different message types and commands.

**File Processing Pipeline**: A modular file processor that extracts text from PDF files using `pdfplumber` and Word documents using `python-docx`. The system supports `.pdf`, `.doc`, and `.docx` formats with configurable file size limits (20MB default).

**Translation Engine**: Integrates with Google's Gemini AI API for English-to-Arabic translation. Uses batch processing to handle large documents efficiently and implements concurrent request limiting through semaphores to respect API rate limits.

**Document Generation**: Creates formatted bilingual Word documents using `python-docx`, presenting original English text alongside Arabic translations in a structured format with proper styling and layout.

**Resource Management**: Implements comprehensive file cleanup mechanisms and rate limiting to prevent resource exhaustion. Includes automatic cleanup of temporary files and per-user rate limiting (10 files per hour default).

### Design Patterns

**Configuration Management**: Centralized configuration class that handles environment variables, file paths, and application settings with validation.

**Asynchronous Processing**: Fully async/await architecture to handle multiple concurrent users and prevent blocking operations during file processing and translation.

**Error Handling**: Comprehensive error handling with proper logging at each stage of the pipeline, ensuring graceful degradation when services are unavailable.

**Modular Architecture**: Clear separation of concerns with dedicated modules for file handling, translation, document generation, and utility functions.

## External Dependencies

**Telegram Bot API**: Primary interface for user interactions, file uploads, and message delivery through the official Telegram bot platform.

**Google Gemini AI API**: Core translation service requiring API key authentication. Uses the `google-genai` client library for making translation requests.

**File Processing Libraries**: 
- `pdfplumber` for PDF text extraction
- `python-docx` for Word document reading and generation

**Python Standard Libraries**: Extensive use of `asyncio` for concurrency, `pathlib` for file system operations, `logging` for monitoring, and `tempfile` for temporary file management.

**Environment Configuration**: Relies on environment variables for sensitive configuration like API keys and bot tokens, with fallback defaults for development settings.