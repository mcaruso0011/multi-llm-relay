from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from backend.conversation_store import get_history, add_message

# Load variables from .env
load_dotenv()

# Create a single OpenAI client instance
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Use OPENAI_MODEL env var if set, otherwise default to gpt-4.1-mini
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


async def ask_openai(prompt: str, conversation_id: str | None = None, model: str = DEFAULT_MODEL) -> str:
    # Build messages list with history
    messages = []

    # Add historical messages
    if conversation_id:
        history = get_history(conversation_id)
        for msg in history:
            messages.append(msg)

    # Add the new user prompt
    messages.append({"role": "user", "content": prompt})

    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=messages
        )

        answer = completion.choices[0].message.content

        # Save messages back into memory store
        if conversation_id:
            add_message(conversation_id, "user", prompt)
            add_message(conversation_id, "assistant", answer, model=model)

        return answer

    except Exception as e:
        # Log full error for debugging
        error_str = repr(e)
        print("Error calling OpenAI:", error_str)

        # Handle common cases with friendly messages
        if "invalid_api_key" in error_str or "Incorrect API key" in error_str:
            return "OpenAI is not available right now (invalid or missing API key)."

        if "insufficient_quota" in error_str or "You exceeded your current quota" in error_str:
            return "OpenAI is not available right now (insufficient quota on the backend)."

        # Fallback generic message
        return "OpenAI is currently unavailable due to an internal error."


async def chat(message: str, history: list, model: str = DEFAULT_MODEL) -> str:
    """Simpler interface for comparison mode."""
    messages = history + [{"role": "user", "content": message}]

    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=messages
        )
        return completion.choices[0].message.content
    except Exception as e:
        error_str = repr(e)
        print("Error calling OpenAI:", error_str)
        return "OpenAI error"


