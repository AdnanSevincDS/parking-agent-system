from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PROMPTS_DIR = PROJECT_ROOT / "src" / "parking_agent_system" / "prompt-templates"


class Settings(BaseSettings):
    """Application configuration — defaults work out of the box. Override via environment variables or a .env file if needed."""

    environment: str = Field(
        default="development",
        validation_alias="ENVIRONMENT",
    )

    # Database configuration
    sqlite_db_path: Path = Field(
        default=DATA_DIR / "parking.db",
        validation_alias="SQLITE_DB_PATH",
    )
    milvus_db_path: Path = Field(
        default=DATA_DIR / "milvus_parking.db",
        validation_alias="MILVUS_DB_PATH",
    )

    # Ollama configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
    )

    model: str = Field(
        default="qwen2.5:7b",
        validation_alias="LLM",
    )

    model_eval: str = Field(
        default="qwen2.5:7b",
        validation_alias="LLM_EVAL",
    )

    llm_context_window: int = Field(
        default=8192,
        validation_alias="LLM_CONTEXT_WINDOW",
    )

    llm_max_output_tokens: int = Field(
        default=2048,
        validation_alias="LLM_MAX_OUTPUT_TOKENS",
    )

    user_system_prompt_path: Path = Field(
        default=PROMPTS_DIR / "user_system_prompt.txt",
        validation_alias="USER_SYSTEM_PROMPT_PATH",
    )

    admin_system_prompt_path: Path = Field(
        default=PROMPTS_DIR / "admin_system_prompt.txt",
        validation_alias="ADMIN_SYSTEM_PROMPT_PATH",
    )

    # RAG tuning
    embedding_model: str = Field(
        default="nomic-embed-text:latest",
        validation_alias="EMBEDDING_MODEL",
    )
    temperature: float = Field(
        default=0.0,
        validation_alias="TEMPERATURE",
    )
    top_k: int = Field(
        default=3,
        validation_alias="TOP_K",
    )
    chunk_size: int = Field(
        default=500,
        validation_alias="CHUNK_SIZE",
    )
    chunk_overlap: int = Field(
        default=50,
        validation_alias="CHUNK_OVERLAP",
    )

    @field_validator("sqlite_db_path", "milvus_db_path", mode="before")
    @classmethod
    def resolve_project_relative_paths(cls, value: str | Path) -> Path:
        """Resolve database paths relative to the repository root."""
        path = Path(value)
        return path if path.is_absolute() else PROJECT_ROOT / path

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )


settings = Settings()