from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import json
from typing import Optional, List
from datetime import datetime

from Backend.routers.auth_route import connection

router = APIRouter()


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Chat"


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: str


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: str


@router.post("/conversations/create")
async def create_conversation(request: Request, data: CreateConversationRequest):
    """
    Create a new conversation for the authenticated user.
    """
    # Extract user_id from cookie
    user_cookie = request.cookies.get("user")
    if not user_cookie:
        raise HTTPException(status_code=401, detail="User not authenticated. Please login.")
    
    try:
        user_info = json.loads(user_cookie)
        user_id = user_info.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user cookie.")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid user cookie format.")
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO conversations (user_id, title) VALUES (%s, %s)",
                (user_id, data.title)
            )
            connection.commit()
            
            # Get the created conversation
            conversation_id = cursor.lastrowid
            cursor.execute(
                "SELECT id, user_id, title, created_at FROM conversations WHERE id = %s",
                (conversation_id,)
            )
            conversation = cursor.fetchone()
            
            return {
                "id": conversation["id"],
                "user_id": conversation["user_id"],
                "title": conversation["title"],
                "created_at": str(conversation["created_at"])
            }
    
    except Exception as e:
        print(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@router.get("/conversations/list")
async def list_conversations(request: Request):
    """
    List all conversations for the authenticated user.
    """
    # Extract user_id from cookie
    user_cookie = request.cookies.get("user")
    if not user_cookie:
        raise HTTPException(status_code=401, detail="User not authenticated. Please login.")
    
    try:
        user_info = json.loads(user_cookie)
        user_id = user_info.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user cookie.")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid user cookie format.")
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, title, created_at 
                FROM conversations 
                WHERE user_id = %s 
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            conversations = cursor.fetchall()
            
            return {
                "conversations": [
                    {
                        "id": conv["id"],
                        "user_id": conv["user_id"],
                        "title": conv["title"],
                        "created_at": str(conv["created_at"])
                    }
                    for conv in conversations
                ]
            }
    
    except Exception as e:
        print(f"Error listing conversations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list conversations")


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int, request: Request):
    """
    Get all messages for a specific conversation.
    """
    # Extract user_id from cookie
    user_cookie = request.cookies.get("user")
    if not user_cookie:
        raise HTTPException(status_code=401, detail="User not authenticated. Please login.")
    
    try:
        user_info = json.loads(user_cookie)
        user_id = user_info.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user cookie.")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid user cookie format.")
    
    try:
        with connection.cursor() as cursor:
            # Verify conversation belongs to user
            cursor.execute(
                "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
                (conversation_id, user_id)
            )
            conversation = cursor.fetchone()
            
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found or access denied")
            
            # Fetch messages
            cursor.execute(
                """
                SELECT id, conversation_id, role, content, created_at 
                FROM messages 
                WHERE conversation_id = %s 
                ORDER BY created_at ASC
                """,
                (conversation_id,)
            )
            messages = cursor.fetchall()
            
            return {
                "messages": [
                    {
                        "id": msg["id"],
                        "conversation_id": msg["conversation_id"],
                        "role": msg["role"],
                        "content": msg["content"],
                        "created_at": str(msg["created_at"])
                    }
                    for msg in messages
                ]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching messages: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch messages")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, request: Request):
    """
    Delete a conversation and all its messages.
    """
    # Extract user_id from cookie
    user_cookie = request.cookies.get("user")
    if not user_cookie:
        raise HTTPException(status_code=401, detail="User not authenticated. Please login.")
    
    try:
        user_info = json.loads(user_cookie)
        user_id = user_info.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user cookie.")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid user cookie format.")
    
    try:
        with connection.cursor() as cursor:
            # Verify conversation belongs to user
            cursor.execute(
                "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
                (conversation_id, user_id)
            )
            conversation = cursor.fetchone()
            
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found or access denied")
            
            # Delete messages first (if not using CASCADE)
            cursor.execute(
                "DELETE FROM messages WHERE conversation_id = %s",
                (conversation_id,)
            )
            
            # Delete conversation
            cursor.execute(
                "DELETE FROM conversations WHERE id = %s",
                (conversation_id,)
            )
            connection.commit()
            
            return {"message": "Conversation deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")
