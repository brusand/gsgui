"""
Configuration settings for GSGUI Backend
"""

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "GSGUI Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql://gsgui:gsgui@localhost:5432/gsgui"
    TEST_DATABASE_URL: str = "postgresql://gsgui:gsgui@localhost:5432/gsgui_test"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # GuruShots API
    GURUSHOTS_API_BASE: str = "https://api.gurushots.com/rest"
    GURUSHOTS_RATE_LIMIT: int = 10  # requests per second
    
    # Scheduling
    SCHEDULER_TIMEZONE: str = "UTC"
    MAX_CONCURRENT_STRATEGIES: int = 50
    
    # WebSockets
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30  # seconds
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()