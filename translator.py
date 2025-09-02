
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
        Translate text by smart chunking instead of line-by-line.
        Preserves mathematical expressions and symbols.

        Args:
            lines: List of English text lines to translate

        Returns:
            List of tuples containing (original_text, translated_text)

        Raises:
            Exception: If translation fails
        """
        try:
            # Smart chunking - group lines into meaningful text blocks
            chunks = self._create_smart_chunks(lines)
            translated_pairs = []

            for chunk in chunks:
                chunk_results = await self._translate_chunk_with_math_preservation(chunk)
                translated_pairs.extend(chunk_results)
                
                # Small delay between chunks
                await asyncio.sleep(0.3)

            logger.info(f"Successfully translated {len(translated_pairs)} text segments")
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
            # 3. Mathematical equation detected (standalone)
            if (line.endswith(('.', '!', '?', ':')) or 
                len(current_chunk) >= 5 or
                self._is_mathematical_line(line)):
                chunks.append(current_chunk)
                current_chunk = []
        
        # Add remaining lines
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def _is_mathematical_line(self, line: str) -> bool:
        """Check if line contains mathematical expressions."""
        import re
        math_patterns = [
            r'\$.*?\$',  # LaTeX math
            r'\\[a-zA-Z]+',  # LaTeX commands
            r'[=∫∑∏∆∇±≤≥≠∞∪∩⊂⊃∈∉∀∃]',  # Math symbols
            r'\b\d+[+\-*/=]\d+',  # Basic equations
            r'[xyz]\s*[=+\-*/]\s*\d+',  # Variables with operations
            r'\b(sin|cos|tan|log|ln|exp|sqrt)\(',  # Math functions
        ]
        
        return any(re.search(pattern, line) for pattern in math_patterns)

    def _extract_math_expressions(self, text: str) -> Tuple[str, dict]:
        """Extract mathematical expressions and replace with placeholders."""
        import re
        
        math_expressions = {}
        modified_text = text
        
        # Pattern for various math expressions
        patterns = [
            (r'\$[^$]+\$', 'LATEX_MATH'),  # LaTeX inline math
            (r'\$\$[^$]+\$\$', 'LATEX_BLOCK'),  # LaTeX block math
            (r'\\[a-zA-Z]+\{[^}]*\}', 'LATEX_CMD'),  # LaTeX commands
            (r'\b\d+\s*[+\-*/=×÷]\s*\d+(?:\s*[+\-*/=×÷]\s*\d+)*', 'EQUATION'),  # Equations
            (r'[xyz]\s*[=+\-*/]\s*[\d\w\s+\-*/]+', 'ALGEBRA'),  # Algebraic expressions
        ]
        
        placeholder_counter = 0
        
        for pattern, expr_type in patterns:
            matches = re.finditer(pattern, modified_text)
            for match in matches:
                placeholder = f"__MATH_EXPR_{placeholder_counter}__"
                math_expressions[placeholder] = match.group()
                modified_text = modified_text.replace(match.group(), placeholder, 1)
                placeholder_counter += 1
        
        return modified_text, math_expressions

    def _restore_math_expressions(self, text: str, math_expressions: dict) -> str:
        """Restore mathematical expressions from placeholders."""
        for placeholder, original_expr in math_expressions.items():
            text = text.replace(placeholder, original_expr)
        return text

    async def _translate_chunk_with_math_preservation(self, chunk: List[str]) -> List[Tuple[str, str]]:
        """Translate a chunk while preserving mathematical expressions."""
        async with self.semaphore:
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    # Get API key from manager
                    api_key = multi_api_manager.get_current_api_key()
                    if not api_key:
                        api_key = self.fallback_api_key
                    
                    if api_key != self.current_api_key:
                        genai.configure(api_key=api_key)
                        self.current_api_key = api_key

                    # Combine chunk into paragraph for better context
                    combined_text = " ".join(chunk)
                    
                    # Extract mathematical expressions
                    text_without_math, math_expressions = self._extract_math_expressions(combined_text)
                    
                    # Prepare translation prompt
                    prompt = f"""Translate the following English text to Arabic. 
Keep mathematical expressions, formulas, equations, and symbols EXACTLY as they appear.
Do not translate mathematical terms, variable names, or scientific notation.
Preserve the natural flow and meaning of the text:

{text_without_math}

Important: Maintain paragraph structure and do not add line numbers."""

                    model = genai.GenerativeModel(self.model)
                    response = await asyncio.wait_for(
                        asyncio.to_thread(model.generate_content, prompt),
                        timeout=45
                    )

                    if response and response.text:
                        translated_text = response.text.strip()
                        
                        # Restore mathematical expressions
                        translated_text = self._restore_math_expressions(translated_text, math_expressions)
                        
                        # Create pairs - one pair per chunk for better formatting
                        original_combined = " ".join(chunk)
                        return [(original_combined, translated_text)]
                    else:
                        raise Exception("No response from API")

                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                        multi_api_manager.mark_key_failed(api_key, "API limit reached")
                        if attempt == max_retries - 1:
                            # Use local translator as final fallback
                            from local_translator import local_translator
                            result = []
                            for line in chunk:
                                translated = await local_translator.translate_text(line)
                                result.append((line, translated))
                            return result
                    else:
                        logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            # Use local translator as final fallback
                            from local_translator import local_translator
                            result = []
                            for line in chunk:
                                translated = await local_translator.translate_text(line)
                                result.append((line, translated))
                            return result
                    
                    await asyncio.sleep(1)

            # Return original text if all attempts fail
            return [(line, line) for line in chunk]

    async def translate_single_line(self, text: str) -> str:
        """Translate a single line of text with math preservation."""
        if not text or text.strip() == "":
            return ""
            
        try:
            # Extract and preserve math
            text_without_math, math_expressions = self._extract_math_expressions(text)
            
            # Translate only if there's actual text to translate
            if text_without_math.strip():
                result = await self._translate_chunk_with_math_preservation([text])
                translated = result[0][1] if result else text
                return self._restore_math_expressions(translated, math_expressions)
            else:
                # If only math expressions, return original
                return text
        except Exception as e:
            logger.error(f"Single line translation failed: {e}")
            return text
