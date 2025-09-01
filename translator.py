
"""
Translation module using Google Gemini API.
Handles English to Arabic translation with proper error handling.
"""

import logging
import asyncio
from typing import List, Tuple
import os

import google.generativeai as genai
from multi_api_manager import multi_api_manager

logger = logging.getLogger(__name__)


class GeminiTranslator:
    """Handles translation using Google Gemini API with multi-key support."""

    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"):
        """
        Initialize the translator.

        Args:
            api_key: Google Gemini API key (fallback, will use multi-key manager)
            model: Gemini model to use for translation
        """
        self.fallback_api_key = api_key
        self.client = genai
        self.model = model
        self.semaphore = asyncio.Semaphore(8)  # Increased concurrent requests for faster processing
        self.current_api_key = None

    async def translate_lines(self, lines: List[str]) -> List[Tuple[str, str]]:
        """
        Translate multiple lines from English to Arabic.

        Args:
            lines: List of English text lines to translate

        Returns:
            List of tuples containing (original_text, translated_text)

        Raises:
            Exception: If translation fails
        """
        try:
            translated_pairs = []

            # Process lines in batches to avoid overwhelming the API
            batch_size = 10
            for i in range(0, len(lines), batch_size):
                batch = lines[i:i + batch_size]
                batch_results = await self._translate_batch(batch)
                translated_pairs.extend(batch_results)

                # Add delay between batches to respect rate limits
                if i + batch_size < len(lines):
                    await asyncio.sleep(0.5)

            logger.info(f"Successfully translated {len(translated_pairs)} lines")
            return translated_pairs

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise Exception(f"Translation service error: {str(e)}")

    async def _translate_batch(self, lines: List[str]) -> List[Tuple[str, str]]:
        """Translate a batch of lines."""
        async with self.semaphore:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # الحصول على مفتاح API من المدير
                    api_key = multi_api_manager.get_current_api_key()
                    if not api_key:
                        api_key = self.fallback_api_key
                    
                    if api_key != self.current_api_key:
                        genai.configure(api_key=api_key)
                        self.current_api_key = api_key
                        logger.info("تم تبديل مفتاح API")

                    # Prepare the prompt for batch translation
                    lines_text = "\n".join([f"{i+1}. {line}" for i, line in enumerate(lines)])
                    
                    prompt = f"""Translate the following English text lines to Arabic. 
Keep the same numbering format and return only the Arabic translations:

{lines_text}"""

                    model = genai.GenerativeModel(self.model)
                    response = await asyncio.wait_for(
                        asyncio.to_thread(model.generate_content, prompt),
                        timeout=30
                    )

                    if response and response.text:
                        # Parse the response and match with original lines
                        translated_lines = response.text.strip().split('\n')
                        result = []
                        
                        for i, original_line in enumerate(lines):
                            if i < len(translated_lines):
                                # Remove numbering from translated line
                                translated = translated_lines[i]
                                # Remove number prefix if exists
                                if f"{i+1}." in translated:
                                    translated = translated.split(f"{i+1}.", 1)[1].strip()
                                result.append((original_line, translated))
                            else:
                                result.append((original_line, original_line))  # Fallback
                        
                        return result
                    else:
                        raise Exception("No response from API")

                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                        multi_api_manager.mark_key_failed(api_key, "API limit reached")
                        if attempt == max_retries - 1:
                            # Use local translator as final fallback
                            from local_translator import local_translator
                            result = await local_translator.translate_lines(batch)
                            return result
                    else:
                        logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            # Use local translator as final fallback
                            from local_translator import local_translator
                            result = await local_translator.translate_lines(batch)
                            return result
                    
                    await asyncio.sleep(1)

            # Return original text if all attempts fail
            return [(line, line) for line in lines]

    async def translate_single_line(self, text: str) -> str:
        """Translate a single line of text."""
        if not text or text.strip() == "":
            return ""
            
        try:
            result = await self._translate_batch([text])
            return result[0][1] if result else text
        except Exception as e:
            logger.error(f"Single line translation failed: {e}")
            return text
