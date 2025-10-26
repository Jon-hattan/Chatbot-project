from datetime import datetime
from typing import Dict, Any, Optional
from modules.intent_detector import IntentDetector
from modules.confirmation_handler import ConfirmationHandler
from modules.response_generator import ResponseGenerator
from modules.session_manager import SessionManager
from modules.google_sheets_agent import GoogleSheetsAgent
from modules.conversation_agent import ConversationAgent
from modules.booking_data_extractor import BookingDataExtractor

class ModularChatbot:
    """
    Modular chatbot that detects intent, asks for confirmation, logs to Google Sheets,
    and provides natural conversational responses.
    """

    def __init__(
        self,
        intent_detector: IntentDetector,
        config: dict,
        sheet_agent: GoogleSheetsAgent,
        session_manager: SessionManager = None,
        confirmation_handler: ConfirmationHandler = None,
        conversation_agent: Optional[ConversationAgent] = None
    ):
        """
        Initialize the modular chatbot.

        Args:
            intent_detector: Intent detection module
            config: Business configuration dict
            sheet_agent: Google Sheets logging agent
            session_manager: Session management module (optional, creates default)
            confirmation_handler: Confirmation handling module (optional, creates default)
            conversation_agent: Conversational AI module (optional, if None uses generic responses)
        """
        self.intent_detector = intent_detector
        self.config = config
        self.sheet_agent = sheet_agent
        self.session_manager = session_manager or SessionManager()
        self.confirmation_handler = confirmation_handler or ConfirmationHandler()
        self.response_generator = ResponseGenerator(config)
        self.conversation_agent = conversation_agent
        self.data_extractor = BookingDataExtractor()

    def process_message(
        self,
        session_id: str,
        name: str,
        handle: str,
        message: str
    ) -> str:
        """
        Process a user message through the modular chatbot pipeline.

        Flow:
        1. Detect special cases (performance, private class) → Route to human
        2. Otherwise, let conversational AI handle everything (browsing + booking)

        Args:
            session_id: Unique identifier for the conversation session
            name: User's name
            handle: User's Instagram handle or identifier
            message: User's message text

        Returns:
            Bot's response message
        """
        # Detect special cases that need human escalation
        special_case_detected = self.intent_detector.detect(message)

        if special_case_detected:
            # Special case - route to human
            return self._handle_special_case(session_id, name, message)

        # Normal conversation - let conversational AI handle it
        if self.conversation_agent:
            response = self.conversation_agent.get_response(session_id, message)

            # Check if response contains a booking summary (store it for later)
            booking_data = self.data_extractor.extract_from_summary(response)
            if booking_data:
                # Store in session state for when confirmation happens
                state = self.session_manager.get_state(session_id)
                state['pending_booking_data'] = booking_data
                self.session_manager.set_state(session_id, state)

            # Check if booking was confirmed
            if self.data_extractor.is_booking_confirmed(response):
                # Retrieve stored booking data
                state = self.session_manager.get_state(session_id)
                stored_booking_data = state.get('pending_booking_data')

                if stored_booking_data:
                    # Log to Google Sheets
                    self.sheet_agent.write_row(stored_booking_data)
                    # Clear stored data
                    state['pending_booking_data'] = None
                    self.session_manager.set_state(session_id, state)
                    print(f"✅ Booking logged to Google Sheets for {stored_booking_data.get('Parent Name', 'Unknown')}")

            return response
        else:
            # Fallback if no conversation agent
            return self.response_generator.get_neutral_response(name)

    def _handle_special_case(self, session_id: str, name: str, message: str) -> str:
        """
        Handle special cases that need human escalation.

        Args:
            session_id: Unique identifier for the conversation session
            name: User's name
            message: User's message

        Returns:
            Escalation message
        """
        # Check if it's a performance or private class enquiry
        message_lower = message.lower()

        if any(word in message_lower for word in ["performance", "event", "party", "hire", "booking", "show", "corporate"]):
            # Performance enquiry
            return "Let me connect you with our artist manager Ryan who handles performances! 🎤 He'll be in touch with you shortly via WhatsApp. 😊"
        elif any(word in message_lower for word in ["private", "1-on-1", "one-on-one", "individual"]):
            # Private class enquiry
            return "Great! For private 1-on-1 classes, we'll need to discuss your specific needs and schedule. 😊 A team member will contact you via WhatsApp to arrange the details!"
        else:
            # Generic escalation
            return "I'll connect you with our team who can help you with this! They'll be in touch via WhatsApp shortly. 😊"

    def clear_session(self, session_id: str):
        """
        Clear all session data for a user.

        Args:
            session_id: Unique identifier for the conversation session
        """
        self.session_manager.clear_session(session_id)
