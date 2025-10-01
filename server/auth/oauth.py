"""Google OAuth 2.0 with PKCE implementation."""
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import httpx
from server.config import settings
from server.storage import storage


class OAuthManager:
    """Manage Google OAuth 2.0 flow with PKCE."""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scopes = settings.GOOGLE_SCOPES
        
        # Google OAuth endpoints
        self.auth_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo"
        
        # In-memory storage for PKCE challenges (in production, use Redis)
        self._pkce_store: Dict[str, Dict[str, str]] = {}
    
    def generate_pkce(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code challenge (SHA256 hash of verifier)
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_authorization_url(self) -> tuple[str, str]:
        """Generate authorization URL and state."""
        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = self.generate_pkce()
        
        # Store PKCE values for later verification
        self._pkce_store[state] = {
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
        }
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent to get refresh token
        }
        
        url = f"{self.auth_endpoint}?{urlencode(params)}"
        return url, state
    
    async def exchange_code(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens."""
        # Get PKCE verifier
        pkce_data = self._pkce_store.get(state)
        if not pkce_data:
            raise ValueError("Invalid state or PKCE data not found")
        
        code_verifier = pkce_data["code_verifier"]
        
        # Clean up PKCE store
        del self._pkce_store[state]
        
        # Exchange code for tokens
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_endpoint, data=data)
            response.raise_for_status()
            tokens = response.json()
            
            # Get user info
            access_token = tokens["access_token"]
            userinfo = await self._get_userinfo(access_token)
            
            # Save tokens to storage
            expires_in = tokens.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            await storage.save_user_tokens(
                user_sub=userinfo["sub"],
                user_email=userinfo.get("email", ""),
                access_token=access_token,
                refresh_token=tokens.get("refresh_token", ""),
                expires_at=expires_at
            )
            
            return {
                "user_sub": userinfo["sub"],
                "user_email": userinfo.get("email", ""),
                "user_name": userinfo.get("name", ""),
                "tokens": tokens,
            }
    
    async def _get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Google."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(self, user_sub: str) -> Optional[str]:
        """Refresh access token using refresh token."""
        user_tokens = await storage.get_user_tokens(user_sub)
        if not user_tokens or not user_tokens.get("refresh_token"):
            return None
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": user_tokens["refresh_token"],
            "grant_type": "refresh_token",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.token_endpoint, data=data)
                response.raise_for_status()
                tokens = response.json()
                
                # Update stored tokens
                access_token = tokens["access_token"]
                expires_in = tokens.get("expires_in", 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                await storage.save_user_tokens(
                    user_sub=user_sub,
                    user_email=user_tokens.get("user_email", ""),
                    access_token=access_token,
                    refresh_token=user_tokens.get("refresh_token", ""),
                    expires_at=expires_at
                )
                
                return access_token
            except httpx.HTTPError:
                return None
    
    async def get_valid_access_token(self, user_sub: str) -> Optional[str]:
        """Get a valid access token, refreshing if necessary."""
        user_tokens = await storage.get_user_tokens(user_sub)
        if not user_tokens:
            return None
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(user_tokens["token_expires_at"])
        if datetime.utcnow() >= expires_at - timedelta(minutes=5):
            # Token expired or about to expire, refresh it
            return await self.refresh_access_token(user_sub)
        
        return user_tokens["access_token"]


oauth_manager = OAuthManager()

