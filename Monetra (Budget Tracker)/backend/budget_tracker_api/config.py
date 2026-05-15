import os
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")


def _build_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "budget_tracker")
    return (
        "postgresql+psycopg://"
        f"{quote_plus(db_user)}:{quote_plus(db_password)}@"
        f"{db_host}:{db_port}/{db_name}"
    )


class Config:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    SECRET_KEY = os.getenv("SECRET_KEY", "local-dev-secret-change-me")
    DATABASE_URL = _build_database_url()
    LEGACY_SQLITE_PATH = Path(
        os.getenv("LEGACY_SQLITE_PATH", str(PROJECT_ROOT / "budget_tracker.db"))
    )
    GENERATED_REPORTS_DIR = Path(
        os.getenv(
            "GENERATED_REPORTS_DIR",
            str(PROJECT_ROOT / "backend" / "generated_reports"),
        )
    )
    MONTHLY_BUDGET = float(os.getenv("MONTHLY_BUDGET", "0.0"))
    MONTHLY_INCOME = float(os.getenv("MONTHLY_INCOME", "0.0"))
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ]
    DEMO_ACCESS_ENABLED = os.getenv("DEMO_ACCESS_ENABLED", "false").lower() == "true"
    DEMO_ACCESS_USERNAME = os.getenv("DEMO_ACCESS_USERNAME", "")
    DEMO_ACCESS_PASSWORD = os.getenv("DEMO_ACCESS_PASSWORD", "")
    LOGIN_REQUIRED = os.getenv("LOGIN_REQUIRED", "true").lower() == "true"
    AUTH_USERNAME = os.getenv("AUTH_USERNAME", "Rushabh")
    AUTH_PASSWORD_HASH = os.getenv("AUTH_PASSWORD_HASH", "")
    READ_ONLY_MODE = os.getenv("READ_ONLY_MODE", "false").lower() == "true"
    PUBLIC_HEALTHCHECK_ENABLED = os.getenv("PUBLIC_HEALTHCHECK_ENABLED", "true").lower() == "true"
    EXPOSE_ERROR_DETAILS = os.getenv("EXPOSE_ERROR_DETAILS", "false").lower() == "true"
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "monetra_session")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE_PATH = Path(
        os.getenv("LOG_FILE_PATH", str(PROJECT_ROOT / "backend" / ".run" / "monetra.log"))
    )
    LOG_TIMEZONE = os.getenv("LOG_TIMEZONE", "Europe/London")
    AGENT_MEMORY_PATH = Path(
        os.getenv("AGENT_MEMORY_PATH", str(PROJECT_ROOT / "backend" / ".run" / "agent_memory.json"))
    )
    RAG_PERSIST_DIRECTORY = Path(
        os.getenv("RAG_PERSIST_DIRECTORY", str(PROJECT_ROOT / "backend" / ".run" / "chroma"))
    )
    RAG_MANIFEST_PATH = Path(
        os.getenv("RAG_MANIFEST_PATH", str(PROJECT_ROOT / "backend" / ".run" / "rag_manifest.json"))
    )
    RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "monetra_finance_knowledge")
    RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "6"))
    RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "700"))
    RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
    CHROMA_HTTP_HOST = os.getenv("CHROMA_HTTP_HOST", "")
    CHROMA_HTTP_PORT = int(os.getenv("CHROMA_HTTP_PORT", "8000"))
    CHROMA_HTTP_SSL = os.getenv("CHROMA_HTTP_SSL", "false").lower() == "true"
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "1048576"))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "3"))
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=int(os.getenv("SESSION_LIFETIME_HOURS", "12"))
    )
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
    OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "86400"))
    FASTMCP_PYTHON_EXECUTABLE = os.getenv("FASTMCP_PYTHON_EXECUTABLE", sys.executable)
    REPORT_EMAIL_TO = os.getenv("REPORT_EMAIL_TO", "")
    REPORT_EMAIL_RECIPIENT_NAME = os.getenv("REPORT_EMAIL_RECIPIENT_NAME", "Rushabh Dharamshi")
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    AUTOMATION_SCHEDULER_ENABLED = os.getenv("AUTOMATION_SCHEDULER_ENABLED", "false").lower() == "true"
    AUTOMATION_POLL_SECONDS = int(os.getenv("AUTOMATION_POLL_SECONDS", "900"))
    MONTH_END_EMAIL_HOUR = int(os.getenv("MONTH_END_EMAIL_HOUR", "22"))
    MONTH_END_EMAIL_MINUTE = int(os.getenv("MONTH_END_EMAIL_MINUTE", "15"))
