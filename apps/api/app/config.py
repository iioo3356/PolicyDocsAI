import os
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_PATH = Path(__file__).resolve()
LOCAL_REPO_ROOT = CONFIG_PATH.parents[3] if len(CONFIG_PATH.parents) > 3 else CONFIG_PATH.parents[1]
ROOT_DIR = Path(os.environ.get("PROJECT_ROOT", LOCAL_REPO_ROOT))


class Settings(BaseSettings):
    database_url: str = "sqlite:///./policy_docs.db"
    storage_path: Path = ROOT_DIR / "storage"
    web_origin: str = "http://localhost:3000"
    max_upload_bytes: int = 25 * 1024 * 1024
    max_extracted_bytes: int = 100 * 1024 * 1024
    max_zip_files: int = 3000
    llm_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("LLM_API_KEY", "GEMINI_API_KEY")
    )
    llm_model: str = Field(
        default="gemini/gemini-3.1-flash-lite", validation_alias=AliasChoices("LLM_MODEL", "GEMINI_MODEL")
    )
    llm_api_base: str | None = None
    llm_timeout_seconds: float = Field(
        default=45.0, validation_alias=AliasChoices("LLM_TIMEOUT_SECONDS", "GEMINI_TIMEOUT_SECONDS")
    )
    llm_min_interval_seconds: float = Field(default=13.0, ge=0)

    @field_validator("llm_model")
    @classmethod
    def normalize_llm_model(cls, value: str) -> str:
        value = value.strip()
        if value.startswith("gemini-"):
            return f"gemini/{value}"
        return value

    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")


settings = Settings()
