from datetime import datetime
from typing import Dict, Any, Optional
from modules.intent_detector import IntentDetector
from modules.session_manager import SessionManager
from modules.google_sheets_agent import GoogleSheetsAgent
from modules.conversation_agent import ConversationAgent
from modules.booking_data_extractor import BookingDataExtractor
import os
import asyncio

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
        conversation_agent: Optional[ConversationAgent] = None,
        llm = None,
        bot_application = None
    ):
        """
        Initialize the modular chatbot.

        Args:
            intent_detector: Intent detection module
            config: Business configuration dict
            sheet_agent: Google Sheets logging agent
            session_manager: Session management module (optional, creates default)
            conversation_agent: Conversational AI module (optional, if None uses generic responses)
            llm: LLM instance for progressive data extraction
            bot_application: Telegram bot application instance for sending messages
        """
        self.intent_detector = intent_detector
        self.config = config
        self.sheet_agent = sheet_agent
        self.session_manager = session_manager or SessionManager()
        self.conversation_agent = conversation_agent
        self.data_extractor = BookingDataExtractor(config, llm=llm)
        self.llm = llm
        self.bot_application = bot_application

    async def process_message(
        self,
        session_id: str,
        name: str,
        handle: str,
        message: str,
        user_username: str = None
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
            user_username: User's Telegram username (optional)

        Returns:
            Bot's response message
        """
        # Detect special cases that need human escalation
        special_case_detected = self.intent_detector.detect(message)

        if special_case_detected:
            # Special case - route to human
            return await self._handle_special_case(session_id, name, message, user_username)

        # Normal conversation - let conversational AI handle it
        if self.conversation_agent:
            # Increment human message counter
            human_msg_count = self.session_manager.increment_message_count(session_id)

            # PROGRESSIVE DATA COLLECTION: Extract booking data BEFORE generating response
            # This ensures extracted data is available when bot decides what to ask next
            window_size = self.session_manager.window_size
            if human_msg_count % window_size == 0:
                # Time to extract! Process current conversation window
                history = self.session_manager.get_history(session_id)
                existing_data = self.session_manager.get_collected_data(session_id)

                # Extract new data from conversation
                new_data = self.data_extractor.extract_from_conversation(
                    messages=history.messages,
                    existing_data=existing_data
                )

                # Merge and update collected data
                if new_data:
                    self.session_manager.update_collected_data(session_id, new_data)
                    print(f"📊 Extracted at message {human_msg_count}: {new_data}")

            # NOW generate response (with updated collected data in context)
            response = self.conversation_agent.get_response(session_id, message)

            # Check if response contains a booking summary (store it for later)
            booking_data = self.data_extractor.extract_from_summary(response)
            if booking_data:
                # Store in session state for when confirmation happens
                # This keeps data safe even if user gives tentative response
                # (e.g., "let me check with my child first")
                # Merge with progressively collected data
                collected = self.session_manager.get_collected_data(session_id)
                merged_data = {**collected, **booking_data}  # booking_data takes priority

                state = self.session_manager.get_state(session_id)
                state['pending_booking_data'] = merged_data
                self.session_manager.set_state(session_id, state)

            # Check if booking was confirmed
            # Note: BOOKING_CONFIRMED will only appear if user gives clear confirmation
            # The LLM is instructed NOT to use this trigger for tentative responses
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
            # Fallback if no conversation agent (should rarely happen)
            return "Hello! I'm currently unable to process messages. Please try again later."

    async def _notify_moderator(self, session_id: str, user_name: str, user_username: str, escalation_type: str, message: str):
        """
        Notify the moderator about a human escalation.

        Args:
            session_id: Unique identifier for the conversation session
            user_name: User's display name
            user_username: User's Telegram username
            escalation_type: Type of escalation (performance/private/generic)
            message: User's original message
        """
        if not self.bot_application:
            print("⚠️ Warning: Cannot notify moderator - bot application not available")
            return

        moderator_chat_id = os.getenv("MODERATOR_CHAT_ID")
        if not moderator_chat_id:
            print("⚠️ Warning: MODERATOR_CHAT_ID not set in .env")
            print("   Add your bot to a group and use /groupid to get the chat ID")
            return

        # Convert to integer (group chat IDs are negative numbers)
        try:
            chat_id = int(moderator_chat_id)
        except ValueError:
            print(f"❌ Error: MODERATOR_CHAT_ID must be a number, got: {moderator_chat_id}")
            return

        # Generate chat summary
        history = self.session_manager.get_history(session_id)
        messages = history.messages[-10:]  # Get last 10 messages for context

        # Create a brief summary
        if len(messages) > 0:
            conversation_context = "\n".join([
                f"{'User' if i % 2 == 0 else 'Bot'}: {msg.content[:100]}..."
                if len(msg.content) > 100 else f"{'User' if i % 2 == 0 else 'Bot'}: {msg.content}"
                for i, msg in enumerate(messages[-6:])  # Last 6 messages
            ])
        else:
            conversation_context = "No prior conversation history"

        # Determine what's needed based on escalation type
        if escalation_type == "performance":
            needed_from_human = "Handle performance/event inquiry - connect with artist manager Ryan"
        elif escalation_type == "private":
            needed_from_human = "Discuss private 1-on-1 class arrangements and scheduling"
        else:
            needed_from_human = "General inquiry that requires human assistance"

        # Get collected data if any
        collected_data = self.session_manager.get_collected_data(session_id)
        data_summary = ""
        if collected_data:
            data_summary = "\n\n**Collected Info:**\n" + "\n".join([f"• {k}: {v}" for k, v in collected_data.items()])

        # Format username with @
        user_handle = f"@{user_username}" if user_username else f"User ID: {session_id}"

        # Compose notification message
        notification = f"""🚨 **Human Escalation Required**

**User:** {user_name} ({user_handle})

**Reason:** {escalation_type.title()} Inquiry

**Latest Message:**
"{message}"

**Conversation Summary:**
{conversation_context}
{data_summary}

**Action Needed:**
{needed_from_human}

---
*Please contact this user via WhatsApp or Telegram to assist them.*"""

        try:
            # Send notification to moderator/group
            await self.bot_application.bot.send_message(
                chat_id=chat_id,
                text=notification,
                parse_mode="Markdown"
            )
            print(f"✅ Moderator notification sent to chat {chat_id} for {user_handle}")
        except Exception as e:
            print(f"❌ Failed to send moderator notification: {e}")
            print(f"   Make sure the bot is added to the group/chat with ID {chat_id}")

    async def _handle_special_case(self, session_id: str, name: str, message: str, user_username: str = None) -> str:
        """
        Handle special cases that need human escalation.

        Args:
            session_id: Unique identifier for the conversation session
            name: User's name
            message: User's message
            user_username: User's Telegram username (optional)

        Returns:
            Escalation message
        """
        # Check if it's a performance or private class enquiry
        message_lower = message.lower()

        escalation_type = "generic"
        if any(word in message_lower for word in ["performance", "event", "party", "hire", "booking", "show", "corporate"]):
            escalation_type = "performance"
            response = "Let me connect you with our artist manager Ryan who handles performances! 🎤 He'll be in touch with you shortly via WhatsApp. 😊"
        elif any(word in message_lower for word in ["private", "1-on-1", "one-on-one", "individual"]):
            escalation_type = "private"
            response = "Great! For private 1-on-1 classes, we'll need to discuss your specific needs and schedule. 😊 A team member will contact you via WhatsApp to arrange the details!"
        else:
            response = "I'll connect you with our team who can help you with this! They'll be in touch via WhatsApp shortly. 😊"

        # Notify moderator
        if self.bot_application:
            await self._notify_moderator(session_id, name, user_username or "unknown", escalation_type, message)

        return response

    def clear_session(self, session_id: str):
        """
        Clear all session data for a user.

        Args:
            session_id: Unique identifier for the conversation session
        """
        self.session_manager.clear_session(session_id)
