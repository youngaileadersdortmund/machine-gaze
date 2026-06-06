from dataclasses import dataclass
import os


@dataclass(frozen=True)
class InferenceSettings:
    backend_url: str = "http://localhost:8000"
    worker_token: str = "dev-worker-token"
    model_id: str = "Qwen/Qwen3-VL-30B-A3B-Thinking"
    hf_home: str = "../hf_cache"
    poll_seconds: float = 1.5
    max_new_tokens: int = 900
    device_mode: str = "auto"
    analyzer: str = "auto"
    attn_implementation: str = "sdpa"

    @classmethod
    def from_env(cls) -> "InferenceSettings":
        return cls(
            backend_url=os.getenv("INFERENCE_BACKEND_URL", "http://localhost:8000"),
            worker_token=os.getenv("INFERENCE_WORKER_TOKEN", os.getenv("WORKER_TOKEN", "dev-worker-token")),
            model_id=os.getenv("INFERENCE_MODEL_ID", "Qwen/Qwen3-VL-30B-A3B-Thinking"),
            hf_home=os.getenv("HF_HOME", "../hf_cache"),
            poll_seconds=float(os.getenv("INFERENCE_POLL_SECONDS", "1.5")),
            max_new_tokens=int(os.getenv("INFERENCE_MAX_NEW_TOKENS", "900")),
            device_mode=os.getenv("INFERENCE_DEVICE_MODE", "auto"),
            analyzer=os.getenv("INFERENCE_ANALYZER", "auto"),
            attn_implementation=os.getenv("INFERENCE_ATTN_IMPLEMENTATION", "sdpa"),
        )

    def apply_environment(self) -> None:
        if self.hf_home:
            os.environ.setdefault("HF_HOME", self.hf_home)
