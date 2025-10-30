# 555Beatbox Academy Telegram Chatbot

An intelligent Telegram chatbot built with Langchain and Google Sheets API for managing bookings with customers. Built for 555BeatboxSG, a beatboxing enrichment class provider for kids.

**Tech Stack**: Python · LangChain · Telegram Bot API · Google Sheets API · Groq LLM

---

**Why I Made This:** 
When I first started exploring automations for small businesses, I realised that most commercial low-code chatbot builders like ManyChat, Chatfuel, and Flow XO offered convenient drag-and-drop flows and social media integrations, but at the cost of steep subscription fees and rigid logic systems. Tools such as ManyChat’s Instagram DM automation start at around US$80 per month, with advanced features like API calls or AI integrations locked behind even higher tiers. For small studios or classes with limited lead volumes, these costs quickly outweigh the benefits. 

I decided to build a low-cost, modular chatbot framework using LangChain, Telegram’s Bot API, and the Google Sheets API. Instead of relying on proprietary platforms, this architecture is fully open and customisable: each business can define its own flows and rules through YAML configuration files without touching the core codebase. It runs affordably on platforms like Railway, and can be easily adapted for other small businesses, from tuition centres to hair salons to creative studios. 

I piloted the first deployment with 555BeatboxSG, a beatboxing enrichment academy where I previously performed and taught. The project serves as a way to streamline parent inquiries and automate class bookings. As of now the prototype runs at zero cost thanks to very light traffic and a lightweight deployment on Railway’s free tier. Based on current architecture and conservative API/hosting assumptions, I estimate a production workload of ~500 customers/day would cost on the order of US$20/month, which is still far cheaper than most low-code alternatives.

**What I've been working on:** 

### 1. Chatbot Foundation (LangChain + Google Sheets)
- **LLM Integration**: Integrated Groq's models (llama-3.3-70b-versatile) via LangChain for natural conversations
- **Intent Detection**: LLM-based classification for special cases (that need human intervention)
- **Conversational AI**: Flow-driven booking system with progressive data collection
- **Google Sheets Logging**: Automatic logging of confirmed bookings to spreadsheet
- **Session Management**: Per-user conversation state with 5-message history window
- **Booking Data Extraction**: Progressive extraction and validation of parent/child information
- **Modularity**: YAML-based business logic and flow rules can be changed to modify chatbot to fit needs of the client.

### 2. Telegram Integration + Moderator System
- **Telegram Bot**: Full webhook-based bot deployment (Railway-ready)
- **Human Escalation**: Automatic moderator notifications for special inquiries
- **Moderator Alerts**: Send notifications to moderators (including conversation summary, user info, and required action)
- **Rate Limiting**: Spam protection with warning → block escalation (5 msgs/10 sec)
- **Session Persistence**: User sessions tracked by Telegram user ID

### 3. Security (Prompt Injection Prevention)
- **Input Sanitization**: 30+ pattern detection for prompt injection attempts
- **Prompt Delimiting**: Clear boundaries between system instructions and user input
- **System Prompt Protection**: Instructions to prevent system information leakage
- **Output Validation**: Automatic detection and blocking of system prompt leaks
- **Suspicious Activity Tracking**: Block users after 3 detected injection attempts

---


## Configuration

### Business Logic (`config/business_profile.yaml`)
Defines the information needed from the business owner to run the bot (eg, class timings, etc.)

### Conversation Flow (`config/flow_rules.txt`)
Defines the bot's personality, booking flow, and conversation rules.

---

## Architecture

```
telegram_bot.py                    # Webhook handler & entry point
├── modules/
│   ├── input_sanitizer.py        # Prompt injection detection
│   ├── chatbot_core.py           # Orchestrates all modules
│   ├── intent_detector.py        # LLM-based intent classification
│   ├── conversation_agent.py     # Natural conversation with LLM
│   ├── booking_data_extractor.py # Progressive data extraction
│   ├── session_manager.py        # Per-user state & rate limiting
│   └── google_sheets_agent.py    # Booking data logging
└── config/
    ├── business_profile.yaml     # Business logic & config
    └── flow_rules.txt            # Conversation flow instructions
```

### Data Flow
```
User Message (Telegram)
    ↓
[Input Sanitization] ← Prompt injection detection
    ↓
[Rate Limiting] ← Spam protection
    ↓
[Intent Detection] ← Special case routing?
    ↓
├─ Special Case → [Moderator Notification] → Exit
└─ Normal → [Conversation Agent]
              ↓
         [Data Extraction] ← Progressive collection
              ↓
         [Booking Confirmation?]
              ↓
         [Google Sheets] ← Validated & logged
```
