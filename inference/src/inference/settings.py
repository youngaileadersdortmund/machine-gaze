from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env_files() -> None:
    package_path = Path(__file__).resolve()
    inference_dir = package_path.parents[2]
    repo_root = package_path.parents[3]
    load_dotenv(repo_root / ".env", override=False)
    load_dotenv(inference_dir / ".env", override=False)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class InferenceSettings:
    backend_url: str = "http://localhost:8000"
    worker_token: str = "dev-worker-token"
    poll_seconds: float = 1.5
    gemini_model_id: str = "gemini-2.5-pro"
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    max_output_tokens: int = 4096
    temperature: float = 0.65

    @classmethod
    def from_env(cls) -> "InferenceSettings":
        _load_env_files()
        return cls(
            backend_url=os.getenv("INFERENCE_BACKEND_URL", "http://localhost:8000"),
            worker_token=os.getenv("INFERENCE_WORKER_TOKEN", os.getenv("WORKER_TOKEN", "dev-worker-token")),
            poll_seconds=float(os.getenv("INFERENCE_POLL_SECONDS", "1.5")),
            gemini_model_id=os.getenv("GEMINI_MODEL_ID", "gemini-2.5-pro"),
            google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
            google_cloud_location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            max_output_tokens=int(os.getenv("INFERENCE_MAX_OUTPUT_TOKENS", "4096")),
            temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.65")),
        )

    @property
    def daemon_default(self) -> bool:
        return _bool_env("INFERENCE_DAEMON", default=False)
