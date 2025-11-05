from typing import Tuple, Optional
from modules.response_schema import ValidationRequest
from modules.date_parser import DateParser
from modules.date_validator import DateValidator


class ValidationExecutor:
    """
    Executes validation requests from the LLM.

    The LLM decides when validations are needed and provides the parameters.
    This class executes the validations and returns success/failure with error messages.
    """

    def __init__(self, date_parser: DateParser, date_validator: DateValidator):
        """
        Initialize the validation executor.

        Args:
            date_parser: DateParser instance for parsing dates
            date_validator: DateValidator instance for validating dates
        """
        self.date_parser = date_parser
        self.date_validator = date_validator

    def execute(self, validation: ValidationRequest) -> Tuple[bool, Optional[str]]:
        """
        Execute a validation request.

        Args:
            validation: ValidationRequest from LLM

        Returns:
            Tuple of (success: bool, error_message: str or None)
            - success: True if validation passed, False if failed
            - error_message: None if passed, error description if failed
        """
        if validation.type == "validate_date":
            return self._validate_date(validation.params)
        else:
            # Unknown validation type - skip it
            print(f"⚠️ Unknown validation type: {validation.type}")
            return True, None

    def _validate_date(self, params: dict) -> Tuple[bool, Optional[str]]:
        """
        Validate that a date matches the timeslot day.

        Args:
            params: Dictionary with keys:
                - date: User's date input (e.g., "20 nov", "15th November 2024")
                - timeslot: Chosen timeslot (e.g., "Friday 3-4pm")

        Returns:
            (success, error_message)
        """
        date_str = params.get("date")
        timeslot = params.get("timeslot")

        if not date_str or not timeslot:
            print("⚠️ Date validation missing parameters")
            return True, None  # Skip validation if params missing

        # Parse the date using DateParser
        parsed_date, readable_date, needs_clarification = self.date_parser.parse_date(date_str)

        if needs_clarification:
            # Date is vague or unclear
            error_msg = self._format_date_error(
                "unclear",
                timeslot,
                f"I couldn't parse '{date_str}'. Please provide an explicit date (e.g., '21 Nov 2025' or '21/11/2025')."
            )
            print(f"📅 Validation: Date '{date_str}' needs clarification")
            return False, error_msg

        if not parsed_date:
            # Could not parse date at all
            error_msg = self._format_date_error(
                "invalid",
                timeslot,
                f"I couldn't understand the date '{date_str}'. Please provide a valid date format."
            )
            print(f"📅 Validation: Could not parse '{date_str}'")
            return False, error_msg

        # Validate the parsed date against timeslot
        is_valid, validation_error = self.date_validator.validate_date(parsed_date, timeslot)

        if is_valid:
            print(f"✅ Validation: Date '{date_str}' ({readable_date}) is valid for {timeslot}")
            return True, None
        else:
            # Validation failed - date doesn't match timeslot day or is in past
            error_msg = self._format_date_error("mismatch", timeslot, validation_error)
            print(f"❌ Validation: {validation_error}")
            return False, error_msg

    def _format_date_error(self, error_type: str, timeslot: str, base_error: str) -> str:
        """
        Format a user-friendly error message for date validation failures.

        Args:
            error_type: "unclear", "invalid", or "mismatch"
            timeslot: The chosen timeslot (e.g., "Friday 3-4pm")
            base_error: Base error message from validator

        Returns:
            Formatted error message
        """
        # Extract day from timeslot (e.g., "Friday" from "Friday 3-4pm")
        day = timeslot.split()[0] if timeslot else "the chosen day"

        if error_type == "mismatch":
            # Date doesn't match the day or is in the past
            return f"\n\n⚠️ {base_error} Please provide a date that falls on {day}."
        elif error_type == "unclear":
            # Vague date like "next Friday"
            return f"\n\n⚠️ {base_error}"
        else:  # invalid
            # Couldn't parse the date
            return f"\n\n⚠️ {base_error}"
