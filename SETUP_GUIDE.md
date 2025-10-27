# Setup Guide - Modular Chatbot

This guide will walk you through setting up your modular chatbot from scratch.

## Prerequisites

- Python 3.8 or higher
- A Google account (for Google Sheets)
- A Groq API account (free tier available at https://console.groq.com)

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install langchain langchain-groq langchain-core gspread oauth2client python-dotenv pyyaml fastapi uvicorn
```

## Step 2: Set Up Google Sheets

### 2.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing one)
3. Enable the **Google Sheets API** and **Google Drive API**

### 2.2 Create Service Account

1. Go to "IAM & Admin" → "Service Accounts"
2. Click "Create Service Account"
3. Give it a name (e.g., "chatbot-sheets-access")
4. Click "Create and Continue"
5. Skip granting access (click "Continue")
6. Click "Done"

### 2.3 Create and Download Credentials

1. Click on the service account you just created
2. Go to "Keys" tab
3. Click "Add Key" → "Create New Key"
4. Choose "JSON" format
5. Download the file and rename it to `credentials.json`
6. Place `credentials.json` in your project root directory

### 2.4 Create and Share Google Sheet

1. Create a new Google Sheet
2. Add column headers in the first row:
   ```
   Name | Instagram Handle | Message | Timestamp
   ```
3. Copy the Sheet URL from your browser
4. Click "Share" button
5. Share the sheet with the service account email from `credentials.json`
   - The email looks like: `your-service-account@your-project.iam.gserviceaccount.com`
   - Give it "Editor" permission

## Step 3: Get Groq API Key

1. Go to [Groq Console](https://console.groq.com)
2. Sign up or log in
3. Go to "API Keys" section
4. Create a new API key
5. Copy the API key

## Step 4: Create Environment File

Create a `.env` file in your project root:

```env
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=llama3-8b-8192

# Google Sheets Configuration
SHEET_URL=your_google_sheet_url_here

# Instagram Webhook (optional - for later)
VERIFY_TOKEN=your_verify_token_here
```

Replace:
- `your_groq_api_key_here` with your actual Groq API key
- `your_google_sheet_url_here` with your Google Sheet URL

## Step 5: Configure Your Business

Edit `config/business_profile.yaml` to customize for your business:

```yaml
business_name: "Your Business Name"

# Customize these responses
reply_on_intent_detected: "Hi {name}! Should I register your information?"
reply_on_success: "Great {name}! You're registered!"
reply_on_rejection: "No problem {name}!"
reply_on_neutral: "Hey {name}! How can I help?"
reply_on_unclear: "Sorry {name}, could you confirm with yes or no?"
```

Edit `config/intent_prompt.txt` to define what intent to detect:

```
You are a binary classifier.

Your task is to decide if the user's message shows interest in [YOUR SERVICE/PRODUCT].

Rules:
- If the message clearly mentions [SPECIFIC KEYWORDS/INTENT], respond with "YES".
- Otherwise, respond with "NO".

Output format: YES or NO only.
```

## Step 6: Test Your Setup

### Test Google Sheets Connection

```bash
python dump/writing_to_sheets.py
```

This should write a test row to your Google Sheet. If you see an error:
- Check that `credentials.json` is in the correct location
- Verify you shared the sheet with the service account email
- Make sure the SHEET_URL in `.env` is correct

### Test the Chatbot

```bash
python main2.py
```

You should see:
```
=== Modular Chatbot for [Your Business Name] ===
Features:
  - Intent detection using LLM
  - Confirmation flow before logging
  - Session-aware conversations
  - Google Sheets integration

Type 'exit' to quit, 'clear' to reset session.

Your name:
```

### Example Test Conversation

```
Your name: Alice
Instagram handle: @alice_test

Alice: Hi there!
Bot: Hey Alice! How can I help?

Alice: I want to sign up
Bot: Hi Alice! Should I register your information?

Alice: yes
Bot: Great Alice! You're registered!
```

Check your Google Sheet - you should see Alice's information logged!

## Step 7: Run Examples

```bash
python example_usage.py
```

This will demonstrate various conversation flows.

## Troubleshooting

### "Could not automatically determine credentials"
- Make sure `credentials.json` exists in project root
- Check that the JSON file is valid

### "The caller does not have permission"
- Share your Google Sheet with the service account email
- Give it "Editor" permission

### "Invalid API key"
- Verify your Groq API key in `.env`
- Make sure there are no extra spaces

### "Sheet not found"
- Check that SHEET_URL in `.env` is correct
- URL should look like: `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit`

### Intent not being detected
- Check `config/intent_prompt.txt`
- Make sure your prompt clearly defines what to detect
- Test with more explicit messages

## Next Steps

1. **Customize responses** in `config/business_profile.yaml`
2. **Adjust intent detection** in `config/intent_prompt.txt`
3. **Test different scenarios** to ensure it works for your use case
4. **Integrate with Instagram** using `endpoint.py` (when ready)

## File Structure

```
chatbot-project/
├── .env                          # Your environment variables (create this)
├── credentials.json              # Google service account (create this)
├── requirements.txt              # Python dependencies
├── main2.py                      # Main entry point for testing
├── example_usage.py              # Example demonstrations
├── endpoint.py                   # Instagram webhook (for later)
├── config/
│   ├── business_profile.yaml     # Customize your responses here
│   ├── intent_prompt.txt         # Define what intent to detect
│   ├── sheet_fields.yaml         # Sheet field configuration
│   ├── master_prompt.txt         # (optional) main chatbot prompt
│   └── context_business.md       # (optional) business context
└── modules/
    ├── chatbot_core.py           # Main orchestration
    ├── intent_detector.py        # Intent detection logic
    ├── conversation_agent.py     # Conversational AI with flow rules
    ├── session_manager.py        # Session state management
    ├── booking_data_extractor.py # Extract booking data from conversations
    ├── google_sheets_agent.py    # Google Sheets integration
    ├── config_loader.py          # Config loading utilities
    └── context_loader.py         # Context loading utilities
```

## Support

If you run into issues:
1. Check the error message carefully
2. Verify all steps in this guide
3. Make sure all dependencies are installed
4. Check that your API keys and credentials are correct

Happy chatbot building!
