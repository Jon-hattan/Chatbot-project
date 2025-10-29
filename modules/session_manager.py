from langchain_core.chat_history import InMemoryChatMessageHistory
from typing import Dict, Any, Optional
from collections import deque
import time

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
                "last_intent": None,
                "collected_booking_data": {},  # Progressive booking data collection
                "human_message_count": 0,  # Track when to trigger extraction
                "rate_limit": {
                    "message_timestamps": deque(maxlen=20),  # Last 20 message times
                    "warned": False,
                    "blocked": False,
                    "block_timestamp": None,
                    "violation_count": 0
                }
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

    def get_collected_data(self, session_id: str) -> Dict[str, Any]:
        """
        Get the progressively collected booking data for a session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            Dictionary of collected booking fields
        """
        return self.get_state(session_id).get("collected_booking_data", {})

    def update_collected_data(self, session_id: str, new_data: Dict[str, Any]):
        """
        Update collected booking data for a session (merges with existing).

        Args:
            session_id: Unique identifier for the session
            new_data: New data to merge into collected data
        """
        state = self.get_state(session_id)
        existing = state.get("collected_booking_data", {})
        # Merge: new_data takes priority but doesn't overwrite with empty values
        merged = {**existing, **{k: v for k, v in new_data.items() if v}}
        state["collected_booking_data"] = merged
        self.set_state(session_id, state)

    def increment_message_count(self, session_id: str) -> int:
        """
        Increment and return the human message count.

        Args:
            session_id: Unique identifier for the session

        Returns:
            Updated message count
        """
        state = self.get_state(session_id)
        count = state.get("human_message_count", 0) + 1
        state["human_message_count"] = count
        self.set_state(session_id, state)
        return count

    def check_rate_limit(self, session_id: str, config: dict) -> Optional[str]:
        """
        Check if user is rate limited and return warning/block message if needed.

        Args:
            session_id: Unique identifier for the session
            config: Rate limiting configuration dict

        Returns:
            None if OK to proceed, or message string if rate limited
        """
        if not config.get("enabled", False):
            return None

        state = self.get_state(session_id)
        rate_state = state["rate_limit"]
        current_time = time.time()

        # Check if user is blocked
        if rate_state["blocked"]:
            block_time = rate_state["block_timestamp"]
            block_duration = config.get("block_duration", 300)

            # Check if block duration has passed
            if current_time - block_time < block_duration:
                return config["messages"]["blocked"]
            else:
                # Block expired, reset state
                self.reset_rate_limit(session_id)

        # Record current message timestamp
        rate_state["message_timestamps"].append(current_time)

        # Count messages in time window
        time_window = config.get("time_window", 10)
        cutoff_time = current_time - time_window
        recent_messages = sum(1 for ts in rate_state["message_timestamps"] if ts > cutoff_time)

        max_messages = config.get("max_messages", 5)
        warning_threshold = config.get("warning_threshold", 4)

        # Check for violation
        if recent_messages >= max_messages:
            if not rate_state["warned"]:
                # First violation - warn
                rate_state["warned"] = True
                rate_state["violation_count"] += 1
                self.set_state(session_id, state)
                return config["messages"]["warning"]
            else:
                # Already warned - block
                rate_state["blocked"] = True
                rate_state["block_timestamp"] = current_time
                rate_state["violation_count"] += 1
                self.set_state(session_id, state)
                return config["messages"]["blocked"]

        # Check for warning threshold (proactive warning)
        if recent_messages >= warning_threshold and not rate_state["warned"]:
            rate_state["warned"] = True
            self.set_state(session_id, state)
            return config["messages"]["warning"]

        # All good
        return None

    def reset_rate_limit(self, session_id: str):
        """Reset rate limiting state for a session."""
        state = self.get_state(session_id)
        state["rate_limit"] = {
            "message_timestamps": deque(maxlen=20),
            "warned": False,
            "blocked": False,
            "block_timestamp": None,
            "violation_count": state["rate_limit"].get("violation_count", 0)  # Keep count
        }
        self.set_state(session_id, state)

    def is_blocked(self, session_id: str) -> bool:
        """Check if a session is currently blocked."""
        state = self.get_state(session_id)
        return state["rate_limit"]["blocked"]

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
