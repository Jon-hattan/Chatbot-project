class ResponseGenerator:
    """Generates contextual responses based on conversation state and config."""

    def __init__(self, config: dict):
        """
        Initialize the response generator with business configuration.

        Args:
            config: Business profile configuration dict with response templates
        """
        self.config = config

    def get_confirmation_request(self, name: str) -> str:
        """
        Generate a confirmation request message.

        Args:
            name: User's name

        Returns:
            Confirmation request message
        """
        template = self.config.get("reply_on_intent_detected",
                                   "Hi {name}! I noticed you're interested. Should I register your information?")
        return template.format(name=name)

    def get_success_response(self, name: str) -> str:
        """
        Generate a success response after confirmation.

        Args:
            name: User's name

        Returns:
            Success message
        """
        template = self.config.get("reply_on_success",
                                   "Great {name}! Your information has been recorded.")
        return template.format(name=name)

    def get_rejection_response(self, name: str) -> str:
        """
        Generate a response when user rejects confirmation.

        Args:
            name: User's name

        Returns:
            Rejection acknowledgment message
        """
        template = self.config.get("reply_on_rejection",
                                   "No problem {name}! Let me know if you change your mind.")
        return template.format(name=name)

    def get_neutral_response(self, name: str) -> str:
        """
        Generate a neutral response when no intent is detected.

        Args:
            name: User's name

        Returns:
            Neutral conversation message
        """
        template = self.config.get("reply_on_neutral",
                                   "Hey {name}! How can I help you today?")
        return template.format(name=name)

    def get_unclear_response(self, name: str) -> str:
        """
        Generate a response when confirmation answer is unclear.

        Args:
            name: User's name

        Returns:
            Clarification request message
        """
        template = self.config.get("reply_on_unclear",
                                   "Sorry {name}, I didn't quite understand. Could you please confirm with yes or no?")
        return template.format(name=name)
