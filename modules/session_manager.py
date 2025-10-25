from langchain_core.chat_history import InMemoryChatMessageHistory
from typing import Dict, Any, Optional

class SessionManager:
    """Manages per-session chat histories and conversation state."""

    def __init__(self, window_size: int = 3):
        """
        Initialize the session manager.

        Args:
            window_size: Maximum number of message exchanges to keep in history
        """
        self.sessions = {}
        self.session_states = {}  # Track conversation state for each session
        self.window_size = window_size

    def get_history(self, session_id: str) -> InMemoryChatMessageHistory:
        """
        Return or create a chat history for a given session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            Chat history object for the session
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = InMemoryChatMessageHistory()
        return self.sessions[session_id]

    def trim_history(self, session_id: str):
        """
        Keep only the last k exchanges in history.

        Args:
            session_id: Unique identifier for the session
        """
        history = self.sessions.get(session_id)
        if history and self.window_size:
            # Trims the message list manually
            messages = history.messages[-self.window_size * 2:]
            history.messages = messages

    def get_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get the current state for a session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            State dictionary for the session
        """
        if session_id not in self.session_states:
            self.session_states[session_id] = {
                "awaiting_confirmation": False,
                "pending_data": None,
                "last_intent": None
            }
        return self.session_states[session_id]

    def set_state(self, session_id: str, state: Dict[str, Any]):
        """
        Update the state for a session.

        Args:
            session_id: Unique identifier for the session
            state: New state dictionary
        """
        self.session_states[session_id] = state

    def set_awaiting_confirmation(self, session_id: str, pending_data: Dict[str, Any]):
        """
        Mark session as awaiting confirmation and store pending data.

        Args:
            session_id: Unique identifier for the session
            pending_data: Data to be logged if user confirms
        """
        state = self.get_state(session_id)
        state["awaiting_confirmation"] = True
        state["pending_data"] = pending_data
        state["last_intent"] = True
        self.set_state(session_id, state)

    def clear_confirmation_state(self, session_id: str):
        """
        Clear the confirmation state after user responds.

        Args:
            session_id: Unique identifier for the session
        """
        state = self.get_state(session_id)
        state["awaiting_confirmation"] = False
        state["pending_data"] = None
        self.set_state(session_id, state)

    def is_awaiting_confirmation(self, session_id: str) -> bool:
        """
        Check if session is awaiting confirmation.

        Args:
            session_id: Unique identifier for the session

        Returns:
            True if awaiting confirmation, False otherwise
        """
        return self.get_state(session_id).get("awaiting_confirmation", False)

    def get_pending_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get pending data for a session awaiting confirmation.

        Args:
            session_id: Unique identifier for the session

        Returns:
            Pending data dict or None
        """
        return self.get_state(session_id).get("pending_data")

    def clear_session(self, session_id: str):
        """
        Clear all data for a session.

        Args:
            session_id: Unique identifier for the session
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.session_states:
            del self.session_states[session_id]
