# Simple in-memory conversation store.
# For now it resets every time you restart the server.
# Later we can swap this to Redis or a database.

from datetime import datetime
from backend.database import get_connection

def add_message(conversation_id: str, role: str, content: str, model=None):
    """Add a message to a conversation."""
    timestamp = datetime.now().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    # Ensure conversation exists
    cursor.execute(
        "INSERT OR IGNORE INTO conversations (conversation_id) VALUES (?)",
        (conversation_id,)
    )

    # Insert message
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content, model, timestamp) VALUES (?, ?, ?, ?, ?)",
        (conversation_id, role, content, model, timestamp)
    )

    conn.commit()
    conn.close()
    return timestamp

def get_history(conversation_id: str):
    """Retrieve all messages for a conversation."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role, content, timestamp
        FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
        """,
        (conversation_id,)
    )

    rows = cursor.fetchall()
    conn.close()

    # Convert to list of dicts
    return [{"role": row["role"], "content": row["content"]} for row in rows]

def list_conversations():
    """List all conversations with metadata."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.conversation_id,
            c.created_at,
            COUNT(m.id) as message_count,
            MAX(m.timestamp) as last_message_at
        FROM conversations c
        LEFT JOIN messages m ON c.conversation_id = m.conversation_id
        GROUP BY c.conversation_id 
        ORDER BY last_message_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "conversation_id": row["conversation_id"],
            "created_at": row["created_at"],
            "message_count": row["message_count"],
            "last_message_at": row["last_message_at"]
        }
        for row in rows
    ]

def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    conn = get_connection()
    cursor = conn.cursor()

    # Delete messages first (foreign key constraint)
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))


    # Delete conversation
    cursor.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted_count > 0

def cleanup_old_conversations(days_old: int = 30):
    """Delete conversations older than specificed days."""
    conn = get_connection()
    cursor = conn.cursor()

    # Find old conversations IDs
    cursor.execute("""
        SELECT conversation_id
        FROM conversations
        WHERE created_at < datetime('now', '-' || ? || ' days')
    """, (days_old,))

    old_conversations = [row["conversation_id"] for row in cursor.fetchall()]

    if not old_conversations:
        conn.close()
        return 0

    # Delete their messages
    placeholders = ','.join('?' * len(old_conversations))
    cursor.execute(
        f"DELETE FROM conversations WHERE conversation_id IN {placeholders}",
        old_conversations
    )

    # Delete the conversations
    cursor.execute(
        f"DELETE FROM conversations WHERE conversation_id IN {placeholders}",
        old_conversations
    )

    deleted_count = len(old_conversations)
    conn.commit()
    conn.close()

    return deleted_count