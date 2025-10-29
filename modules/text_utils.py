"""
Utility functions for text processing.
"""

import re


def strip_think_tags(text: str) -> str:
    """
    Remove Qwen3's <think> reasoning tags from text.

    Qwen3-32B outputs internal reasoning in <think>...</think> tags
    which should be removed before displaying to users.

    Args:
        text: The text containing potential <think> tags

    Returns:
        Cleaned text without <think> tags

    Examples:
        >>> strip_think_tags("Hello <think>some reasoning</think> world")
        'Hello world'
        >>> strip_think_tags("No tags here")
        'No tags here'
    """
    if not text:
        return text

    # Remove everything between <think> and </think> tags (including multiline)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Clean up any extra whitespace left behind
    # Replace multiple newlines with double newline
    text = re.sub(r'\n\n+', '\n\n', text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text
