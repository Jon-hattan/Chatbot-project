import re
from datetime import datetime
from typing import Dict, Optional

class BookingDataExtractor:
    """Extracts booking data from conversational AI responses."""

    def extract_from_summary(self, response_text: str) -> Optional[Dict[str, str]]:
        """
        Extract booking data from confirmation summary.

        Args:
            response_text: The AI's response containing booking details

        Returns:
            Dictionary with extracted booking data, or None if not found
        """
        # Check if this contains a booking summary
        if "Booking Details:" not in response_text and "📝" not in response_text:
            return None

        data = {}

        # Extract Parent Name
        match = re.search(r'Parent Name:\s*(.+?)(?:\n|•|$)', response_text)
        if match:
            data['Parent Name'] = match.group(1).strip()

        # Extract Child Name
        match = re.search(r'(?:Child Name|Student Name):\s*(.+?)(?:\n|•|$)', response_text)
        if match:
            data['Child Name'] = match.group(1).strip()

        # Extract Child Age
        match = re.search(r'(?:Child Age|Age):\s*(.+?)(?:\n|•|$)', response_text)
        if match:
            data['Child Age'] = match.group(1).strip()

        # Extract Contact
        match = re.search(r'Contact:\s*(.+?)(?:\n|•|$)', response_text)
        if match:
            data['Contact'] = match.group(1).strip()

        # Extract Email
        match = re.search(r'Email:\s*(.+?)(?:\n|•|$)', response_text)
        if match:
            data['Email'] = match.group(1).strip()

        # Extract Timeslot
        match = re.search(r'Timeslot:\s*(.+?)(?:\n|•|$)', response_text)
        if match:
            data['Timeslot'] = match.group(1).strip()

        # Extract Date
        match = re.search(r'Date:\s*(.+?)(?:\n|•|$)', response_text)
        if match:
            data['Date'] = match.group(1).strip()

        # Extract Location
        match = re.search(r'Location:\s*(.+?)(?:\n|•|$)', response_text)
        if match:
            data['Location'] = match.group(1).strip()

        # Add timestamp
        data['Timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Ensure all required fields exist (with empty string as default)
        required_fields = [
            'Parent Name',
            'Child Name',
            'Child Age',
            'Contact',
            'Email',
            'Timeslot',
            'Date',
            'Location'
        ]
        for field in required_fields:
            if field not in data:
                data[field] = ""

        # Only return if we have the essential fields
        if 'Parent Name' in data and 'Contact' in data:
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
        return "BOOKING_CONFIRMED" in response_text or "**BOOKING_CONFIRMED**" in response_text
