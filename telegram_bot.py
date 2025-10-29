# -*- coding: utf-8 -*-
import os
import sys
import asyncio
import signal
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Fix Windows console encoding for emoji support
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    # Python < 3.7
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Import existing chatbot components
from modules.config_loader import load_yaml
from modules.google_sheets_agent import GoogleSheetsAgent
from modules.intent_detector import IntentDetector
from modules.session_manager import SessionManager
from modules.conversation_agent import ConversationAgent
from modules.chatbot_core import ModularChatbot
from modules.llm_factory import get_llm, get_recommended_model
from modules.input_sanitizer import InputSanitizer

# Load environment
load_dotenv()

# Initialize chatbot (same as main2.py)
SHEET_URL = os.getenv("SHEET_URL")
business_config = load_yaml("config/business_profile.yaml")

llm_config = business_config.get("llm", {})
provider = llm_config.get("provider", "groq")
model = llm_config.get("model")
tier = llm_config.get("tier")

if tier and not model:
    model = get_recommended_model(provider, tier)

llm = get_llm(provider=provider, model=model)

intent_detector = IntentDetector(llm, "config/intent_prompt.txt")
sheet_agent = GoogleSheetsAgent(sheet_url=SHEET_URL)
session_manager = SessionManager(window_size=5)
conversation_agent = ConversationAgent(llm, business_config, session_manager)

# Initialize chatbot without bot_application first (will be set later)
chatbot = None

# Initialize input sanitizer
sanitizer = InputSanitizer(max_length=business_config.get("security", {}).get("input_sanitization", {}).get("max_length", 500))

print(f"✅ Chatbot configuration loaded: {business_config['business_name']}")
print(f"✅ Using LLM: {provider.upper()} - {model or 'default model'}")
print(f"✅ Input sanitizer initialized")


# ===== TELEGRAM HANDLERS =====

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    welcome_msg = f"Hi {user.first_name}! I'm Luke.AI from 555Beatbox Academy Singapore! 🎤\n\n"
    welcome_msg += "How can I help you today? Feel free to ask about our classes! 😊"
    await update.message.reply_text(welcome_msg)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command - reset conversation"""
    session_id = str(update.effective_user.id)
    chatbot.clear_session(session_id)
    await update.message.reply_text("✅ Session cleared! Let's start fresh. 😊")


# async def groupid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle /groupid command - show chat ID for groups"""
#     chat = update.effective_chat
#     chat_id = chat.id
#     chat_type = chat.type

#     if chat_type in ['group', 'supergroup']:
#         # It's a group - show the ID
#         await update.message.reply_text(
#             f"📋 Group Chat ID: `{chat_id}`\n\n"
#             f"Add this to your .env file as:\n"
#             f"`MODERATOR_CHAT_ID={chat_id}`",
#             parse_mode="Markdown"
#         )
#     else:
#         # Private chat
#         await update.message.reply_text(
#             f"ℹ️ This command only works in groups!\n\n"
#             f"Your personal chat ID is: `{chat_id}`",
#             parse_mode="Markdown"
#         )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    try:
        # Show typing indicator
        await update.message.chat.send_action("typing")

        # Extract user info
        user = update.effective_user
        session_id = str(user.id)  # Telegram user ID as session
        name = user.first_name or "User"
        handle = user.username or f"telegram_{user.id}"
        user_username = user.username  # Telegram username for moderator notifications
        message = update.message.text

        # Check input sanitization (prompt injection detection)
        security_config = business_config.get("security", {})
        if security_config.get("input_sanitization", {}).get("enabled", True):
            if not sanitizer.is_safe(message):
                await update.message.reply_text(sanitizer.get_blocked_message())
                session_manager.track_suspicious_activity(session_id, "prompt_injection_attempt")
                return  # Exit early, block malicious input

            # Sanitize the message
            message = sanitizer.sanitize(message)

        # Check rate limit before processing
        rate_limit_config = business_config.get("rate_limiting", {})
        if rate_limit_config.get("enabled", False):
            limit_message = session_manager.check_rate_limit(session_id, rate_limit_config)
            if limit_message:
                await update.message.reply_text(limit_message)
                return  # Exit early, don't process message

        # Process through existing chatbot
        response = await chatbot.process_message(
            session_id=session_id,
            name=name,
            handle=handle,
            message=message,
            user_username=user_username
        )

        # Send response back to Telegram
        await update.message.reply_text(response)

    except Exception as e:
        print(f"❌ Error processing message: {e}")
        await update.message.reply_text(
            "Sorry, something went wrong! Please try again. 😅"
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    print(f"❌ Error: {context.error}")


# ===== MAIN WEBHOOK SETUP =====

async def main():
    """Start the Telegram bot with webhook mode"""

    # Get token
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in .env file!")
        print("Please add: TELEGRAM_BOT_TOKEN=your_token_here")
        print("\nTo get a token:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /newbot and follow instructions")
        print("3. Copy the token and add it to your .env file")
        return

    # Get webhook URL from environment
    webhook_url = os.getenv("WEBHOOK_URL")

    if not webhook_url:
        print("❌ ERROR: WEBHOOK_URL not found in .env file!")
        print("Please add: WEBHOOK_URL=https://your-app.railway.app")
        print("\nFor local development with ngrok:")
        print("1. Start ngrok manually: ngrok http 8443")
        print("2. Copy the HTTPS URL (e.g., https://xxxx.ngrok-free.dev)")
        print("3. Add to .env: WEBHOOK_URL=https://xxxx.ngrok-free.dev")
        return

    # Get port from environment (cloud platforms set this automatically)
    port = int(os.getenv("PORT", "8443"))

    print(f"\n{'='*60}")
    print(f"🤖 Starting Telegram Bot: {business_config['bot_name']} (Webhook Mode)")
    print(f"{'='*60}\n")
    print(f"📍 Webhook URL: {webhook_url}")
    print(f"📍 Port: {port}\n")

    try:
        # Create application
        app = Application.builder().token(token).build()

        # Initialize chatbot with bot application
        global chatbot
        chatbot = ModularChatbot(
            intent_detector=intent_detector,
            config=business_config,
            sheet_agent=sheet_agent,
            session_manager=session_manager,
            conversation_agent=conversation_agent,
            llm=llm,
            bot_application=app
        )
        print(f"✅ Chatbot initialized with bot application")

        # Add command handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("clear", clear_command))
        # app.add_handler(CommandHandler("groupid", groupid_command))

        # Add message handler (for all text messages)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Add error handler
        app.add_error_handler(error_handler)

        # Initialize the application
        await app.initialize()
        await app.start()

        # Set webhook
        webhook_endpoint = f"{webhook_url}/webhook"
        await app.bot.set_webhook(url=webhook_endpoint)
        print(f"✅ Webhook set to: {webhook_endpoint}")

        print("\n✅ Bot is running! Press Ctrl+C to stop.")
        print("📱 Go to Telegram and search for your bot to start chatting!\n")

        # Start the webhook server
        await app.updater.start_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="/webhook",
            webhook_url=webhook_endpoint
        )

        # Keep the bot running
        stop_event = asyncio.Event()

        # Handle shutdown signals
        def signal_handler(_signum, _frame):
            print("\n🛑 Shutdown signal received...")
            stop_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Wait for stop event
        await stop_event.wait()

    except KeyboardInterrupt:
        print("\n🛑 Shutdown initiated by user...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("🧹 Cleaning up...")

        try:
            # Delete webhook
            await app.bot.delete_webhook()
            print("✅ Webhook deleted")
        except:
            pass

        try:
            # Stop the application
            await app.stop()
            await app.shutdown()
        except:
            pass

        print("👋 Bot stopped gracefully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
