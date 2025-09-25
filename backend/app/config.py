"""Application configuration settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./cartelem.db"
    
    # Application
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Logging
    log_level: str = "INFO"
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings: Application settings.
    """
    return Settings()


# Global settings instance
settings = get_settings()
