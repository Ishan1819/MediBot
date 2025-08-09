from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from Backend.routers.auth_route import connection
import json

router = APIRouter()

class HistoryRequest(BaseModel):
    num_messages: int  # number of message-response pairs to fetch


@router.post("/get_history/")
async def get_history(request: Request, data: HistoryRequest):
    # Extract user info from cookies
    user_cookie = request.cookies.get("user")
    if not user_cookie:
        raise HTTPException(status_code=401, detail="User not authenticated. Please login.")

    try:
        user_info = json.loads(user_cookie)
        user_id = user_info.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user cookie. Please login again.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user cookie format. Please login again.")

    # Validate num_messages
    if data.num_messages <= 0:
        raise HTTPException(status_code=400, detail="num_messages must be a positive integer")

    try:
        with connection.cursor() as cursor:
            # Fetch last N messages (message+response) for the user, ordered newest first
            cursor.execute(
                """
                SELECT message, response, created_at
                FROM messages
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, data.num_messages)
            )
            rows = cursor.fetchall()

        # Reverse to chronological order (oldest first)
        rows.reverse()

        # Format results
        history = [
            {
                "message": row["message"],
                "response": row["response"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            }
            for row in rows
        ]

        return {"history": history}

    except Exception as e:
        print(f"Error fetching chat history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch chat history. Please try again later."
        )
