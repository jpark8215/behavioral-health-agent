"""
Configuration management for behavioral health application
Centralizes all configuration with validation and type safety
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Application
    app_name: str = "Behavioral Health Session Summarization Agent"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    host: str = "0.0.0.0"
    port: int = Field(default=8001, ge=1024, le=65535)
    allowed_origins: str = "http://localhost:3000,http://localhost:8000,http://localhost:8001"
    
    # Database
    postgres_host: str = "localhost"
    postgres_port: int = Field(default=5432, ge=1024, le=65535)
    postgres_user: str = "postgres"
    postgres_password: str
    postgres_db: str = "postgres"
    postgres_pool_min_size: int = Field(default=2, ge=1)
    postgres_pool_max_size: int = Field(default=10, ge=1)
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = Field(default=6379, ge=1024, le=65535)
    redis_url: Optional[str] = None
    redis_ttl: int = Field(default=3600, ge=60)
    
    # Ollama (Optional)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b"
    ollama_timeout: int = Field(default=120, ge=10, le=300)
    ollama_enabled: bool = True
    
    # Whisper
    whisper_model_size: str = Field(default="base", pattern="^(tiny|base|small|medium|large)$")
    
    # File Upload
    max_file_size_mb: int = Field(default=50, ge=1, le=500)
    max_audio_duration_seconds: int = Field(default=3600, ge=60)
    allowed_audio_types: list = ["audio/wav", "audio/mpeg", "audio/mp4", "audio/m4a", "audio/webm"]
    
    # Security
    enable_cors: bool = True
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
    @validator("redis_url", pre=True, always=True)
    def build_redis_url(cls, v, values):
        """Build Redis URL from components if not provided"""
        if v:
            return v
        host = values.get("redis_host", "localhost")
        port = values.get("redis_port", 6379)
        return f"redis://{host}:{port}"
    
    @validator("postgres_password")
    def validate_password(cls, v):
        """Ensure password is set and meets minimum requirements"""
        if not v or len(v) < 8:
            raise ValueError("POSTGRES_PASSWORD must be at least 8 characters")
        return v
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes"""
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def cors_origins(self) -> list:
        """Parse CORS origins"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def database_url(self) -> str:
        """Build database URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
