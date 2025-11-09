import re
from datetime import datetime, timedelta
from typing import Tuple, Optional
from dateutil import parser as date_parser
from zoneinfo import ZoneInfo


class DateValidator:
    """
    Validates and parses dates for booking system.
    Handles relative dates (next Sunday, this Friday) and converts to ddmmyyyy format.
    """

    # Day name mappings
    DAYS_OF_WEEK = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }

    def __init__(self, llm=None):
        """
        Initialize the date validator.

        Args:
            llm: Optional LLM for parsing natural language dates
        """
        self.llm = llm

    def parse_relative_date(self, user_input: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
        """
        Parse various date formats including relative dates.

        Args:
            user_input: User's date input (e.g., "next Sunday", "15th November", "15/11/2025")
            reference_date: Reference date for relative calculations (defaults to today)

        Returns:
            datetime object or None if parsing fails

        Examples:
            "next Sunday" → datetime for next Sunday
            "this Friday" → datetime for upcoming Friday
            "tomorrow" → datetime for tomorrow
            "15th November" → datetime for Nov 15 this year
            "15/11/2025" → datetime for Nov 15, 2025
            "15112025" → datetime for Nov 15, 2025 (ddmmyyyy format)
        """
        if not user_input:
            return None

        if reference_date is None:
            # Use Singapore timezone (UTC+8) for accurate date parsing
            singapore_tz = ZoneInfo("Asia/Singapore")
            reference_date = datetime.now(singapore_tz)

        # Normalize input
        text = user_input.lower().strip()

        # Handle ddmmyyyy format (already standardized) - try first for exact matches
        if re.match(r'^\d{8}$', text):
            try:
                day = int(text[0:2])
                month = int(text[2:4])
                year = int(text[4:8])
                return datetime(year, month, day)
            except ValueError:
                return None

        # Try manual relative date parsing (deterministic, no LLM)
        manual_date = self._parse_relative_manual(text, reference_date)
        if manual_date:
            return manual_date

        # Fallback: Try flexible parsing with dateutil
        try:
            # Parse the date
            parsed = date_parser.parse(text, fuzzy=True, default=reference_date.replace(day=1))

            # If only day and month provided, assume current or next year
            if parsed.year == reference_date.year and parsed < reference_date.replace(hour=0, minute=0, second=0, microsecond=0):
                # Date is in the past this year, assume next year
                parsed = parsed.replace(year=reference_date.year + 1)

            return parsed
        except:
            return None

    def _parse_relative_manual(self, text: str, reference_date: datetime) -> Optional[datetime]:
        """
        Parse relative dates using manual pattern matching (no LLM).

        Args:
            text: Normalized lowercase text
            reference_date: Reference date for calculations

        Returns:
            datetime object or None if not a relative expression
        """
        text_lower = text.lower().strip()

        # Handle "tomorrow"
        if "tomorrow" in text_lower:
            return reference_date + timedelta(days=1)

        # Handle "today"
        if text_lower in ["today", "tdy"]:
            return reference_date

        # Extract day name
        day_name = None
        target_day = None
        for day, day_num in self.DAYS_OF_WEEK.items():
            if day in text_lower:
                day_name = day
                target_day = day_num
                break

        if day_name is None or target_day is None:
            return None

        # Calculate days ahead
        current_day = reference_date.weekday()
        days_ahead = target_day - current_day

        # Determine if "next" or "this/coming"
        if "next" in text_lower and "next week" not in text_lower:
            # "next Friday" = Friday in the week after this coming Friday
            if days_ahead <= 0:
                days_ahead += 7
            days_ahead += 7  # Add another week
        else:
            # "this Friday", "coming Friday", or just "Friday" = next occurrence
            if days_ahead <= 0:
                days_ahead += 7

        return reference_date + timedelta(days=days_ahead)

    def _parse_with_llm(self, user_input: str, reference_date: datetime) -> Optional[datetime]:
        """
        Use LLM to parse natural language date expressions.

        Args:
            user_input: User's natural language date input
            reference_date: Reference date for relative calculations

        Returns:
            datetime object or None if parsing fails
        """
        if not self.llm:
            return None

        # Format reference date for LLM
        today_str = reference_date.strftime('%A, %d %B %Y')

        prompt = f"""Today's date is {today_str}.

User said: "{user_input}"

Parse the date the user is referring to and return it in DD/MM/YYYY format.

Rules:
- "this Friday" or "this coming Friday" = the next upcoming Friday from today
- "next Friday" = the Friday after this coming Friday (one week later than "this Friday")
- "tomorrow" = the day after today
- "next week" = 7 days from today
- For any day name without "this" or "next", assume they mean the next upcoming occurrence of that day

Return ONLY the date in DD/MM/YYYY format, nothing else. No explanation."""

        try:
            response = self.llm.invoke(prompt)
            date_str = response.content.strip()

            # Extract DD/MM/YYYY pattern from response
            match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
            if match:
                day, month, year = match.groups()
                return datetime(int(year), int(month), int(day))

            return None
        except Exception as e:
            print(f"Warning: LLM date parsing failed: {e}")
            return None

    def validate_date(self, date: datetime, timeslot: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that date is in the future and matches the timeslot day.

        Args:
            date: The datetime to validate
            timeslot: The timeslot string (e.g., "Friday 3-4pm", "Saturday 3-4pm")

        Returns:
            Tuple of (is_valid: bool, error_message: str or None)

        Examples:
            validate_date(datetime(2025, 11, 15), "Friday 3-4pm") → (True, None)
            validate_date(datetime(2025, 11, 15), "Saturday 3-4pm") → (False, "Date is Friday but timeslot is Saturday")
        """
        # Use Singapore timezone (UTC+8) for accurate date validation
        singapore_tz = ZoneInfo("Asia/Singapore")
        today = datetime.now(singapore_tz).replace(hour=0, minute=0, second=0, microsecond=0)

        # Check if date is in the future (not today or past)
        if date < today:
            return False, "Date is in the past. Please choose a future date."

        # Extract expected day from timeslot
        expected_day = self._extract_day_from_timeslot(timeslot)

        if not expected_day:
            # If we can't extract day, we can't validate
            return True, None

        # Get actual day of week from date
        actual_day = date.strftime("%A")

        # Check if they match
        if actual_day.lower() != expected_day.lower():
            return False, f"Date is {actual_day} but timeslot is {expected_day}. Please choose a {expected_day}."

        return True, None

    def _extract_day_from_timeslot(self, timeslot: str) -> Optional[str]:
        """
        Extract day name from timeslot string.

        Args:
            timeslot: Timeslot string (e.g., "Friday 3-4pm", "Sunday 12-1pm")

        Returns:
            Day name (e.g., "Friday") or None if not found
        """
        if not timeslot:
            return None

        timeslot_lower = timeslot.lower()

        for day_name in self.DAYS_OF_WEEK.keys():
            if day_name in timeslot_lower:
                return day_name.capitalize()

        return None

    def format_to_standard(self, date: datetime) -> str:
        """
        Convert datetime to standardized ddmmyyyy format.

        Args:
            date: datetime object

        Returns:
            Date string in ddmmyyyy format (e.g., "15112025")
        """
        return date.strftime("%d%m%Y")

    def format_to_readable(self, date: datetime) -> str:
        """
        Convert datetime to human-readable format.

        Args:
            date: datetime object

        Returns:
            Readable date string (e.g., "Friday, 15th November 2025")
        """
        # Get day with ordinal suffix
        day = date.day
        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        return date.strftime(f"%A, {day}{suffix} %B %Y")

    def parse_and_validate(self, user_input: str, timeslot: str, reference_date: Optional[datetime] = None) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        All-in-one: Parse, validate, and format date.

        Args:
            user_input: User's date input
            timeslot: The chosen timeslot
            reference_date: Reference date for relative calculations

        Returns:
            Tuple of (
                is_valid: bool,
                standardized_date: str (ddmmyyyy) or None,
                readable_date: str (human-readable) or None,
                error_message: str or None
            )
        """
        # Parse date
        parsed_date = self.parse_relative_date(user_input, reference_date)

        if not parsed_date:
            return False, None, None, "Could not understand the date format. Please try again (e.g., 'next Sunday', '15th November')."

        # Validate date
        is_valid, error_msg = self.validate_date(parsed_date, timeslot)

        if not is_valid:
            return False, None, None, error_msg

        # Format dates
        standardized = self.format_to_standard(parsed_date)
        readable = self.format_to_readable(parsed_date)

        return True, standardized, readable, None
