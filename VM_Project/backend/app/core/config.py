"""Core application configuration using Pydantic Settings (v2)."""

import os
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "VM_project - Insurance Customer Intelligence Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev-secret-key-vm-insurance-platform"

    # Server Binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Database URLs
    DATABASE_URL: str = "sqlite+aiosqlite:///./vm_project.db"
    SYNC_DATABASE_URL: str = "sqlite:///./vm_project.db"

    # Google Gemini AI Settings
    # Modern google-genai SDK models
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_ANALYSIS_MODEL: str = "gemini-3.8-flash"
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_MAX_OUTPUT_TOKENS: int = 2048

    # Gemini Timeout Settings (milliseconds)
    GEMINI_TIMEOUT_MS: int = 120000
    GEMINI_CONNECTIVITY_TIMEOUT_MS: int = 30000
    GEMINI_MAX_RETRIES: int = 3

    # RAG & Knowledge Base Settings (separate from generation model config)
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    RAG_UPLOAD_DIR: str = "./uploaded_knowledge_docs"
    RAG_MAX_FILE_SIZE_MB: int = 20
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 5
    RAG_RELEVANCE_THRESHOLD: float = 0.45

    # AI Business Rules & Thresholds
    PROACTIVE_SCAN_BATCH_SIZE: int = 25
    ATTENTION_SCORE_THRESHOLD: float = 45.0

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
