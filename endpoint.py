from fastapi import FastAPI, Request
import os
from dotenv import load_dotenv

load_dotenv()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

app = FastAPI()



@app.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    return "Verification failed"

@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    print("Incoming message:", data)
    return "EVENT_RECEIVED"
