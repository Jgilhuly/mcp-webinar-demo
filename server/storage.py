"""Token and session storage using SQLite."""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager


class Storage:
    """Simple SQLite storage for sessions and tokens."""
    
    def __init__(self, db_path: str = "mcp_sessions.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                jti TEXT PRIMARY KEY,
                user_sub TEXT NOT NULL,
                user_email TEXT,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                revoked BOOLEAN DEFAULT 0
            )
        """)
        
        # User tokens table (for Google OAuth refresh tokens)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                user_sub TEXT PRIMARY KEY,
                user_email TEXT,
                access_token TEXT,
                refresh_token TEXT,
                token_expires_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Exchange codes table (v2 feature)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exchange_codes (
                code TEXT PRIMARY KEY,
                user_sub TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def save_session(self, jti: str, user_sub: str, user_email: str, expires_at: datetime):
        """Save a session."""
        await asyncio.to_thread(self._save_session_sync, jti, user_sub, user_email, expires_at)
    
    def _save_session_sync(self, jti: str, user_sub: str, user_email: str, expires_at: datetime):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO sessions (jti, user_sub, user_email, expires_at) VALUES (?, ?, ?, ?)",
            (jti, user_sub, user_email, expires_at.isoformat())
        )
        conn.commit()
        conn.close()
    
    async def get_session(self, jti: str) -> Optional[Dict[str, Any]]:
        """Get a session by JTI."""
        return await asyncio.to_thread(self._get_session_sync, jti)
    
    def _get_session_sync(self, jti: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE jti = ? AND revoked = 0", (jti,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    async def revoke_session(self, jti: str):
        """Revoke a session."""
        await asyncio.to_thread(self._revoke_session_sync, jti)
    
    def _revoke_session_sync(self, jti: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET revoked = 1 WHERE jti = ?", (jti,))
        conn.commit()
        conn.close()
    
    async def save_user_tokens(self, user_sub: str, user_email: str, access_token: str, 
                                refresh_token: str, expires_at: datetime):
        """Save user's OAuth tokens."""
        await asyncio.to_thread(
            self._save_user_tokens_sync, 
            user_sub, user_email, access_token, refresh_token, expires_at
        )
    
    def _save_user_tokens_sync(self, user_sub: str, user_email: str, access_token: str, 
                                refresh_token: str, expires_at: datetime):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO user_tokens 
               (user_sub, user_email, access_token, refresh_token, token_expires_at, updated_at) 
               VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (user_sub, user_email, access_token, refresh_token, expires_at.isoformat())
        )
        conn.commit()
        conn.close()
    
    async def get_user_tokens(self, user_sub: str) -> Optional[Dict[str, Any]]:
        """Get user's OAuth tokens."""
        return await asyncio.to_thread(self._get_user_tokens_sync, user_sub)
    
    def _get_user_tokens_sync(self, user_sub: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_tokens WHERE user_sub = ?", (user_sub,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    async def save_exchange_code(self, code: str, user_sub: str, expires_at: datetime):
        """Save an exchange code (v2 feature)."""
        await asyncio.to_thread(self._save_exchange_code_sync, code, user_sub, expires_at)
    
    def _save_exchange_code_sync(self, code: str, user_sub: str, expires_at: datetime):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO exchange_codes (code, user_sub, expires_at) VALUES (?, ?, ?)",
            (code, user_sub, expires_at.isoformat())
        )
        conn.commit()
        conn.close()
    
    async def use_exchange_code(self, code: str) -> Optional[str]:
        """Use an exchange code and return the user_sub if valid."""
        return await asyncio.to_thread(self._use_exchange_code_sync, code)
    
    def _use_exchange_code_sync(self, code: str) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if code exists and is valid
        cursor.execute(
            """SELECT user_sub, expires_at, used FROM exchange_codes 
               WHERE code = ?""",
            (code,)
        )
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        user_sub, expires_at_str, used = row
        
        # Check if already used
        if used:
            conn.close()
            return None
        
        # Check if expired
        expires_at = datetime.fromisoformat(expires_at_str)
        if datetime.utcnow() > expires_at:
            conn.close()
            return None
        
        # Mark as used
        cursor.execute("UPDATE exchange_codes SET used = 1 WHERE code = ?", (code,))
        conn.commit()
        conn.close()
        
        return user_sub


# Global storage instance
storage = Storage()

