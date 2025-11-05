from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class ValidationRequest(BaseModel):
    """
    A validation request that the LLM wants the system to perform.

    Validators check data and return errors if invalid. If validation fails,
    the error is fed back to the LLM to reformulate its response.
    """
    type: Literal["validate_date"] = Field(
        description="Type of validation to perform. Currently supported: 'validate_date'"
    )
    params: dict = Field(
        description="Parameters for the validation. For validate_date: {date: str, timeslot: str}"
    )


class ActionRequest(BaseModel):
    """
    An action request that the LLM wants the system to perform.

    Actions execute operations like extracting booking data or booking to Google Sheets.
    Actions are only executed after all validators pass.
    """
    type: Literal["extract_booking_data", "book_to_sheets", "update_booking_state"] = Field(
        description=(
            "Type of action to perform. "
            "'extract_booking_data': Extract booking information from the conversation. "
            "'book_to_sheets': Write confirmed booking to Google Sheets. "
            "'update_booking_state': Update the booking state tracker (timeslot, date, confirmations, etc.)."
        )
    )
    params: dict = Field(
        default={},
        description=(
            "Parameters for the action. "
            "For extract_booking_data: {} (no params needed). "
            "For book_to_sheets: {booking_data: dict} (optional, uses session data if not provided). "
            "For update_booking_state: {timeslot: str, date: str, date_confirmed: bool, trial_accepted: bool, stage: str}"
        )
    )


class BotResponse(BaseModel):
    """
    Structured response from the conversational LLM.

    The LLM returns:
    1. user_message: The reply to show the user
    2. validators: Validations to perform (errors fed back to LLM if they fail)
    3. actions: Actions to execute after successful validation

    This architecture allows a single LLM call per message while maintaining
    control over validations and actions.
    """
    user_message: str = Field(
        description="The message to display to the user"
    )
    validators: List[ValidationRequest] = Field(
        default=[],
        description=(
            "List of validations to perform BEFORE executing actions. "
            "Use this when you need to validate user input (e.g., date matches timeslot day). "
            "If validation fails, the error will be fed back to you to reformulate your response."
        )
    )
    actions: List[ActionRequest] = Field(
        default=[],
        description=(
            "List of actions to perform AFTER successful validation. "
            "Use 'extract_booking_data' to progressively extract booking information. "
            "Use 'book_to_sheets' when the user confirms their booking."
        )
    )
    booking_summary: Optional[str] = Field(
        default=None,
        description=(
            "Summary of what booking information has been collected from the parent "
            "(e.g., 'Collected: Parent Name (Sarah), Contact (98765432)') "
            "and brief remarks about non-booking topics discussed "
            "(e.g., 'Remarks: Asked about makeup classes, concerned about drop-off time')."
        )
    )
