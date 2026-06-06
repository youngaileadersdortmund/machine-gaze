from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    backend_public_url: AnyHttpUrl = "http://localhost:8000"
    frontend_public_url: AnyHttpUrl = "http://localhost:3000"
    admin_token: str = "dev-admin-token"
    worker_token: str = "dev-worker-token"
    session_ttl_seconds: int = Field(default=900, ge=60)
    max_upload_mb: int = Field(default=8, ge=1, le=64)
    database_url: str = "sqlite+aiosqlite:///../data/machine_gaze.db"
    upload_dir: Path = Path("../data/uploads")
    cors_origins: list[str] = ["http://localhost:3000"]
    cleanup_interval_seconds: int = Field(default=60, ge=5)
    worker_job_timeout_seconds: int = Field(default=300, ge=30)
    worker_max_attempts: int = Field(default=2, ge=1, le=10)
    worker_heartbeat_ttl_seconds: int = Field(default=20, ge=5)

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def upload_url_base(self) -> str:
        return str(self.frontend_public_url).rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
