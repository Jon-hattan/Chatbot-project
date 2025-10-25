import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

class GoogleSheetsAgent:
    def __init__(self, sheet_url, creds_path="credentials.json"):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        self.sheet = client.open_by_url(sheet_url).sheet1

        # Define fixed column order for booking data
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

    def write_row(self, values: dict):
        """
        Write a row to Google Sheets in fixed column order.

        Args:
            values: Dictionary with booking data
        """
        # Create ordered list based on COLUMN_ORDER
        # Use empty string for missing values instead of "N/A"
        ordered = [values.get(col, "") for col in self.COLUMN_ORDER]
        self.sheet.append_row(ordered)
