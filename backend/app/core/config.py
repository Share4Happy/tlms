"""
TLMS Application Configuration
Loads settings from environment variables
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "TLMS"
    APP_ENV: str = "development"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tlms"
    
    # S4H Auth Service - Identity Provider
    S4H_AUTH_BASE_URL: str = "http://api-auth.aisteamx.edu.vn"

    # LHU External API
    LHU_API_BASE_URL: str = "https://tapi.lhu.edu.vn"

    # LHU MySQL Database (for Student ID Sync)
    LHU_MYSQL_HOST: str = "103.130.216.74"
    LHU_MYSQL_PORT: int = 3306
    LHU_MYSQL_USER: str = "hmcdat_public"
    LHU_MYSQL_PASSWORD: str = "3)3@3or#yFT&)Sr0"
    LHU_MYSQL_DATABASE: str = "hmcdat_public"

    # Webhook Security - API Key for S4H check-in webhook
    WEBHOOK_API_KEY: str = ""

    # MongoDB (for User Import from S4H)
    MONGODB_CONNECTION_STRING: str = ""
    MONGODB_DATABASE: str = "checkin_service"
    MONGODB_USERS_COLLECTION: str = "users"

    # User Import Security - Secret Token for admin operations
    USER_IMPORT_SECRET_TOKEN: str = ""

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080,https://tlms.talab.io.vn,https://tlms-backend.talab.io.vn"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

settings = get_settings()

