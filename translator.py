"""
Translation module using Local Dictionary.
Handles English to Arabic translation using internal dictionary.
"""

import logging
import asyncio
from typing import List, Tuple
import os

# Import the local translator as the primary translation method
from local_translator import LocalTranslator

logger = logging.getLogger(__name__)


class LocalDictionaryTranslator:
    """Handles translation using internal dictionary approach."""

    def __init__(self):
        """
        Initialize the local dictionary translator.
        """
        self.local_translator = LocalTranslator()
        
    async def translate_lines(self, lines: List[str]) -> List[Tuple[str, str]]:
        """
        Translate text using local dictionary approach.

        Args:
            lines: List of English text lines to translate

        Returns:
            List of tuples containing (original_text, translated_text)

        Raises:
            Exception: If translation fails
        """
        try:
            logger.info(f"Translating {len(lines)} lines using local dictionary")
            return await self.local_translator.translate_lines(lines)

        except Exception as e:
            logger.error(f"Local translation failed: {e}")
            raise Exception(f"Local translation service error: {str(e)}")

    async def translate_single_line(self, text: str) -> str:
        """Translate a single line of text using local dictionary."""
        if not text or text.strip() == "":
            return ""
            
        try:
            translated = await self.local_translator.translate_text(text)
            return translated
        except Exception as e:
            logger.error(f"Single line translation failed: {e}")
            return text

    def _create_smart_chunks(self, lines: List[str]) -> List[List[str]]:
        """Create smart text chunks for better translation context."""
        chunks = []
        current_chunk = []
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line - end current chunk if it has content
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                continue
            
            current_chunk.append(line)
            
            # End chunk on these conditions:
            # 1. Sentence ending punctuation
            # 2. Chunk gets too long (more than 5 lines)
            if (line.endswith(('.', '!', '?', ':')) or 
                len(current_chunk) >= 5):
                chunks.append(current_chunk)
                current_chunk = []
        
        # Add remaining lines
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    async def _translate_chunk_with_math_preservation(self, chunk: List[str]) -> List[Tuple[str, str]]:
        """Translate a chunk while preserving structure."""
        try:
            # Combine chunk into paragraph for better context
            combined_text = " ".join(chunk)
            
            # Translate the combined text
            translated_text = await self.local_translator.translate_text(combined_text)
            
            # Create pairs - one pair per chunk for better formatting
            original_combined = " ".join(chunk)
            return [(original_combined, translated_text)]
            
        except Exception as e:
            logger.error(f"Chunk translation failed: {e}")
            # Return original text if translation fails
            original_combined = " ".join(chunk)
            return [(original_combined, original_combined)]
