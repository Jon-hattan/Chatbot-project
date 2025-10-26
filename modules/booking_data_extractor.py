import re
from datetime import datetime
from typing import Dict, Optional, List


class BookingDataExtractor:
    """
    Extracts booking data from conversational AI responses.
    Now fully configurable via business_profile.yaml!
    """

    def __init__(self, config: dict):
        """
        Initialize extractor with configuration.

        Args:
            config: Business configuration dict containing booking_fields section
        """
        self.config = config
        booking_config = config.get("booking_fields", {})

        # Load configuration
        self.summary_indicators = booking_config.get("summary_indicators", ["Booking Details:", "📝"])
        self.confirmation_triggers = booking_config.get("confirmation_triggers", ["BOOKING_CONFIRMED"])
        self.fields = booking_config.get("fields", [])
        self.essential_fields = booking_config.get("essential_fields", [])

        # Build regex patterns for each field
        self._build_field_patterns()

    def _build_field_patterns(self):
        """Build regex patterns from field configuration."""
        self.field_patterns = {}

        for field_config in self.fields:
            field_name = field_config.get("name")
            patterns = field_config.get("patterns", [])
            auto_generate = field_config.get("auto_generate", False)

            if auto_generate:
                # Field is auto-generated (like Timestamp), skip pattern building
                self.field_patterns[field_name] = None
                continue

            if not patterns:
                # If no patterns specified, use field name as pattern
                patterns = [field_name]

            # Build regex: match any of the alternative patterns
            # Pattern format: "Field Name:\s*(.+?)(?:\n|•|$)"
            pattern_alternatives = "|".join([re.escape(p) for p in patterns])
            regex = rf'(?:{pattern_alternatives}):\s*(.+?)(?:\n|•|$)'
            self.field_patterns[field_name] = regex

    def extract_from_summary(self, response_text: str) -> Optional[Dict[str, str]]:
        """
        Extract booking data from confirmation summary.

        Args:
            response_text: The AI's response containing booking details

        Returns:
            Dictionary with extracted booking data, or None if not found
        """
        # Check if this contains a booking summary
        has_indicator = any(indicator in response_text for indicator in self.summary_indicators)
        if not has_indicator:
            return None

        data = {}

        # Extract each field using configured patterns
        for field_config in self.fields:
            field_name = field_config.get("name")
            auto_generate = field_config.get("auto_generate", False)

            if auto_generate:
                # Auto-generate fields (like Timestamp)
                if field_name == "Timestamp":
                    data[field_name] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                continue

            # Extract using regex pattern
            pattern = self.field_patterns.get(field_name)
            if pattern:
                match = re.search(pattern, response_text, re.IGNORECASE)
                if match:
                    data[field_name] = match.group(1).strip()

        # Ensure all required fields exist (with empty string as default)
        for field_config in self.fields:
            field_name = field_config.get("name")
            required = field_config.get("required", False)
            auto_generate = field_config.get("auto_generate", False)

            if required and not auto_generate and field_name not in data:
                data[field_name] = ""

        # Validate essential fields are present
        has_essential = all(
            field in data and data[field]
            for field in self.essential_fields
        )

        if has_essential:
            return data
        else:
            return None

    def is_booking_confirmed(self, response_text: str) -> bool:
        """
        Check if response contains the booking confirmation trigger.

        Args:
            response_text: The AI's response

        Returns:
            True if booking is confirmed
        """
        return any(trigger in response_text for trigger in self.confirmation_triggers)
