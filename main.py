from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.database import init_db
from backend.conversation_store import (
    add_message,
    get_history,
    list_conversations,
    delete_conversation,
    cleanup_old_conversations,
)

from app.routes import router as api_router
app = FastAPI()

@app.on_event("startup")
def startup_event():
    init_db()

# Allow your frontend (PyCharm's localhost port) to talk to the API
origins = [
    "http://127.0.0.1:8000",
    "http://localhost:63343",
    "http://127.0.0.1:63343",
    "http://localhost:63342",
    "http://localhost:63344",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def root():
    return {"message": "Multi-LLM Relay API is running."}

@app.get("/conversations")
def get_conversations():
    """"List all conversations with metadata."""
    try:
        conversations = list_conversations()
        return {"conversations": conversations}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/conversations/{conversation_id}")
def remove_conversation(conversation_id: str):
    """Delete a specific conversation."""
    try:
        deleted = delete_conversation(conversation_id)
        if deleted:
            return {"message": f"Conversation {conversation_id} deleted"}
        else:
            return {"error": "Conversation not found"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/cleanup")
def cleanup_conversations_endpoint(days_old: int = 30):
    """Delete conversations older than specified days."""
    try:
        deleted_count = cleanup_old_conversations(days_old)
        return {"message": f"Deleted {deleted_count} old conversations"}
    except Exception as e:
        return {"error": str(e)}

# Attach all routes from app/routes.py
app.include_router(api_router)

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/ui")
def serve_frontend():
    return FileResponse("frontend/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)