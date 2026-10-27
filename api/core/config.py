from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "SismoWatch"
    ENVIRONMENT: str = "production"
    
    # PostgreSQL Configuration
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5432))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "sismowatch")
    
    # Application Read-Only User (Principio de Mínimo Privilegio - PDF Pág. 5)
    SISMO_APP_USER: str = os.getenv("SISMO_APP_USER", "sismo_app_readonly")
    SISMO_APP_PASSWORD: str = os.getenv("SISMO_APP_PASSWORD", "readonly_app_secret_2026")
    
    # Master Admin credentials (for migrations/seeding if needed)
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres_master_secret_2026")
    
    # Database URLs
    @property
    def READONLY_DATABASE_URL(self) -> str:
        return f"postgresql://{self.SISMO_APP_USER}:{self.SISMO_APP_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        
    @property
    def ADMIN_DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "baa52f74fb2963994ed09af14b08ee64715c8e5c50622b8cd703abe59738ff07")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

    # Seed User Credentials
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "SismoAdmin2026!Secret")
    VIEWER_USERNAME: str = os.getenv("VIEWER_USERNAME", "viewer")
    VIEWER_PASSWORD: str = os.getenv("VIEWER_PASSWORD", "SismoViewer2026!")

    # AI Configuration (Dual Engine)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)

    # OpenMetadata
    OPENMETADATA_SERVER_URL: str = os.getenv("OPENMETADATA_SERVER_URL", "http://openmetadata-viewer:8585")

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
