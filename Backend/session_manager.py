"""
Server-side session management for secure authentication.
Stores session_id -> user_id mappings in memory.
In production, use Redis or a database table for persistence.
"""

import secrets
from typing import Optional, Dict
from datetime import datetime, timedelta


class SessionManager:
    """
    Manages user sessions with session_id -> user_id mapping.
    Sessions expire after inactivity.
    """
    
    def __init__(self, session_timeout_hours: int = 24):
        self._sessions: Dict[str, Dict] = {}
        self.session_timeout = timedelta(hours=session_timeout_hours)
    
    def create_session(self, user_id: int, email: str) -> str:
        """
        Create a new session for a user.
        Invalidates any existing sessions for this user.
        
        Args:
            user_id: User ID from database
            email: User email
            
        Returns:
            session_id: Unique session identifier
        """
        # Generate secure random session ID
        session_id = secrets.token_urlsafe(32)
        
        # Invalidate old sessions for this user
        self._invalidate_user_sessions(user_id)
        
        # Store session
        self._sessions[session_id] = {
            "user_id": user_id,
            "email": email,
            "created_at": datetime.now(),
            "last_activity": datetime.now()
        }
        
        print(f"✅ Created session {session_id[:8]}... for user {user_id}")
        return session_id
    
    def get_user_id(self, session_id: str) -> Optional[int]:
        """
        Get user_id from session_id.
        Returns None if session is invalid or expired.
        
        Args:
            session_id: Session identifier
            
        Returns:
            user_id or None
        """
        if not session_id or session_id not in self._sessions:
            return None
        
        session = self._sessions[session_id]
        
        # Check if session expired
        if datetime.now() - session["last_activity"] > self.session_timeout:
            print(f"⏰ Session {session_id[:8]}... expired")
            self.invalidate_session(session_id)
            return None
        
        # Update last activity
        session["last_activity"] = datetime.now()
        
        return session["user_id"]
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """
        Get full session information.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session dict or None
        """
        user_id = self.get_user_id(session_id)
        if user_id is None:
            return None
        
        return self._sessions.get(session_id)
    
    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a specific session (logout).
        
        Args:
            session_id: Session to invalidate
            
        Returns:
            True if session was found and deleted
        """
        if session_id in self._sessions:
            user_id = self._sessions[session_id]["user_id"]
            del self._sessions[session_id]
            print(f"🗑️ Invalidated session {session_id[:8]}... for user {user_id}")
            return True
        return False
    
    def _invalidate_user_sessions(self, user_id: int):
        """
        Invalidate all sessions for a specific user.
        Used during login to prevent multiple sessions.
        
        Args:
            user_id: User ID
        """
        sessions_to_delete = [
            sid for sid, session in self._sessions.items()
            if session["user_id"] == user_id
        ]
        
        for sid in sessions_to_delete:
            del self._sessions[sid]
            print(f"🗑️ Invalidated old session {sid[:8]}... for user {user_id}")
    
    def cleanup_expired_sessions(self):
        """
        Remove all expired sessions.
        Should be called periodically.
        """
        now = datetime.now()
        expired = [
            sid for sid, session in self._sessions.items()
            if now - session["last_activity"] > self.session_timeout
        ]
        
        for sid in expired:
            user_id = self._sessions[sid]["user_id"]
            del self._sessions[sid]
            print(f"🧹 Cleaned up expired session {sid[:8]}... for user {user_id}")
        
        if expired:
            print(f"🧹 Cleaned up {len(expired)} expired sessions")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)


# Global session manager instance
session_manager = SessionManager(session_timeout_hours=24)
