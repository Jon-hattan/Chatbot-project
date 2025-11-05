"""
Logging utilities for the chatbot system.

Provides timestamped, colored logging for different operations.
"""

from datetime import datetime
from typing import Optional


def log(message: str, emoji: str = "ℹ️", end: str = "\n"):
    """
    Print a timestamped log message.

    Args:
        message: The message to log
        emoji: Emoji prefix for the message
        end: String to append at end (default newline)
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {emoji} {message}", end=end, flush=True)


def log_llm_call(operation: str, char_count: int):
    """Log an LLM call with character count."""
    log(f"Sending to LLM for {operation} ({char_count:,} chars)...", "📤")


def log_llm_response(operation: str, duration: float):
    """Log an LLM response with duration."""
    log(f"LLM responded for {operation} ({duration:.2f}s)", "✅")


def log_validation(validator_type: str, params: dict):
    """Log a validation operation."""
    log(f"Validating: {validator_type} with params {params}", "🔍")


def log_validation_result(success: bool, error: Optional[str] = None):
    """Log validation result."""
    if success:
        log("Validation passed", "✅")
    else:
        log(f"Validation failed: {error}", "❌")


def log_action(action_type: str):
    """Log an action execution."""
    log(f"Executing action: {action_type}", "⚡")


def log_action_result(action_type: str, success: bool, error: Optional[str] = None):
    """Log action execution result."""
    if success:
        log(f"Action completed: {action_type}", "✅")
    else:
        log(f"Action failed: {action_type} - {error}", "❌")


def log_reformulation():
    """Log that response is being reformulated."""
    log("Validation failed - reformulating response", "🔄")


def log_info(message: str):
    """Log general information."""
    log(message, "ℹ️")


def log_warning(message: str):
    """Log a warning."""
    log(message, "⚠️")


def log_error(message: str):
    """Log an error."""
    log(message, "❌")


def log_success(message: str):
    """Log a success."""
    log(message, "✅")


def log_waiting(message: str):
    """Log a waiting state."""
    log(message, "⏳", end="")
    # Print without newline so we can update on same line
