from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from modules.context_loader import load_context

class ConversationAgent:
    """Handles natural conversational responses using LLM with flow rules."""

    def __init__(self, llm, business_config: dict, session_manager, flow_rules_path: str = "config/flow_rules.txt"):
        """
        Initialize the conversation agent.

        Args:
            llm: Any LangChain-compatible LLM
            business_config: Business configuration dict with context
            session_manager: SessionManager instance for chat history
            flow_rules_path: Path to the flow rules file
        """
        self.llm = llm
        self.business_config = business_config
        self.session_manager = session_manager
        self.flow_rules_path = flow_rules_path
        self.conversation_chain = self._build_chain()

    def _build_chain(self):
        """Build the conversational prompt chain with flow rules."""
        # Load flow rules
        flow_rules = load_context(self.flow_rules_path)

        # Get business details
        business_name = self.business_config.get("business_name", "our business")
        bot_name = self.business_config.get("bot_name", "AI Assistant")
        business_description = self.business_config.get("business_description", "")

        system_prompt = f"""{flow_rules}

BUSINESS INFORMATION:
{business_description}

Remember:
- You are {bot_name} from {business_name}
- Follow the flow rules STRICTLY
- Ask ONE question at a time
- Keep responses SHORT (1-2 sentences unless listing options)
- Always guide toward booking a $10 trial
- Be warm, cheerful, use emojis 😊✨🎤"""

        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])

        return prompt | self.llm

    def get_response(self, session_id: str, message: str) -> str:
        """
        Generate a conversational response to user's message.

        Args:
            session_id: Unique identifier for the conversation session
            message: User's message

        Returns:
            AI-generated conversational response
        """
        # Get chat history for this session
        history = self.session_manager.get_history(session_id)

        # Get session state
        state = self.session_manager.get_state(session_id)

        # Increment message counter
        message_count = state.get("message_count", 0) + 1
        state["message_count"] = message_count
        self.session_manager.set_state(session_id, state)

        # Check if we should suggest booking this time
        booking_freq = self.business_config.get("conversation", {}).get("booking_suggestion_frequency", 0)
        should_suggest = booking_freq > 0 and message_count % booking_freq == 0

        # Add context hint to the input if it's time to suggest booking
        context_hint = ""
        if should_suggest:
            context_hint = "\n[INTERNAL NOTE: Consider casually suggesting booking/trial if appropriate]"

        # Generate response
        response = self.conversation_chain.invoke({
            "input": message + context_hint,
            "history": history.messages
        })

        # Update chat history
        history.add_message(HumanMessage(content=message))
        history.add_message(AIMessage(content=response.content))

        # Trim history to keep it manageable
        self.session_manager.trim_history(session_id)

        return response.content
