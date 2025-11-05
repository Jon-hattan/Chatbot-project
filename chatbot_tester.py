# -*- coding: utf-8 -*-
import os
import sys
import asyncio
from dotenv import load_dotenv
from modules.config_loader import load_yaml
from modules.google_sheets_agent import GoogleSheetsAgent
from modules.intent_detector import IntentDetector
from modules.session_manager import SessionManager
from modules.conversation_agent import ConversationAgent
from modules.chatbot_core import ModularChatbot
from modules.llm_factory import get_llm, get_recommended_model

# Fix Windows console encoding for emoji support
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    # Python < 3.7
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

load_dotenv()

# --- Load environment ---
SHEET_URL = os.getenv("SHEET_URL")

# --- Load configs ---
# this is where all the configuration for the chatbot will be done
business_config = load_yaml("config/business_profile.yaml")

# --- Initialize LLM from configuration ---
llm_config = business_config.get("llm", {})
provider = llm_config.get("provider", "groq")
model = llm_config.get("model")
tier = llm_config.get("tier")

# If tier is specified, use recommended model for that tier
if tier and not model:
    model = get_recommended_model(provider, tier)

# Get LLM instance
llm = get_llm(provider=provider, model=model)

print(f"Using LLM: {provider.upper()} - {model or 'default model'}")

# --- Initialize modular components ---
intent_detector = IntentDetector(llm, "config/intent_prompt.txt")
sheet_agent = GoogleSheetsAgent(sheet_url=SHEET_URL)
session_manager = SessionManager(window_size=8)
conversation_agent = ConversationAgent(llm, business_config, session_manager)

# --- Initialize modular chatbot ---
chatbot = ModularChatbot(
    intent_detector=intent_detector,
    config=business_config,
    sheet_agent=sheet_agent,
    session_manager=session_manager,
    conversation_agent=conversation_agent,
    llm=llm  # For progressive booking data extraction
)

# --- Simulated chat loop for testing ---
async def main():
    """Main async chat loop for testing the chatbot."""
    print(f"=== Modular Chatbot for {business_config['business_name']} ===")
    print("Features:")
    print("  - Conversational AI (answers questions naturally)")
    print("  - Intent detection using LLM")
    print("  - Confirmation flow before logging")
    print("  - Session-aware conversations")
    print("  - Google Sheets integration")
    print("\nType 'exit' to quit, 'clear' to reset session.\n")

    # Simulate a single user session
    session_id = "test_user_123"
    user_name = None
    user_handle = None

    while True:
        # Get user info if not set
        if user_name is None:
            user_name = input("Your name: ")
            if user_name.lower() == "exit":
                break
            user_handle = input("Instagram handle: ")

        # Get message
        msg = input(f"\n{user_name}: ")

        if msg.lower() == "exit":
            break
        elif msg.lower() == "clear":
            chatbot.clear_session(session_id)
            print("Session cleared!\n")
            user_name = None
            user_handle = None
            continue

        # Process message through modular chatbot (async call)
        try:
            reply = await chatbot.process_message(
                session_id=session_id,
                name=user_name,
                handle=user_handle,
                message=msg,
                user_username=user_handle
            )
            print(f"Bot: {reply}\n")
        except Exception as e:
            print(f"❌ Error processing message: {e}\n")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
