from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PROMPTS_DIR = PROJECT_ROOT / "src" / "parking_agent_system" / "prompt-templates"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env."""

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
    
    parking_capacity: int = Field(
        default=20,
        gt=0,
        validation_alias="PARKING_CAPACITY",
    )

    system_prompt_path: Path = Field(
        default=PROMPTS_DIR / "prompt.txt",
        validation_alias="SYSTEM_PROMPT_PATH",
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