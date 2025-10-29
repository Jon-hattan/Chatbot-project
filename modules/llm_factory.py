"""
LLM Factory - Create LLM instances for different providers.

Supports:
- Groq (llama3, mixtral, etc.)
- OpenAI (gpt-4, gpt-3.5-turbo, etc.)
- Anthropic (claude-3-sonnet, claude-3-opus, etc.)
"""

import os
from typing import Optional


def get_llm(provider: str = "groq", model: Optional[str] = None, api_key: Optional[str] = None):
    """
    Get an LLM instance based on provider.

    Args:
        provider: One of "groq", "openai", "anthropic"
        model: Model name (e.g., "llama3-8b-8192", "gpt-4", "claude-3-sonnet-20240229")
        api_key: API key (optional, will try to load from env)

    Returns:
        LangChain LLM instance

    Raises:
        ValueError: If provider is unknown or API key is missing
    """
    provider = provider.lower()

    if provider == "groq":
        return _get_groq_llm(model, api_key)
    elif provider == "openai":
        return _get_openai_llm(model, api_key)
    elif provider == "anthropic":
        return _get_anthropic_llm(model, api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}. Choose from: groq, openai, anthropic")


def _get_groq_llm(model: Optional[str] = None, api_key: Optional[str] = None):
    """Get Groq LLM instance."""
    from langchain_groq import ChatGroq

    # Get API key
    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")

    # Default model
    model = model or "llama3-8b-8192"

    return ChatGroq(
        model=model,
        api_key=api_key,
        temperature=0.2
    )


def _get_openai_llm(model: Optional[str] = None, api_key: Optional[str] = None):
    """Get OpenAI LLM instance."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai not installed. Install with: pip install langchain-openai"
        )

    # Get API key
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Default model
    model = model or "gpt-3.5-turbo"

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=0.2
    )


def _get_anthropic_llm(model: Optional[str] = None, api_key: Optional[str] = None):
    """Get Anthropic LLM instance."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "langchain-anthropic not installed. Install with: pip install langchain-anthropic"
        )

    # Get API key
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    # Default model
    model = model or "claude-3-sonnet-20240229"

    return ChatAnthropic(
        model=model,
        api_key=api_key,
        temperature=0.2
    )


# Model recommendations for each provider
RECOMMENDED_MODELS = {
    "groq": {
        "fast": "llama3-8b-8192",
        "balanced": "mixtral-8x7b-32768",
        "powerful": "llama-3.1-70b-versatile"
    },
    "openai": {
        "fast": "gpt-3.5-turbo",
        "balanced": "gpt-4-turbo-preview",
        "powerful": "gpt-4"
    },
    "anthropic": {
        "fast": "claude-3-haiku-20240307",
        "balanced": "claude-3-sonnet-20240229",
        "powerful": "claude-3-opus-20240229"
    }
}


def get_recommended_model(provider: str, tier: str = "balanced") -> str:
    """
    Get recommended model for a provider.

    Args:
        provider: "groq", "openai", or "anthropic"
        tier: "fast", "balanced", or "powerful"

    Returns:
        Model name string
    """
    provider = provider.lower()
    tier = tier.lower()

    if provider not in RECOMMENDED_MODELS:
        raise ValueError(f"Unknown provider: {provider}")

    if tier not in RECOMMENDED_MODELS[provider]:
        raise ValueError(f"Unknown tier: {tier}. Choose from: fast, balanced, powerful")

    return RECOMMENDED_MODELS[provider][tier]
