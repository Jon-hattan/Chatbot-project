import os
from dotenv import load_dotenv
load_dotenv()

model_name = os.getenv("MODEL_NAME")
llm_api_key = os.getenv("GROQ_API_KEY")


from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# Base LLM (Groq model)
llm = ChatGroq(temperature=0.0, model_name=model_name)

#  System Prompt
system_prompt = "You are a helpful assistant called Zeta."

#  Prompt Template with History Slot
prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(system_prompt),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{query}"),
])

#  Create runnable pipeline (prompt → LLM)
pipeline = prompt_template | llm

#  Session-based Chat History Storage (for multiple users/bots)
chat_map = {}  # Dictionary: session_id → chat history

def get_chat_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in chat_map:
        chat_map[session_id] = InMemoryChatMessageHistory()
    return chat_map[session_id]

#  Attach RunnableWithMessageHistory
pipeline_with_history = RunnableWithMessageHistory(
    pipeline,
    get_session_history=get_chat_history,
    input_messages_key="query",
    history_messages_key="history"
)

#  Testing Conversation
session_id = "user_123"  # Simulating unique user session (replace with IG user_id)
response = pipeline_with_history.invoke(
    {"query": "Hello, I'm Jonathan."},
    config={"session_id": session_id}
)
print("Zeta:", response)

response = pipeline_with_history.invoke(
    {"query": "What did I just tell you?"},
    config={"session_id": session_id}
)
print("Zeta:", response.content)
