import os
from dotenv import load_dotenv
from anthropic import AsyncAnthropic
from backend.conversation_store import get_history, add_message

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest")

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def ask_claude(prompt: str, conversation_id: str | None = None) -> str:
    """
    Send a prompt to Claude and return the text response (async version).
    """
    if not prompt:
        return "Prompt was empty."

    if not ANTHROPIC_API_KEY:
        return "Claude API key not configured. Please set ANTHROPIC_API_KEY in .env."

    # Build the logical history in our internal format
    history_messages: list[dict] = []
    if conversation_id:
        history_messages = get_history(conversation_id)

    # Add the new user message
    history_messages.append({"role": "user", "content": prompt})

    # Now adapt to Anthropic's expected format
    anthro_messages: list[dict] = []
    for msg in history_messages:
        if not isinstance(msg.get("content"), str):
            continue
        if not msg.get("content"):
            continue

        anthro_messages.append({
            "role": msg["role"],
            "content": [
                {"type": "text", "text": msg["content"]}
            ],
        })

    try:
        message = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            messages=anthro_messages,
        )

        # Extract the first text block from Claude's response
        answer = ""
        for block in message.content:
            if block.type == "text":
                answer = block.text
                break

        if not answer:
            answer = "Claude did not return any text content."

        # Save back into our shared conversation store
        if conversation_id:
            add_message(conversation_id, "user", prompt)
            add_message(conversation_id, "assistant", answer, model=CLAUDE_MODEL)

        return answer

    except Exception as e:
        # log the full error for debugging
        error_str = repr(e)
        print("Error calling Claude:", error_str)

        # Friendly messages for common cases
        if "authentication_error" in error_str or "invalid x-api-key" in error_str:
            return "Claude is not available right now (invalid or missing API key)."

        return "Claude is currently unavailable due to an internal error. Please try again later."


async def chat(user_message: str, conversation_history: list = None, model: str = CLAUDE_MODEL) -> str:
    """
    Simpler async function for comparison mode.
    Takes history directly instead of fetching from DB.
    """
    # Build Anthropic-formatted messages
    anthro_messages = []

    # Add conversation history if provided
    if conversation_history:
        for msg in conversation_history:
            if isinstance(msg.get("content"), str) and msg.get("content"):
                anthro_messages.append({
                    "role": msg["role"],
                    "content": [{"type": "text", "text": msg["content"]}]
                })

    # Add current user message
    anthro_messages.append({
        "role": "user",
        "content": [{"type": "text", "text": user_message}]
    })

    try:
        message = await client.messages.create(
            model=model,
            max_tokens=512,
            messages=anthro_messages
        )

        # Extract text from response
        for block in message.content:
            if block.type == "text":
                return block.text

        return "Claude did not return any text content."

    except Exception as e:
        error_str = repr(e)
        print("Error calling Claude:", error_str)
        return "Claude error"