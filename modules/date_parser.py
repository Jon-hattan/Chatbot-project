import re
from datetime import datetime, timedelta
from typing import Tuple, Optional
from dateutil import parser as date_parser
from zoneinfo import ZoneInfo


class DateParser:
    """
    Hybrid date parser:
    - Explicit dates via comprehensive regex patterns
    - Relative dates via LLM week offset detection
    """

    DAYS_OF_WEEK = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }

    # Full month names
    MONTHS_FULL = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    ]

    # Short month names (3-letter)
    MONTHS_SHORT = [
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "sept", "oct", "nov", "dec"
    ]

    def __init__(self, llm=None):
        """
        Initialize date parser.

        Args:
            llm: Optional LLM for week offset detection
        """
        self.llm = llm
        self._build_month_pattern()

    def _build_month_pattern(self):
        """Build comprehensive month regex pattern."""
        # Combine full and short month names
        all_months = "|".join(self.MONTHS_FULL + self.MONTHS_SHORT)
        self.month_pattern = all_months

    def parse_date(self, user_input: str, reference_date: Optional[datetime] = None) -> Tuple[Optional[datetime], str, bool]:
        """
        Parse date from user input (explicit or relative).

        Args:
            user_input: User's date input
            reference_date: Reference date (defaults to today)

        Returns:
            Tuple of (parsed_date, readable_format, needs_clarification)
            - parsed_date: datetime object or None
            - readable_format: "Friday, 15th November 2024"
            - needs_clarification: True if LLM returned -1 (uncertain)
        """
        if reference_date is None:
            # Use Singapore timezone (UTC+8) for accurate date parsing
            singapore_tz = ZoneInfo("Asia/Singapore")
            reference_date = datetime.now(singapore_tz)

        # STEP 1: Try to find explicit date (comprehensive patterns)
        explicit_date = self._extract_explicit_date(user_input, reference_date)
        if explicit_date:
            readable = self._format_readable(explicit_date)
            return explicit_date, readable, False

        # STEP 2: No explicit date found → Ask for clarification
        # (Removed LLM week offset detection - we only accept explicit dates)
        return None, "", True

    def _extract_explicit_date(self, text: str, reference_date: datetime) -> Optional[datetime]:
        """
        Extract explicit date using comprehensive regex patterns.

        Handles:
        - Full month names: "15th November 2024", "November 15th"
        - Short month names: "15th Nov 2024", "Nov 15th"
        - Numeric formats: "15/11/2024", "15-11-2024"
        - Day-only: "the 15th"

        Returns datetime if found, None otherwise.
        """
        text_lower = text.lower()

        # === PATTERN 1: "15th November 2024" or "15 Nov" (day first) ===
        pattern = rf'\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({self.month_pattern})(?:\s+(\d{{4}}))?\b'
        match = re.search(pattern, text_lower)
        if match:
            try:
                date_str = match.group(0)
                parsed = date_parser.parse(date_str, fuzzy=True, default=reference_date.replace(day=1))
                # If no year specified and date is in the past, assume next year
                if not match.group(3) and parsed < reference_date.replace(hour=0, minute=0, second=0, microsecond=0):
                    parsed = parsed.replace(year=reference_date.year + 1)
                return parsed
            except:
                pass

        # === PATTERN 2: "November 15th 2024" or "Nov 15" (month first) ===
        pattern = rf'\b({self.month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s+(\d{{4}}))?\b'
        match = re.search(pattern, text_lower)
        if match:
            try:
                date_str = match.group(0)
                parsed = date_parser.parse(date_str, fuzzy=True, default=reference_date.replace(day=1))
                # If no year specified and date is in the past, assume next year
                if not match.group(3) and parsed < reference_date.replace(hour=0, minute=0, second=0, microsecond=0):
                    parsed = parsed.replace(year=reference_date.year + 1)
                return parsed
            except:
                pass

        # === PATTERN 3: "15/11/2024" or "15-11-2024" or "15.11.2024" ===
        match = re.search(r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b', text)
        if match:
            try:
                day, month, year = match.groups()
                return datetime(int(year), int(month), int(day))
            except:
                pass

        # === PATTERN 4: "15/11" or "15-11" (without year) ===
        match = re.search(r'\b(\d{1,2})[/\-\.](\d{1,2})(?!\d)\b', text)
        if match:
            try:
                day, month = match.groups()
                year = reference_date.year
                parsed = datetime(year, int(month), int(day))
                # If date is in the past, assume next year
                if parsed < reference_date.replace(hour=0, minute=0, second=0, microsecond=0):
                    parsed = parsed.replace(year=year + 1)
                return parsed
            except:
                pass

        # === PATTERN 5: "the 15th" or "on the 15th" (day-only) ===
        match = re.search(r'\b(?:the|on\s+the)\s+(\d{1,2})(?:st|nd|rd|th)\b', text_lower)
        if match:
            try:
                day = int(match.group(1))
                # Assume current month, or next month if day already passed
                year = reference_date.year
                month = reference_date.month

                parsed = datetime(year, month, day)
                if parsed < reference_date.replace(hour=0, minute=0, second=0, microsecond=0):
                    # Day has passed in current month, try next month
                    month += 1
                    if month > 12:
                        month = 1
                        year += 1
                    parsed = datetime(year, month, day)

                return parsed
            except:
                pass

        return None

    def _llm_detect_week_offset(self, user_input: str, reference_date: datetime) -> Tuple[int, Optional[str]]:
        """
        Use LLM to detect week offset and day name from relative date expression.

        Args:
            user_input: User's input (e.g., "next Friday", "this coming Friday")
            reference_date: Current date

        Returns:
            Tuple of (week_offset, day_name)
            - week_offset: 0 (this week), 1 (next week), 2, 3, ... or -1 (uncertain)
            - day_name: "friday", "monday", etc. or None
        """
        today_str = reference_date.strftime('%A, %d %B %Y')

        prompt = f"""Today is {today_str}.

User said: "{user_input}"

Task: Determine how many weeks in the future the user is referring to, and which day of the week.

Week offset rules:
- 0 = This coming week (e.g., "this Friday", "Friday", "this coming Friday")
- 1 = Next week (e.g., "next Friday")
- 2 = Two weeks from now (e.g., "next next Friday", "the Friday after next")
- 3 = Three weeks from now (e.g., "Friday 3 weeks later")
- -1 = Uncertain or ambiguous (cannot determine)

Day of week: monday, tuesday, wednesday, thursday, friday, saturday, sunday

Return ONLY in this exact format:
week_offset: <number>
day: <day_name>

Examples:
- "this Friday" → week_offset: 0, day: friday
- "next Friday" → week_offset: 1, day: friday
- "next next Friday" → week_offset: 2, day: friday
- "Friday 3 weeks later" → week_offset: 3, day: friday
- "the Friday after next" → week_offset: 2, day: friday
- "in 2 weeks" → week_offset: 2, day: unknown
- "sometime next month" → week_offset: -1, day: unknown

Return ONLY the two lines above. No explanation."""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            # Parse response
            week_offset = -1
            day_name = None

            for line in content.split('\n'):
                if 'week_offset:' in line.lower():
                    try:
                        week_offset = int(re.search(r'-?\d+', line).group(0))
                    except:
                        week_offset = -1
                elif 'day:' in line.lower():
                    match = re.search(r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', line.lower())
                    if match:
                        day_name = match.group(1)

            # If day is unknown but we have week_offset, return -1 (ask for clarification)
            if day_name is None and week_offset != -1:
                return -1, None

            return week_offset, day_name

        except Exception as e:
            print(f"⚠️ LLM week offset detection failed: {e}")
            return -1, None

    def _calculate_date_from_offset(self, day_name: str, week_offset: int, reference_date: datetime) -> Optional[datetime]:
        """
        Calculate date from day name and week offset.

        Args:
            day_name: "friday", "monday", etc.
            week_offset: 0 (this week), 1 (next week), etc.
            reference_date: Current date

        Returns:
            Calculated datetime
        """
        if day_name not in self.DAYS_OF_WEEK:
            return None

        target_day = self.DAYS_OF_WEEK[day_name]
        current_day = reference_date.weekday()

        # Calculate days until target day this week
        days_ahead = target_day - current_day
        if days_ahead <= 0:
            days_ahead += 7  # Go to next week's occurrence

        # Add week offset
        total_days = days_ahead + (week_offset * 7)

        return reference_date + timedelta(days=total_days)

    def _format_readable(self, date: datetime) -> str:
        """Format datetime to readable string: 'Friday, 15th November 2024'"""
        day = date.day
        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        return date.strftime(f"%A, {day}{suffix} %B %Y")
