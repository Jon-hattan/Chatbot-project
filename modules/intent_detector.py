from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from modules.context_loader import load_context

class IntentDetector:
    """Modular intent detector using LLM-based classification."""

    def __init__(self, llm, intent_prompt_path: str):
        """
        Initialize the intent detector with an LLM and prompt template.

        Args:
            llm: Any LangChain-compatible LLM (e.g., ChatGroq)
            intent_prompt_path: Path to the intent classification prompt file
        """
        self.llm = llm
        self.chain = self._build_chain(intent_prompt_path)

    def _build_chain(self, intent_prompt_path: str):
        """Load the intent classification prompt and return an LLM chain."""
        intent_text = load_context(intent_prompt_path)
        intent_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(intent_text),
            HumanMessagePromptTemplate.from_template("{input}")
        ])
        return intent_prompt | self.llm

    def detect(self, message: str) -> bool:
        """
        Detect if the message matches the configured intent.

        Args:
            message: The user's message to classify

        Returns:
            True if intent is detected, False otherwise
        """
        result = self.chain.invoke({"input": message}).content.strip().upper()

        # Sanitize output - default to False if unclear
        if "YES" in result:
            return True
        else:
            return False
