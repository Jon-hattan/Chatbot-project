"""
Action Executor - Executes actions requested by the LLM.

Actions are operations like extracting booking data or writing to Google Sheets.
Actions are only executed after all validators pass successfully.
"""

from typing import Dict, Any, Optional
from modules.response_schema import ActionRequest


class ActionExecutor:
    """
    Executes actions requested by the LLM in structured JSON responses.

    Supported actions:
    - extract_booking_data: Extract booking information from conversation
    - book_to_sheets: Write confirmed booking to Google Sheets
    - update_booking_state: Update the booking state tracker (timeslot, date, confirmations, etc.)
    """

    def __init__(self, booking_data_extractor, google_sheets_agent, session_manager):
        """
        Initialize action executor with required dependencies.

        Args:
            booking_data_extractor: BookingDataExtractor instance
            google_sheets_agent: GoogleSheetsAgent instance
            session_manager: SessionManager instance for accessing session data
        """
        self.booking_data_extractor = booking_data_extractor
        self.google_sheets_agent = google_sheets_agent
        self.session_manager = session_manager

    def execute(self, action: ActionRequest, session_id: str) -> Dict[str, Any]:
        """
        Execute the requested action.

        Args:
            action: ActionRequest with type and params
            session_id: Session identifier for accessing conversation history

        Returns:
            Dictionary with:
                - success: bool
                - result: Any data returned by the action
                - error: Optional error message
        """
        if action.type == "extract_booking_data":
            return self._extract_booking_data(session_id, action.params)
        elif action.type == "book_to_sheets":
            return self._book_to_sheets(session_id, action.params)
        elif action.type == "update_booking_state":
            return self._update_booking_state(session_id, action.params)
        else:
            return {
                "success": False,
                "error": f"Unknown action type: {action.type}"
            }

    def _extract_booking_data(self, session_id: str, params: Dict) -> Dict[str, Any]:
        """
        Extract booking data from conversation history.

        This replaces the progressive extraction that used to run every N messages.
        Now the LLM decides when to extract data.

        Args:
            session_id: Session identifier
            params: Action parameters (currently unused)

        Returns:
            Result dictionary with extracted data
        """
        try:
            # Get conversation history
            messages = self.session_manager.get_history(session_id).messages

            # Get existing collected data
            collected_data = self.session_manager.get_collected_data(session_id)

            # Extract new data using LLM
            extracted_data = self.booking_data_extractor.extract_from_conversation(
                messages,
                collected_data
            )

            # Update session with newly extracted data
            if extracted_data:
                self.session_manager.update_collected_data(session_id, extracted_data)

            return {
                "success": True,
                "result": {
                    "extracted": extracted_data,
                    "total_collected": {**collected_data, **extracted_data}
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to extract booking data: {str(e)}"
            }

    def _book_to_sheets(self, session_id: str, params: Dict) -> Dict[str, Any]:
        """
        Write confirmed booking to Google Sheets.

        This replaces the "BOOKING_CONFIRMED" string trigger.
        Now the LLM explicitly requests booking via structured action.

        Args:
            session_id: Session identifier
            params: Action parameters. Can optionally include 'booking_data' dict,
                   otherwise uses pending_booking_data from session

        Returns:
            Result dictionary indicating success/failure
        """
        try:
            # Get booking data from params or session
            booking_data = params.get("booking_data")

            if not booking_data:
                # Use pending booking data from session state
                state = self.session_manager.get_state(session_id)
                booking_data = state.get('pending_booking_data')

            if not booking_data:
                return {
                    "success": False,
                    "error": "No booking data available to write to sheets"
                }

            # Write to Google Sheets
            self.google_sheets_agent.write_row(booking_data)

            # Clear pending booking data after successful write
            state = self.session_manager.get_state(session_id)
            state['pending_booking_data'] = None
            self.session_manager.set_state(session_id, state)

            return {
                "success": True,
                "result": {
                    "message": "Booking successfully written to Google Sheets",
                    "booking_data": booking_data
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to book to sheets: {str(e)}"
            }

    def _update_booking_state(self, session_id: str, params: Dict) -> Dict[str, Any]:
        """
        Update the booking state tracker.

        This replaces implicit state tracking. The LLM explicitly calls this action
        to update booking state whenever new information is confirmed (timeslot chosen,
        date validated, trial accepted, etc.).

        Args:
            session_id: Session identifier
            params: State updates. Can include:
                - timeslot: str (e.g., "Saturday 3-4pm")
                - date: str (e.g., "28/11/2024")
                - date_confirmed: bool
                - trial_accepted: bool
                - stage: str (e.g., "browsing", "selecting_timeslot", "scheduling_date", "collecting_info", "confirming")

        Returns:
            Result dictionary indicating success/failure
        """
        try:
            # Get current session state
            state = self.session_manager.get_state(session_id)
            booking_state = state.get("booking_state", {})

            # Update booking state with provided params
            # Only update fields that are provided in params
            if "timeslot" in params:
                booking_state["timeslot"] = params["timeslot"]
            if "date" in params:
                booking_state["date"] = params["date"]
            if "date_confirmed" in params:
                booking_state["date_confirmed"] = params["date_confirmed"]
            if "trial_accepted" in params:
                booking_state["trial_accepted"] = params["trial_accepted"]
            if "stage" in params:
                booking_state["stage"] = params["stage"]

            # Save updated booking state back to session
            state["booking_state"] = booking_state
            self.session_manager.set_state(session_id, state)

            return {
                "success": True,
                "result": {
                    "message": "Booking state updated successfully",
                    "booking_state": booking_state
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to update booking state: {str(e)}"
            }
