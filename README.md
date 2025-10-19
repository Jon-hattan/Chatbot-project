# Instagram DM AI Chatbot (Work in Progress)

This project is an AI-powered Instagram Direct Message chatbot built using the Meta Instagram API, LangChain, Groq and Google Sheets API. The goal is to create an AI chatbot on Instagram DMs that can also handle structured data logging into Google Sheets.

## Project Goal
By completion, the chatbot will be able to:

- Receive and respond to Instagram DMs via webhook  
- Generate responses using LangChain  
- Extract key information from messages (eg. client details)  
- Record structured data into a connected Google Sheet

## Technology Stack

| Component          | Purpose                              |
|--------------------|--------------------------------------|
| Instagram API      | DM handling via webhook              |
| LangChain + Groq   | AI reasoning and response generation |
| FastAPI            | Backend webhook server               |
| ngrok / Vercel     | Local tunneling and deployment       |
| Google Sheets API  | Data storage and logging             |

## Current Status

- Initial project setup completed  
- Meta API configuration and webhook development in progress  
- LangChain integration and Google Sheets automation planned

