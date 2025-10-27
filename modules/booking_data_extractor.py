import re
from datetime import datetime
from typing import Dict, Optional, List
from langchain_core.messages import HumanMessage, AIMessage


class BookingDataExtractor:
    """
    Extracts booking data from conversational AI responses.
    Now fully configurable via business_profile.yaml!
    """

    def __init__(self, config: dict, llm=None):
        """
        Initialize extractor with configuration.

        Args:
            config: Business configuration dict containing booking_fields section
            llm: Optional LLM for intelligent extraction (hybrid mode)
        """
        self.config = config
        self.llm = llm
        booking_config = config.get("booking_fields", {})

        # Load configuration
        self.summary_indicators = booking_config.get("summary_indicators", ["Booking Details:", "📝"])
        self.confirmation_triggers = booking_config.get("confirmation_triggers", ["BOOKING_CONFIRMED"])
        self.fields = booking_config.get("fields", [])
        self.essential_fields = booking_config.get("essential_fields", [])

        # Progressive collection settings
        conversation_config = config.get("conversation", {})
        self.progressive_collection = conversation_config.get("progressive_data_collection", True)
        self.extraction_method = conversation_config.get("extraction_method", "hybrid")

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

    def extract_from_conversation(self, messages: List, existing_data: Dict[str, str]) -> Dict[str, str]:
        """
        Extract booking data progressively from conversation history (hybrid approach).

        This method is called periodically (every N messages) to extract partial booking
        information as the conversation progresses.

        Args:
            messages: List of conversation messages (HumanMessage, AIMessage)
            existing_data: Previously collected data (won't be overwritten unless empty)

        Returns:
            Dictionary with newly extracted fields
        """
        if not self.progressive_collection:
            return {}

        extracted = {}

        # PHASE 1: REGEX EXTRACTION (Fast - always run for clear patterns)
        regex_data = self._extract_with_regex(messages, existing_data)
        extracted.update(regex_data)

        # PHASE 2: LLM EXTRACTION (Accurate - only for missing ambiguous fields)
        if self.extraction_method in ["llm", "hybrid"] and self.llm:
            # Identify fields still missing after regex
            missing_fields = self._get_missing_fields(existing_data, extracted)

            if missing_fields:
                llm_data = self._extract_with_llm(messages, missing_fields)
                extracted.update(llm_data)

        return extracted

    def _extract_with_regex(self, messages: List, existing_data: Dict[str, str]) -> Dict[str, str]:
        """Extract clear patterns using regex (phone, email)."""
        extracted = {}

        # Combine all messages into text
        text_parts = []
        for msg in messages:
            if isinstance(msg, (HumanMessage, AIMessage)):
                text_parts.append(msg.content)
        full_text = " ".join(text_parts)

        # Extract phone number (Singapore: 8 digits or +65 format)
        if not existing_data.get("Contact"):
            phone_pattern = r'(?:\+65\s?)?[689]\d{7}'
            phone_match = re.search(phone_pattern, full_text)
            if phone_match:
                extracted["Contact"] = phone_match.group(0).strip()

        # Extract email
        if not existing_data.get("Email"):
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_match = re.search(email_pattern, full_text)
            if email_match:
                extracted["Email"] = email_match.group(0).strip()

        return extracted

    def _extract_with_llm(self, messages: List, missing_fields: List[str]) -> Dict[str, str]:
        """Extract ambiguous fields using LLM (names, ages, timeslots, dates)."""
        if not self.llm or not missing_fields:
            return {}

        # Build conversation text
        conversation_text = ""
        for msg in messages:
            if isinstance(msg, HumanMessage):
                conversation_text += f"User: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                conversation_text += f"Bot: {msg.content}\n"

        # Build prompt for LLM
        fields_list = ", ".join(missing_fields)
        prompt = f"""Extract booking information from this conversation snippet.

Only extract the following fields if they are clearly mentioned: {fields_list}

Conversation:
{conversation_text}

Return ONLY a valid JSON object with the extracted fields. Use these exact field names: {', '.join(missing_fields)}
If a field is not found, omit it from the JSON.
Do not include any explanation, only the JSON object.

Example format:
{{"Parent Name": "Sarah", "Child Age": "8"}}"""

        try:
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            # Parse JSON
            import json
            extracted = json.loads(result_text)

            # Only return fields that were requested and have non-empty values
            return {k: v for k, v in extracted.items() if k in missing_fields and v}

        except Exception as e:
            print(f"Warning: LLM extraction failed: {e}")
            return {}

    def _get_missing_fields(self, existing_data: Dict[str, str], newly_extracted: Dict[str, str]) -> List[str]:
        """Identify which fields are still missing."""
        # Fields that might be extractable progressively (not auto-generated)
        extractable_fields = [
            "Parent Name", "Child Name", "Child Age",
            "Contact", "Email", "Timeslot", "Date", "Location"
        ]

        missing = []
        for field in extractable_fields:
            # Check if field is not in existing data and not just extracted
            if not existing_data.get(field) and not newly_extracted.get(field):
                missing.append(field)

        return missing
