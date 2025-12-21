from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import json
import re
from typing import Optional

from ..models.rag import collection, get_best_maternity_guide
from ..models.translator import process_multilingual_query
from Backend.routers.auth_route import connection  # import DB connection

router = APIRouter()

class QueryRequest(BaseModel):
    message: str
    conversation_id: int  # Required: conversation ID for message context


def check_language_override(query: str, detected_language: str) -> str:
    """
    Check if user explicitly requested a specific language in their query.
    
    Examples:
        - "explain in marathi" → mr
        - "हिंदी में बताओ" → hi
        - "தமிழில் சொல்லுங்கள்" → ta
    
    Args:
        query: Original user query
        detected_language: Language detected by langdetect
    
    Returns:
        str: Language code (override if found, otherwise detected_language)
    """
    query_lower = query.lower()
    
    # Language override patterns (phrase → language code)
    language_patterns = {
        # English patterns
        r'\bin\s+marathi\b': 'mr',
        r'\bin\s+hindi\b': 'hi',
        r'\bin\s+tamil\b': 'ta',
        r'\bin\s+telugu\b': 'te',
        r'\bin\s+malayalam\b': 'ml',
        r'\bin\s+gujarati\b': 'gu',
        r'\bin\s+odia\b': 'or',
        r'\bin\s+bengali\b': 'bn',
        r'\bin\s+punjabi\b': 'pa',
        r'\bin\s+kannada\b': 'kn',
        r'\bin\s+assamese\b': 'as',
        r'\bin\s+urdu\b': 'ur',
        r'\bin\s+spanish\b': 'es',
        r'\bin\s+french\b': 'fr',
        r'\bin\s+german\b': 'de',
        
        # Native language patterns
        r'मराठी\s*(मध्ये|मधे)': 'mr',
        r'marathi\s*(madhe|madhye)': 'mr',
        r'हिंदी\s*में': 'hi',
        r'hindi\s*(me|mein)': 'hi',
        r'தமிழில்': 'ta',
        r'తెలుగులో': 'te',
        r'മലയാളത്തിൽ': 'ml',
        r'ગુજરાતીમાં': 'gu',
        r'ଓଡ଼ିଆରେ': 'or',
        r'বাংলায়': 'bn',
        r'ਪੰਜਾਬੀ\s*ਵਿੱਚ': 'pa',
        r'ಕನ್ನಡದಲ್ಲಿ': 'kn',
        r'অসমীয়াত': 'as',
        r'اردو\s*میں': 'ur',
    }
    
    for pattern, lang_code in language_patterns.items():
        if re.search(pattern, query_lower):
            print(f"Language override detected: {lang_code}")
            return lang_code
    
    return detected_language


@router.post("/query_rag/")
async def query_rag(request: Request, data: QueryRequest):
    user_id = None
    
    # First, try to get user info from cookies
    user_cookie = request.cookies.get("user")
    if user_cookie:
        try:
            user_info = json.loads(user_cookie)
            user_id = user_info.get("user_id")
            print(f"User ID from cookie: {user_id}")
        except Exception as e:
            print(f"Error parsing user cookie: {e}")
    
    # If still no user_id, return 401
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated. Please login.")

    print("Final User ID:", user_id)
    print("Original Message:", data.message)
    print("Conversation ID:", data.conversation_id)

    try:
        # Verify conversation belongs to user
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
                (data.conversation_id, user_id)
            )
            conversation = cursor.fetchone()
            
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found or access denied")
        
        # Step 1: Fetch conversation history for context (role-based format)
        # ONLY from this specific conversation, ordered chronologically
        conversation_history = []
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
                LIMIT 20
                """,
                (data.conversation_id,)
            )
            history_rows = cursor.fetchall()
            # Build role-based history list (no pairing)
            for row in history_rows:
                conversation_history.append({
                    "role": row['role'],
                    "content": row['content']
                })
        
        print(f"Loaded {len(conversation_history)} messages for conversation context")
        
        # Step 2: Process multilingual query (detect language and translate to English)
        english_query, detected_language, is_greeting = process_multilingual_query(data.message)
        
        # Step 2.5: Check for explicit language override in the query
        detected_language = check_language_override(data.message, detected_language)
        
        print(f"Detected Language: {detected_language}")
        print(f"English Query: {english_query}")
        print(f"Is Greeting: {is_greeting}")
        
        # Step 3: Query ChromaDB with English query
        results = collection.query(
            query_texts=[english_query],
            n_results=3
        )

        # Step 4: Get the RAG-based response with language parameter and conversation history
        response_text = get_best_maternity_guide(
            query=english_query,
            results=results,
            conversation_history=conversation_history,
            target_language=detected_language,
            is_greeting=is_greeting
        )

        # Step 5: Save message + response to DB with conversation_id
        with connection.cursor() as cursor:
            # Save user message
            cursor.execute(
                "INSERT INTO messages (conversation_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
                (data.conversation_id, user_id, 'user', data.message)
            )
            # Save assistant response
            cursor.execute(
                "INSERT INTO messages (conversation_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
                (data.conversation_id, user_id, 'assistant', response_text)
            )
            connection.commit()
            
            # Update conversation title if it's the first message (title is still "New Chat")
            cursor.execute(
                "SELECT title FROM conversations WHERE id = %s",
                (data.conversation_id,)
            )
            conv = cursor.fetchone()
            if conv and conv['title'] in ['New Chat', 'new chat']:
                # Generate title from first message (first 50 chars)
                title = data.message[:50] + ('...' if len(data.message) > 50 else '')
                cursor.execute(
                    "UPDATE conversations SET title = %s WHERE id = %s",
                    (title, data.conversation_id)
                )
                connection.commit()

        # Step 6: Return response to frontend
        return {"response": response_text, "detected_language": detected_language}

    except Exception as e:
        print(f"Error in RAG query: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Failed to process your query. Please try again."
        )