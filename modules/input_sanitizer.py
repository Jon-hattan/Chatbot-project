"""
Input Sanitizer - Prevents prompt injection attacks.

This module detects and blocks common prompt injection patterns
to protect the system from malicious user input.
"""

import re
from typing import Optional


class InputSanitizer:
    """Sanitize user input to prevent prompt injection attacks."""

    # Common prompt injection patterns to detect
    SUSPICIOUS_PATTERNS = [
        r'ignore\s+(all\s+)?previous\s+instructions',
        r'ignore\s+(all\s+)?prior\s+instructions',
        r'disregard\s+(all\s+)?previous',
        r'forget\s+(all\s+)?previous',
        r'system\s*(message|prompt|instructions?)',
        r'you\s+are\s+now',
        r'act\s+as',
        r'pretend\s+to\s+be',
        r'forget\s+everything',
        r'disregard',
        r'\[INTERNAL\s*NOTE',
        r'\[COLLECTED\s*INFO',
        r'\[SYSTEM\]',
        r'---\s*SYSTEM',
        r'===\s*SYSTEM',
        r'BOOKING_CONFIRMED',
        r'repeat\s+your\s+(instructions?|prompt|rules)',
        r'what\s+(are|were)\s+your\s+instructions',
        r'show\s+me\s+your\s+(prompt|instructions|rules)',
        r'reveal\s+your\s+(prompt|instructions|system)',
        r'tell\s+me\s+your\s+(prompt|instructions|rules)',
        r'admin\s+mode',
        r'developer\s+(mode|access)',
        r'debug\s+mode',
        r'test\s+mode',
        r'override',
        r'bypass',
        r'USER\s+MESSAGE\s+(START|END)',
        r'===\s*USER\s+MESSAGE',
    ]

    def __init__(self, max_length: int = 500):
        """
        Initialize the input sanitizer.

        Args:
            max_length: Maximum allowed message length
        """
        self.max_length = max_length
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.SUSPICIOUS_PATTERNS
        ]

    def is_safe(self, text: str) -> bool:
        """
        Check if input is safe from prompt injection.

        Args:
            text: User input to check

        Returns:
            True if input is safe, False if suspicious
        """
        if not text:
            return True

        # Check for suspicious patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                # Found a suspicious pattern
                matched = pattern.pattern
                print(f"⚠️ Prompt injection pattern detected: {matched}")
                return False

        return True

    def sanitize(self, text: str) -> str:
        """
        Sanitize user input by removing potentially harmful content.

        Args:
            text: User input to sanitize

        Returns:
            Sanitized text

        Note: This should only be called after is_safe() returns True.
        For unsafe input, block it entirely rather than trying to sanitize.
        """
        if not text:
            return text

        # Remove markdown code blocks that could be used for injection
        text = text.replace("```", "")

        # Remove excessive markdown formatting
        text = re.sub(r'\*\*+', '', text)  # Remove bold
        text = re.sub(r'__+', '', text)    # Remove underline

        # Limit length
        if len(text) > self.max_length:
            text = text[:self.max_length]
            print(f"⚠️ Input truncated to {self.max_length} characters")

        # Remove multiple newlines (could be used for delimiter injection)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove null bytes and other control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')

        return text.strip()

    def get_blocked_message(self) -> str:
        """
        Get a friendly message to show when input is blocked.

        Returns:
            User-friendly error message
        """
        return "I'm sorry, I can't process that message. Please rephrase your question. 😊"
