from app.llm_clients.openai_client import ask_openai
from app.llm_clients.claude_client import ask_claude


async def route_to_model(model_name: str, prompt: str, conversation_id: str | None) -> str:
    """
    Simple model router for multiple LLM backends (async version).
    More models (Claude, Gemini) will be added later.
    """
    model_name = model_name.lower()

    if model_name in ("openai", "gpt", "gpt-4", "gpt-4o", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"):
        return await ask_openai(prompt, conversation_id)

    if model_name in ("claude", "claude-3", "claude-3-5"):
        return await ask_claude(prompt, conversation_id)

    # Placeholder for upcoming models - this keeps app stable
    return f"Model '{model_name}' not supported yet."