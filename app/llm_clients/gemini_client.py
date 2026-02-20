import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from backend.conversation_store import get_history, add_message

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


def _build_contents(messages: list[dict]) -> list[types.Content]:
    """Convert internal message format to Gemini's Content format."""
    contents = []
    for msg in messages:
        if not isinstance(msg.get("content"), str) or not msg.get("content"):
            continue
        # Gemini uses "model" instead of "assistant"
        role = "model" if msg["role"] == "assistant" else msg["role"]
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )
    return contents


async def ask_gemini(prompt: str, conversation_id: str | None = None, model: str = DEFAULT_MODEL) -> str:
    if not prompt:
        return "Prompt was empty."

    if not client:
        return "Gemini API key not configured. Please set GEMINI_API_KEY in .env."

    # Build messages list with history
    messages = []
    if conversation_id:
        messages = get_history(conversation_id)
    messages.append({"role": "user", "content": prompt})

    contents = _build_contents(messages)

    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents
        )

        answer = response.text

        if not answer:
            answer = "Gemini did not return any text content."

        # Save messages to conversation store
        if conversation_id:
            add_message(conversation_id, "user", prompt)
            add_message(conversation_id, "assistant", answer, model=model)

        return answer

    except Exception as e:
        error_str = repr(e)
        print("Error calling Gemini:", error_str)

        if "API_KEY_INVALID" in error_str or "invalid" in error_str.lower() and "key" in error_str.lower():
            return "Gemini is not available right now (invalid or missing API key)."

        return "Gemini is currently unavailable due to an internal error."


async def chat(message: str, history: list, model: str = DEFAULT_MODEL) -> str:
    """Simpler interface for comparison mode."""
    if not client:
        return "Gemini API key not configured."

    messages = history + [{"role": "user", "content": message}]
    contents = _build_contents(messages)

    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents
        )
        return response.text or "Gemini did not return any text content."
    except Exception as e:
        error_str = repr(e)
        print("Error calling Gemini:", error_str)
        return "Gemini error"
