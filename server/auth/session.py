"""JWT session management."""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from server.config import settings
from server.storage import storage


class SessionManager:
    """Manage JWT session tokens."""
    
    def __init__(self):
        self.algorithm = settings.JWT_ALGORITHM
        self.secret_key = settings.JWT_SIGNING_KEY
        self.duration_hours = settings.SESSION_DURATION_HOURS
    
    async def create_session(self, user_sub: str, user_email: str) -> str:
        """Create a new session and return JWT token."""
        jti = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=self.duration_hours)
        
        # Save session to database
        await storage.save_session(jti, user_sub, user_email, expires_at)
        
        # Create JWT
        payload = {
            "jti": jti,
            "sub": user_sub,
            "email": user_email,
            "iat": now,
            "exp": expires_at,
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    async def verify_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a session token and return payload if valid."""
        try:
            # Decode JWT
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if session exists and is not revoked
            jti = payload.get("jti")
            if not jti:
                return None
            
            session = await storage.get_session(jti)
            if not session:
                return None
            
            # Check expiration from database
            expires_at = datetime.fromisoformat(session["expires_at"])
            if datetime.utcnow() > expires_at:
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def revoke_session(self, token: str) -> bool:
        """Revoke a session token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            jti = payload.get("jti")
            if jti:
                await storage.revoke_session(jti)
                return True
        except jwt.InvalidTokenError:
            pass
        return False
    
    async def create_exchange_code(self, user_sub: str) -> str:
        """Create a short-lived exchange code (v2 feature)."""
        code = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        await storage.save_exchange_code(code, user_sub, expires_at)
        return code
    
    async def exchange_code_for_session(self, code: str) -> Optional[str]:
        """Exchange a code for a session token."""
        user_sub = await storage.use_exchange_code(code)
        if not user_sub:
            return None
        
        # Get user email from stored tokens
        user_tokens = await storage.get_user_tokens(user_sub)
        user_email = user_tokens.get("user_email", "") if user_tokens else ""
        
        # Create new session
        return await self.create_session(user_sub, user_email)


session_manager = SessionManager()

