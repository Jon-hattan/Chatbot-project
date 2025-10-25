"""
Example usage of the Modular Chatbot.

This script demonstrates how to use the chatbot programmatically,
including custom configuration and different use cases.
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from modules.intent_detector import IntentDetector
from modules.google_sheets_agent import GoogleSheetsAgent
from modules.chatbot_core import ModularChatbot
from modules.config_loader import load_yaml
from modules.session_manager import SessionManager
from modules.confirmation_handler import ConfirmationHandler

# Load environment
load_dotenv()

# Configuration
SHEET_URL = os.getenv("SHEET_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3-8b-8192")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Load configs
business_config = load_yaml("config/business_profile.yaml")

# Initialize LLM
llm = ChatGroq(model=MODEL_NAME, api_key=GROQ_API_KEY)

# Initialize components
intent_detector = IntentDetector(llm, "config/intent_prompt.txt")
sheet_agent = GoogleSheetsAgent(sheet_url=SHEET_URL)
session_manager = SessionManager(window_size=5)
confirmation_handler = ConfirmationHandler(
    confirmation_keywords=business_config.get("confirmation")
)

# Create chatbot
chatbot = ModularChatbot(
    intent_detector=intent_detector,
    config=business_config,
    sheet_agent=sheet_agent,
    session_manager=session_manager,
    confirmation_handler=confirmation_handler
)


def example_conversation():
    """Simulates a complete conversation flow."""
    print("=== Example Conversation Flow ===\n")

    session_id = "demo_user_1"
    name = "Sarah"
    handle = "@sarah_music"

    # Message 1: Casual greeting (no intent)
    print(f"{name}: Hello!")
    response = chatbot.process_message(session_id, name, handle, "Hello!")
    print(f"Bot: {response}\n")

    # Message 2: Shows intent
    print(f"{name}: I want to enroll my kid in beatboxing classes")
    response = chatbot.process_message(
        session_id, name, handle, "I want to enroll my kid in beatboxing classes"
    )
    print(f"Bot: {response}\n")

    # Message 3: Confirms
    print(f"{name}: Yes, please!")
    response = chatbot.process_message(session_id, name, handle, "Yes, please!")
    print(f"Bot: {response}\n")

    print("✓ Data has been logged to Google Sheets!\n")


def example_rejection():
    """Simulates a rejection flow."""
    print("=== Example Rejection Flow ===\n")

    session_id = "demo_user_2"
    name = "Mike"
    handle = "@mike_beats"

    # Message 1: Shows intent
    print(f"{name}: I'm interested in signing up")
    response = chatbot.process_message(session_id, name, handle, "I'm interested in signing up")
    print(f"Bot: {response}\n")

    # Message 2: Rejects
    print(f"{name}: Actually, no thanks")
    response = chatbot.process_message(session_id, name, handle, "Actually, no thanks")
    print(f"Bot: {response}\n")

    print("✗ No data logged (user declined)\n")


def example_unclear_response():
    """Simulates unclear confirmation response."""
    print("=== Example Unclear Response Flow ===\n")

    session_id = "demo_user_3"
    name = "Emma"
    handle = "@emma_rhythms"

    # Message 1: Shows intent
    print(f"{name}: Can I join?")
    response = chatbot.process_message(session_id, name, handle, "Can I join?")
    print(f"Bot: {response}\n")

    # Message 2: Unclear response
    print(f"{name}: Maybe later")
    response = chatbot.process_message(session_id, name, handle, "Maybe later")
    print(f"Bot: {response}\n")

    # Message 3: Clear confirmation
    print(f"{name}: Yes")
    response = chatbot.process_message(session_id, name, handle, "Yes")
    print(f"Bot: {response}\n")

    print("✓ Data logged after clarification!\n")


def example_multiple_sessions():
    """Demonstrates session isolation."""
    print("=== Example Multiple Sessions (Isolation) ===\n")

    # User 1 starts conversation
    print("User 1 (Alex) - Session 1:")
    print("Alex: I want to register")
    response1 = chatbot.process_message("session_1", "Alex", "@alex", "I want to register")
    print(f"Bot: {response1}\n")

    # User 2 starts different conversation
    print("User 2 (Taylor) - Session 2:")
    print("Taylor: Hello!")
    response2 = chatbot.process_message("session_2", "Taylor", "@taylor", "Hello!")
    print(f"Bot: {response2}\n")

    # User 1 confirms
    print("User 1 (Alex) - Session 1:")
    print("Alex: Yes")
    response1 = chatbot.process_message("session_1", "Alex", "@alex", "Yes")
    print(f"Bot: {response1}\n")

    print("✓ Sessions are isolated - User 2's 'Hello' didn't interfere with User 1's confirmation!\n")


if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════╗")
    print("║   Modular Chatbot - Example Usage Demonstrations       ║")
    print("╚════════════════════════════════════════════════════════╝\n")

    try:
        # Run examples
        example_conversation()
        print("-" * 60 + "\n")

        example_rejection()
        print("-" * 60 + "\n")

        example_unclear_response()
        print("-" * 60 + "\n")

        example_multiple_sessions()
        print("-" * 60 + "\n")

        print("✅ All examples completed successfully!")
        print("\nNote: Check your Google Sheet to see the logged data.")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        print("\nMake sure you have:")
        print("  1. Set up .env with GROQ_API_KEY and SHEET_URL")
        print("  2. Added credentials.json for Google Sheets")
        print("  3. Shared the sheet with your service account email")
