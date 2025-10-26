import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os

load_dotenv()

SHEET_URL = os.getenv("SHEET_URL")

# Define required Google scopes
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Load your service account credentials
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Open the Google Sheet by full URL
sheet = client.open_by_url(SHEET_URL).sheet1

# Try to write test data
sheet.append_row(["✅ Access Test", "Service Account Working"])

print("SUCCESS: Service account can access & write to the Google Sheet!")
