# Modular Chatbot with Intent Detection & Confirmation

A highly modular chatbot system that detects user intent using LLMs, asks for confirmation, and logs information to Google Sheets. Built with clean separation of concerns for easy customization and extension.

## Features

- **LLM-Based Intent Detection**: Uses Groq LLMs to intelligently detect user intent
- **Confirmation Flow**: Always asks for user confirmation before logging data
- **Session Management**: Tracks conversation state across multiple messages
- **Google Sheets Integration**: Automatically logs confirmed data to Google Sheets
- **Highly Modular**: Each component is independent and easily swappable
- **Configurable**: All responses and behavior controlled via YAML configs

## Architecture

```
modules/
├── intent_detector.py        # LLM-based intent classification
├── conversation_agent.py     # Natural conversational AI with flow rules
├── session_manager.py        # Manages conversation state per user
├── booking_data_extractor.py # Extracts booking data from conversations
├── google_sheets_agent.py    # Logs data to Google Sheets
└── chatbot_core.py           # Orchestrates all modules (ModularChatbot class)
```

## Conversation Flow

1. **User sends message** → Intent detector analyzes it
2. **Intent detected?** → Bot asks "Should I register your information?"
3. **User confirms** → Data logged to Google Sheets + Success response
4. **User declines** → Neutral response, no logging
5. **No intent** → Casual conversation continues

## Installation

1. Install dependencies:
```bash
pip install langchain langchain-groq gspread oauth2client python-dotenv pyyaml
```

2. Set up environment variables in `.env`:
```env
GROQ_API_KEY=your_groq_api_key
MODEL_NAME=llama3-8b-8192
SHEET_URL=your_google_sheets_url
```

3. Set up Google Sheets credentials:
   - Create a service account in Google Cloud Console
   - Download `credentials.json` to project root
   - Share your Google Sheet with the service account email

## Configuration

### Business Profile (`config/business_profile.yaml`)

```yaml
business_name: "Your Business Name"

# Response templates
reply_on_intent_detected: "Hi {name}! Should I register your information?"
reply_on_success: "Great {name}! You're registered!"
reply_on_rejection: "No problem {name}!"
reply_on_neutral: "Hey {name}! How can I help?"
reply_on_unclear: "Sorry {name}, could you confirm with yes or no?"

# Confirmation keywords
confirmation:
  positive: ["yes", "yeah", "sure", "ok"]
  negative: ["no", "nope", "cancel"]
```

### Intent Prompt (`config/intent_prompt.txt`)

Define what intent to detect. Example:

```
You are a binary classifier.

Your task is to decide if the user's message shows interest in [YOUR BUSINESS OFFERING].

Rules:
- If the message clearly mentions interest, respond with "YES".
- Otherwise, respond with "NO".

Output format: YES or NO only.
```

## Usage

### Basic Usage (CLI Testing)

```bash
python main2.py
```

### Programmatic Usage

```python
from langchain_groq import ChatGroq
from modules.intent_detector import IntentDetector
from modules.google_sheets_agent import GoogleSheetsAgent
from modules.chatbot_core import ModularChatbot
from modules.config_loader import load_yaml

# Initialize components
llm = ChatGroq(model="llama3-8b-8192", api_key="your_api_key")
intent_detector = IntentDetector(llm, "config/intent_prompt.txt")
sheet_agent = GoogleSheetsAgent(sheet_url="your_sheet_url")
config = load_yaml("config/business_profile.yaml")

# Create chatbot
chatbot = ModularChatbot(
    intent_detector=intent_detector,
    config=config,
    sheet_agent=sheet_agent
)

# Process messages
response = chatbot.process_message(
    session_id="user123",
    name="John",
    handle="@john_doe",
    message="I want to sign up for classes"
)
print(response)  # Asks for confirmation

# User confirms
response = chatbot.process_message(
    session_id="user123",
    name="John",
    handle="@john_doe",
    message="yes"
)
print(response)  # Success! Data logged to sheets
```

## Module Details

### IntentDetector

Detects if a message matches your configured intent using LLM classification.

```python
from modules.intent_detector import IntentDetector

detector = IntentDetector(llm, "config/intent_prompt.txt")
has_intent = detector.detect("I want to join your class")  # Returns True/False
```

### SessionManager

Tracks conversation state for each user session.

```python
from modules.session_manager import SessionManager

manager = SessionManager()
manager.set_awaiting_confirmation("user123", {"name": "John"})
is_waiting = manager.is_awaiting_confirmation("user123")  # True
```

### GoogleSheetsAgent

Logs data to Google Sheets.

```python
from modules.google_sheets_agent import GoogleSheetsAgent

agent = GoogleSheetsAgent(sheet_url="your_url")
agent.write_row({"Name": "John", "Email": "john@example.com"})
```

## Customization

### Swap LLM Provider

```python
# Use OpenAI instead of Groq
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4", api_key="your_key")
intent_detector = IntentDetector(llm, "config/intent_prompt.txt")
```

### Custom Confirmation Logic

```python
# Create custom conversation agent with different flow rules
custom_agent = ConversationAgent(llm, config, session_manager, "config/custom_flow_rules.txt")

chatbot = ModularChatbot(
    intent_detector=intent_detector,
    config=config,
    sheet_agent=sheet_agent,
    conversation_agent=custom_agent
)
```

### Add Multiple Intents

```python
# Create multiple intent detectors
signup_detector = IntentDetector(llm, "config/signup_intent.txt")
support_detector = IntentDetector(llm, "config/support_intent.txt")

# Check different intents
if signup_detector.detect(message):
    # Handle signup
elif support_detector.detect(message):
    # Handle support
```

## Testing Example

```
Your name: Alice
Instagram handle: @alice_beats

Alice: Hi there!
Bot: Hey Alice! Want to learn some cool beatboxing skills? I can help you sign up when you're ready.

Alice: I want to join the class
Bot: Hi Alice! It looks like you're interested in joining our beatboxing kids class. Should I go ahead and register your information?

Alice: yes please
Bot: Awesome Alice! You're officially registered for our next beatboxing kids class. We'll reach out soon with more details!
```

Data logged to Google Sheets:
| Name  | Instagram Handle | Message                  | Timestamp          |
|-------|------------------|--------------------------|--------------------|
| Alice | @alice_beats     | I want to join the class | 2024-01-15 14:30:22|

## Extending for Instagram Webhooks

The chatbot is designed to easily integrate with Instagram webhooks. See `endpoint.py` for the FastAPI webhook structure. You'll need to:

1. Update `endpoint.py` to initialize the `ModularChatbot`
2. Extract user info from Instagram webhook payload
3. Use Instagram sender ID as `session_id`
4. Call `chatbot.process_message()` with the data
5. Send the response back via Instagram API

## License

MIT

## Contributing

This chatbot is highly modular - feel free to:
- Add new intent detectors
- Create custom confirmation handlers
- Integrate different LLM providers
- Add new logging destinations (databases, CRMs, etc.)
- Extend session management features
