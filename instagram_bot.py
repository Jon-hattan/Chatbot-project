# -*- coding: utf-8 -*-
"""
Instagram Bot - Webhook server for Instagram Messaging API.

Receives Instagram DMs via webhook and processes them through the chatbot.
"""

import os
import sys
import asyncio
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Import chatbot modules
from modules.config_loader import load_yaml
from modules.google_sheets_agent import GoogleSheetsAgent
from modules.intent_detector import IntentDetector
from modules.session_manager import SessionManager
from modules.conversation_agent import ConversationAgent
from modules.chatbot_core import ModularChatbot
from modules.llm_factory import get_llm, get_recommended_model
from modules.input_sanitizer import InputSanitizer
from modules.instagram_sender import InstagramSender

# Fix Windows console encoding for emoji support
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Load environment variables
load_dotenv()

# Flask app
app = Flask(__name__)

# Instagram credentials
PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("INSTAGRAM_PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN")

if not PAGE_ID or not PAGE_ACCESS_TOKEN:
    print("❌ Error: Instagram credentials not found in .env file")
    print("   Required: INSTAGRAM_PAGE_ID, INSTAGRAM_PAGE_ACCESS_TOKEN")
    sys.exit(1)

# --- Load configs ---
SHEET_URL = os.getenv("SHEET_URL")
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

print(f"✅ Using LLM: {provider.upper()} - {model or 'default model'}")

# --- Initialize modular components ---
intent_detector = IntentDetector(llm, "config/intent_prompt.txt")
sheet_agent = GoogleSheetsAgent(sheet_url=SHEET_URL)
session_manager = SessionManager(window_size=25)  # Larger window, no progressive extraction
conversation_agent = ConversationAgent(llm, business_config, session_manager)

# Initialize Instagram sender
instagram_sender = InstagramSender(PAGE_ID, PAGE_ACCESS_TOKEN)

# Initialize chatbot with Instagram sender
chatbot = ModularChatbot(
    intent_detector=intent_detector,
    config=business_config,
    sheet_agent=sheet_agent,
    session_manager=session_manager,
    conversation_agent=conversation_agent,
    llm=llm,
    platform_sender=instagram_sender  # Pass Instagram sender
)

# Input sanitizer
security_config = business_config.get("security", {})
sanitizer = InputSanitizer(
    max_length=security_config.get("input_sanitization", {}).get("max_length", 500)
)

print(f"✅ Chatbot initialized: {business_config['business_name']}")
print(f"✅ Instagram sender ready for Page ID: {PAGE_ID}")


# ===== WEBHOOK ENDPOINTS =====

@app.route('/webhook/instagram', methods=['GET', 'POST'])
def instagram_webhook():
    """
    Instagram webhook endpoint.

    GET: Webhook verification from Meta
    POST: Incoming message events
    """

    if request.method == 'GET':
        # Webhook verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("✅ Webhook verified successfully!")
            return challenge, 200
        else:
            print(f"❌ Webhook verification failed!")
            print(f"   Expected token: {VERIFY_TOKEN}")
            print(f"   Received token: {token}")
            return 'Forbidden', 403

    elif request.method == 'POST':
        # Handle incoming messages
        try:
            body = request.get_json()

            # Verify it's an Instagram event
            if body.get('object') != 'instagram':
                print(f"⚠️ Received non-Instagram event: {body.get('object')}")
                return 'Not Found', 404

            # Process each entry
            for entry in body.get('entry', []):
                for messaging_event in entry.get('messaging', []):
                    # Extract sender and recipient
                    sender_id = messaging_event.get('sender', {}).get('id')
                    recipient_id = messaging_event.get('recipient', {}).get('id')

                    # Handle message event
                    if 'message' in messaging_event:
                        message_data = messaging_event['message']
                        message_text = message_data.get('text', '')

                        if message_text:
                            # Process message asynchronously
                            asyncio.run(handle_message(sender_id, message_text))

                    # Handle postback (button clicks)
                    elif 'postback' in messaging_event:
                        postback_data = messaging_event['postback']
                        payload = postback_data.get('payload', '')
                        title = postback_data.get('title', '')

                        # Treat postback as text message
                        message_text = title or payload
                        asyncio.run(handle_message(sender_id, message_text))

            return 'EVENT_RECEIVED', 200

        except Exception as e:
            print(f"❌ Webhook error: {e}")
            import traceback
            traceback.print_exc()
            # Still return 200 to avoid Meta retrying
            return 'EVENT_RECEIVED', 200


async def handle_message(sender_id: str, message_text: str):
    """
    Process incoming Instagram message through chatbot.

    Args:
        sender_id: IGSID (Instagram Scoped ID)
        message_text: User's message text
    """
    try:
        # Get user info from Instagram Graph API
        user_info = instagram_sender.get_user_info(sender_id)
        name = user_info.get('name', 'User')
        username = user_info.get('username', f'ig_{sender_id[:8]}')

        print(f"\n📩 Message from @{username} ({name}): {message_text[:50]}...")

        # Session ID is the IGSID
        session_id = sender_id

        # Check input sanitization
        if security_config.get("input_sanitization", {}).get("enabled", True):
            if not sanitizer.is_safe(message_text):
                response = sanitizer.get_blocked_message()
                instagram_sender.send_text_message(sender_id, response)
                session_manager.track_suspicious_activity(session_id, "prompt_injection_attempt")
                print(f"⚠️ Blocked suspicious message from {username}")
                return

            # Sanitize message
            message_text = sanitizer.sanitize(message_text)

        # Check rate limit
        rate_limit_config = business_config.get("rate_limiting", {})
        if rate_limit_config.get("enabled", False):
            limit_message = session_manager.check_rate_limit(session_id, rate_limit_config)
            if limit_message:
                instagram_sender.send_text_message(sender_id, limit_message)
                print(f"⚠️ Rate limit exceeded for {username}")
                return

        # Process through chatbot core
        response = await chatbot.process_message(
            session_id=session_id,
            name=name,
            handle=username,
            message=message_text,
            user_username=username
        )

        # Send response back via Instagram
        instagram_sender.send_text_message(sender_id, response)

        print(f"✅ Response sent to @{username}")

    except Exception as e:
        print(f"❌ Error processing message: {e}")
        import traceback
        traceback.print_exc()

        # Send error message to user
        try:
            instagram_sender.send_text_message(
                sender_id,
                "Sorry, something went wrong! Please try again. 😅"
            )
        except:
            pass


# ===== HEALTH CHECK =====

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "platform": "Instagram",
        "bot_name": business_config.get("bot_name", "Bot")
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        "message": "Instagram Bot is running!",
        "bot_name": business_config.get("bot_name", "Bot"),
        "webhook": "/webhook/instagram"
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8443))
    webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:8443")

    print(f"\n{'='*60}")
    print(f"🤖 Starting Instagram Bot: {business_config['bot_name']}")
    print(f"{'='*60}\n")
    print(f"📍 Webhook URL: {webhook_url}/webhook/instagram")
    print(f"📍 Port: {port}")
    print(f"📍 Page ID: {PAGE_ID}")
    print(f"\n⚠️  Configure this webhook URL in Meta App Dashboard:")
    print(f"   1. Go to developers.facebook.com")
    print(f"   2. Select your app → Instagram → Webhooks")
    print(f"   3. Callback URL: {webhook_url}/webhook/instagram")
    print(f"   4. Verify Token: {VERIFY_TOKEN}")
    print(f"   5. Subscribe to: messages\n")
    print("✅ Bot is running! Send a DM to your Instagram Business account to test!\n")

    # Run Flask app
    # For production, use gunicorn: gunicorn -w 4 -b 0.0.0.0:8443 instagram_bot:app
    app.run(host='0.0.0.0', port=port, debug=False)
