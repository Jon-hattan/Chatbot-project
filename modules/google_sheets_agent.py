import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import os

class GoogleSheetsAgent:
    def __init__(self, sheet_url):
        """
        Initialize GoogleSheetsAgent with lazy connection.
        Connection to Google Sheets is deferred until first use.

        Args:
            sheet_url: URL of the Google Sheet to connect to
        """
        # Store sheet URL for later connection
        self.sheet_url = sheet_url
        self.sheet = None  # Will be initialized on first use
        self._client = None  # Will be initialized on first use

        # Read service account JSON from environment variable
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

        if not creds_json:
            raise ValueError("Missing GOOGLE_CREDENTIALS_JSON environment variable")

        # Convert JSON string to dict and store
        self.creds_dict = json.loads(creds_json)

        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        self.COLUMN_ORDER = [
            'Parent Name',
            'Child Name',
            'Child Age',
            'Contact',
            'Email',
            'Timeslot',
            'Date',
            'Location',
            'Timestamp'
        ]

    def _ensure_connected(self):
        """
        Ensure connection to Google Sheets is established.
        Lazy initialization - only connects on first use.
        """
        if self.sheet is None:
            try:
                # Create credentials from JSON dict
                creds = Credentials.from_service_account_info(self.creds_dict, scopes=self.scope)
                self._client = gspread.authorize(creds)
                self.sheet = self._client.open_by_url(self.sheet_url).sheet1
                print("✓ Connected to Google Sheets successfully")
            except Exception as e:
                print(f"⚠️ Warning: Could not connect to Google Sheets: {e}")
                print("   Chatbot will continue without sheet logging functionality")
                # Set sheet to a sentinel value to avoid retry loops
                self.sheet = False
                raise

    def write_row(self, values: dict):
        """
        Write a row to Google Sheets in fixed column order.

        Args:
            values: Dictionary with booking data
        """
        # Ensure connection is established
        self._ensure_connected()

        # Check if connection failed
        if self.sheet is False:
            print("⚠️ Skipping sheet write - connection unavailable")
            return

        # Create ordered list based on COLUMN_ORDER
        # Use empty string for missing values instead of "N/A"
        ordered = [values.get(col, "") for col in self.COLUMN_ORDER]
        self.sheet.append_row(ordered)
