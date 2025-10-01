"""Configuration management for the MCP server."""
import os
import secrets
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Server configuration from environment variables."""
    
    # Server
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")
    
    # OpenWeatherMap API
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    
    # JWT/Session
    JWT_SIGNING_KEY: str = os.getenv("JWT_SIGNING_KEY", secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = "HS256"
    SESSION_DURATION_HOURS: int = 24
    
    # Storage
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    
    # OAuth Scopes
    GOOGLE_SCOPES: list[str] = [
        "openid",
        "profile",
        "email",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.readonly",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

