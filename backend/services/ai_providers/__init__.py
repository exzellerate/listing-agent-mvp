"""
Provider-agnostic AI layer.

Everything the app needs from an LLM (image analysis, eBay category/aspect
suggestion, pricing research) goes through the `AIProvider` interface in
`base.py`, so a new vendor can be added without touching call sites in
main.py. Selection is a single global env var, not a per-user/per-request
setting — see CLAUDE.md.
"""
import os
import logging

logger = logging.getLogger(__name__)

_provider_instance = None


def get_provider():
    """Return the singleton AIProvider selected by the AI_PROVIDER env var.

    Defaults to "claude" (production default). Set AI_PROVIDER=gemini to
    switch. The instance is cached for the process lifetime, same as the
    existing get_analyzer()/get_pricing_researcher() factories.
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("AI_PROVIDER", "claude").strip().lower()

    if provider_name == "claude":
        from services.ai_providers.claude_provider import ClaudeProvider
        _provider_instance = ClaudeProvider()
    elif provider_name == "gemini":
        from services.ai_providers.gemini_provider import GeminiProvider
        _provider_instance = GeminiProvider()
    else:
        raise ValueError(
            f"Unknown AI_PROVIDER '{provider_name}' — expected 'claude' or 'gemini'"
        )

    logger.info(f"AI provider selected: {provider_name}")
    return _provider_instance
