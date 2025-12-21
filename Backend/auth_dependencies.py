"""
Authentication dependencies for FastAPI routes.
Validates sessions and extracts user information.
"""

from fastapi import Request, HTTPException
from typing import Dict
from Backend.session_manager import session_manager


def get_current_user(request: Request) -> Dict[str, int]:
    """
    Dependency to get current authenticated user from session.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dict with user_id and email
        
    Raises:
        HTTPException: 401 if session is invalid or missing
    """
    # Extract session_id from cookie
    session_id = request.cookies.get("session_id")
    
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="No active session. Please sign in."
        )
    
    # Validate session and get user_id
    user_id = session_manager.get_user_id(session_id)
    
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please sign in again."
        )
    
    # Get full session info
    session_info = session_manager.get_session_info(session_id)
    
    return {
        "user_id": user_id,
        "email": session_info["email"]
    }


def get_current_user_id(request: Request) -> int:
    """
    Simplified dependency to get only user_id.
    
    Args:
        request: FastAPI request object
        
    Returns:
        user_id
        
    Raises:
        HTTPException: 401 if session is invalid or missing
    """
    user = get_current_user(request)
    return user["user_id"]
