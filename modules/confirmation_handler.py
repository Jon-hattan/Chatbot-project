class ConfirmationHandler:
    """Handles user confirmation flow for detected intents."""

    def __init__(self, confirmation_keywords: dict = None):
        """
        Initialize the confirmation handler.

        Args:
            confirmation_keywords: Dict with 'positive' and 'negative' keyword lists
                                  If None, uses default keywords
        """
        self.keywords = confirmation_keywords or {
            "positive": ["yes", "yeah", "yep", "sure", "ok", "okay", "confirm", "correct", "right", "absolutely", "definitely"],
            "negative": ["no", "nope", "nah", "cancel", "stop", "never mind", "nevermind", "not interested"]
        }

    def is_confirmation(self, message: str) -> bool:
        """
        Check if message is a positive confirmation.

        Args:
            message: User's response to confirmation request

        Returns:
            True if positive confirmation, False otherwise
        """
        message_lower = message.lower().strip()

        # Check for positive keywords
        for keyword in self.keywords["positive"]:
            if keyword in message_lower:
                return True

        return False

    def is_rejection(self, message: str) -> bool:
        """
        Check if message is a negative confirmation (rejection).

        Args:
            message: User's response to confirmation request

        Returns:
            True if rejection, False otherwise
        """
        message_lower = message.lower().strip()

        # Check for negative keywords
        for keyword in self.keywords["negative"]:
            if keyword in message_lower:
                return True

        return False

    def get_response_type(self, message: str) -> str:
        """
        Determine the type of response: confirmed, rejected, or unclear.

        Args:
            message: User's response to confirmation request

        Returns:
            One of: "confirmed", "rejected", "unclear"
        """
        if self.is_confirmation(message):
            return "confirmed"
        elif self.is_rejection(message):
            return "rejected"
        else:
            return "unclear"
