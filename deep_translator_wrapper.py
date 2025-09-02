"""
Deep Translator Wrapper
Wrapper for the deep-translator library to provide translation services as an alternative to local dictionary
"""

import logging
import asyncio
from typing import List, Tuple
from deep_translator import GoogleTranslator
import re

logger = logging.getLogger(__name__)


class DeepTranslatorWrapper:
    """Wrapper for deep-translator library to provide translation services."""

    def __init__(self):
        """Initialize the Deep Translator wrapper."""
        self.translator = GoogleTranslator(source='en', target='ar')
        
    async def translate_text(self, text: str) -> str:
        """
        Translate text from English to Arabic using deep-translator.
        
        Args:
            text: English text to translate
            
        Returns:
            Translated Arabic text
        """
        if not text or not text.strip():
            return text
            
        try:
            # Preserve mathematical expressions
            text_without_math, math_expressions = self._extract_math_expressions(text)
            
            # Translate the text
            translated = await asyncio.get_event_loop().run_in_executor(
                None, self.translator.translate, text_without_math
            )
            
            # Restore mathematical expressions
            if math_expressions:
                translated = self._restore_math_expressions(translated, math_expressions)
            
            return translated
            
        except Exception as e:
            logger.error(f"Deep translation failed: {e}")
            # Return original text if translation fails
            return text

    async def translate_lines(self, lines: List[str]) -> List[Tuple[str, str]]:
        """
        Translate multiple lines of text.
        
        Args:
            lines: List of English text lines to translate
            
        Returns:
            List of tuples containing (original_text, translated_text)
        """
        translated_pairs = []
        
        for line in lines:
            if line.strip():
                translated = await self.translate_text(line)
                translated_pairs.append((line, translated))
            else:
                translated_pairs.append((line, ""))
        
        return translated_pairs

    def _extract_math_expressions(self, text: str) -> Tuple[str, dict]:
        """Extract mathematical expressions and replace with placeholders."""
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

    async def translate_single_line(self, text: str) -> str:
        """Translate a single line of text."""
        if not text or text.strip() == "":
            return ""
            
        try:
            translated = await self.translate_text(text)
            return translated
        except Exception as e:
            logger.error(f"Single line translation failed: {e}")
            return text


# Global instance
deep_translator = DeepTranslatorWrapper()