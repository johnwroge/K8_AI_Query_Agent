"""
Configuration module for Kubernetes AI Query Agent.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-3.5-turbo"
    openai_temperature: float = 0.0
    openai_max_tokens: Optional[int] = None
    
    # Application Configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False
    log_level: str = "INFO"
    log_file: str = "agent.log"
    
    # Kubernetes Configuration
    k8s_namespace_filter: Optional[str] = None
    k8s_max_resources_per_type: int = 50
    
    # Rate Limiting
    enable_rate_limiting: bool = False
    rate_limit_per_minute: int = 60
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


settings = get_settings()