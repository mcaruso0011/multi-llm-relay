import logging
import uuid
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

from app.utils.router import route_to_model
from backend import conversation_store
from app.llm_clients import openai_client, claude_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class AskRequest(BaseModel):
    prompt: str
    model: str = "openai"  # default to openai for now
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None


class AskResponse(BaseModel):
    model: str
    conversation_id: Optional[str] = None
    response: str
    history: Optional[List[Dict[str, str]]] = None


@router.post("/ask")
async def ask(request: AskRequest):
    logger.info(
        f"Received request -> "
        f"model: {request.model}, "
        f"conversation_id: {request.conversation_id}, "
        f"user_id: {request.user_id}, "
        f"prompt: {request.prompt}"
    )

    # If prompt is empty, just return history (for loading conversations)
    if not request.prompt or request.prompt.strip() == '':
        history = conversation_store.get_history(request.conversation_id) if request.conversation_id else []
        return AskResponse(
            model=request.model,
            conversation_id=request.conversation_id,
            response="",
            history=history,
        )

    answer = await route_to_model(
        request.model,
        request.prompt,
        request.conversation_id
    )
    return AskResponse(
        model=request.model,
        conversation_id=request.conversation_id,
        response=answer,
    )


@router.post("/compare")
async def compare_models(request: dict):
    """
    Send the same prompt to multiple models in parallel and return all responses.

    Request format:
    {
        "message": "What is the capital of France?",
        "models": ["gpt-4.1", "claude-3-5-sonnet-20241022"],
        "conversation_id": "optional-uuid"
    }

    Returns:
    {
        "conversation_id": "uuid",
        "responses": [
            {"model": "gpt-4", "response": "Paris is...", "timestamp": "..."},
            {"model": "claude-3-5-sonnet-20241022", "response": "The capital...", "timestamp": "..."}
        ]
    }
    """
    message = request.get("message")
    models = request.get("models", [])
    conversation_id = request.get("conversation_id")

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    if not models or len(models) == 0:
        raise HTTPException(status_code=400, detail="At least one model must be specified")

    # Create or use existing conversation
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    # Store the user's message once
    conversation_store.add_message(
        conversation_id=conversation_id,
        role="user",
        content=message,
        model=None
    )

    # Get conversation history (same for all models)
    history = conversation_store.get_history(conversation_id)

    # Create async tasks for each model
    async def query_model(model):
        """Query a single model and return structured result."""
        try:
            # Route to appropriate client
            if "gpt" in model.lower():
                response_text = await openai_client.chat(message, history, model)
            elif "claude" in model.lower():
                response_text = await claude_client.chat(message, history, model)
            else:
                response_text = f"Unknown model: {model}"

            # Store this model's response
            timestamp = conversation_store.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response_text,
                model=model
            )

            return {
                "model": model,
                "response": response_text,
                "timestamp": timestamp
            }
        except Exception as e:
            logger.error(f"Error querying {model}: {e}")
            return {
                "model": model,
                "response": f"Error: {str(e)}",
                "timestamp": None
            }

    # Run all model queries in parallel
    responses = await asyncio.gather(*[query_model(model) for model in models])

    return {
        "conversation_id": conversation_id,
        "responses": responses
    }