import argparse
import tempfile
import time
from pathlib import Path
from typing import Protocol

import httpx

from .analyzer import Analyzer, build_analyzer
from .settings import InferenceSettings


class WorkerBackend(Protocol):
    def heartbeat(
        self,
        status: str,
        *,
        model_id: str | None = None,
        model_version: str | None = None,
        error_message: str | None = None,
    ) -> None:
        ...

    def claim(self) -> dict | None:
        ...

    def download_image(self, job_id: str) -> bytes:
        ...

    def complete(self, job_id: str, report: dict) -> None:
        ...

    def fail(self, job_id: str, error_message: str) -> None:
        ...


class BackendClient:
    def __init__(self, backend_url: str, worker_token: str):
        self.client = httpx.Client(
            base_url=backend_url.rstrip("/"),
            headers={"Authorization": f"Bearer {worker_token}"},
            timeout=120,
        )

    def close(self) -> None:
        self.client.close()

    def heartbeat(
        self,
        status: str,
        *,
        model_id: str | None = None,
        model_version: str | None = None,
        error_message: str | None = None,
    ) -> None:
        response = self.client.post(
            "/api/worker/heartbeat",
            json={
                "status": status,
                "modelId": model_id,
                "modelVersion": model_version,
                "errorMessage": error_message,
            },
        )
        response.raise_for_status()

    def claim(self) -> dict | None:
        response = self.client.post("/api/worker/jobs/claim")
        response.raise_for_status()
        payload = response.json()
        if payload.get("job") is None and "id" not in payload:
            return None
        return payload

    def download_image(self, job_id: str) -> bytes:
        response = self.client.get(f"/api/worker/jobs/{job_id}/image")
        response.raise_for_status()
        return response.content

    def complete(self, job_id: str, report: dict) -> None:
        response = self.client.post(f"/api/worker/jobs/{job_id}/complete", json=report)
        response.raise_for_status()

    def fail(self, job_id: str, error_message: str) -> None:
        response = self.client.post(
            f"/api/worker/jobs/{job_id}/fail",
            json={"errorMessage": error_message[:500]},
        )
        response.raise_for_status()


def process_one_job(backend: WorkerBackend, analyzer: Analyzer) -> bool:
    claim = backend.claim()
    if claim is None:
        return False

    job_id = claim["id"]
    try:
        image_bytes = backend.download_image(job_id)
        suffix = Path(claim.get("imageUrl", "")).suffix or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix) as image_file:
            image_file.write(image_bytes)
            image_file.flush()
            report = analyzer.analyze(image_file.name)
        backend.complete(job_id, report.model_dump(mode="json"))
    except Exception as exc:
        backend.fail(job_id, f"Inference failed: {exc}")
    return True


def run_worker(settings: InferenceSettings, *, daemon: bool, analyzer: Analyzer | None = None) -> bool:
    backend = BackendClient(settings.backend_url, settings.worker_token)
    processed_any = False
    try:
        backend.heartbeat("warming", model_id=settings.model_id)
        active_analyzer = analyzer or build_analyzer(settings)
        backend.heartbeat(
            "ready",
            model_id=active_analyzer.model_name,
            model_version=active_analyzer.model_version,
        )

        while True:
            processed = process_one_job(backend, active_analyzer)
            processed_any = processed_any or processed
            if not daemon:
                return processed
            if not processed:
                backend.heartbeat(
                    "ready",
                    model_id=active_analyzer.model_name,
                    model_version=active_analyzer.model_version,
                )
                time.sleep(settings.poll_seconds)
    except Exception as exc:
        try:
            backend.heartbeat("error", model_id=settings.model_id, error_message=str(exc)[:500])
        finally:
            raise
    finally:
        backend.close()
    return processed_any


def run_once(backend_url: str, worker_token: str) -> bool:
    settings = InferenceSettings.from_env()
    settings = InferenceSettings(
        backend_url=backend_url,
        worker_token=worker_token,
        model_id=settings.model_id,
        hf_home=settings.hf_home,
        poll_seconds=settings.poll_seconds,
        max_new_tokens=settings.max_new_tokens,
        device_mode=settings.device_mode,
        analyzer=settings.analyzer,
        attn_implementation=settings.attn_implementation,
        google_cloud_quota_project=settings.google_cloud_quota_project,
        google_cloud_project=settings.google_cloud_project,
        google_cloud_location=settings.google_cloud_location,
        google_genai_use_enterprise=settings.google_genai_use_enterprise,
        gemini_model_id=settings.gemini_model_id,
    )
    return run_worker(settings, daemon=False)


def main() -> None:
    defaults = InferenceSettings.from_env()
    parser = argparse.ArgumentParser(description="Run the Machine Gaze inference worker.")
    parser.add_argument("--backend-url", default=defaults.backend_url)
    parser.add_argument("--worker-token", default=defaults.worker_token)
    parser.add_argument("--model-id", default=defaults.model_id)
    parser.add_argument("--hf-home", default=defaults.hf_home)
    parser.add_argument("--poll-seconds", type=float, default=defaults.poll_seconds)
    parser.add_argument("--max-new-tokens", type=int, default=defaults.max_new_tokens)
    parser.add_argument("--device-mode", default=defaults.device_mode)
    parser.add_argument(
        "--analyzer",
        choices=["auto", "qwen", "stub", "gemini", "google", "google-vision", "vision"],
        default=defaults.analyzer,
    )
    parser.add_argument("--gemini-model-id", default=defaults.gemini_model_id)
    parser.add_argument("--attn-implementation", default=defaults.attn_implementation)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    settings = InferenceSettings(
        backend_url=args.backend_url,
        worker_token=args.worker_token,
        model_id=args.model_id,
        hf_home=args.hf_home,
        poll_seconds=args.poll_seconds,
        max_new_tokens=args.max_new_tokens,
        device_mode=args.device_mode,
        analyzer=args.analyzer,
        attn_implementation=args.attn_implementation,
        google_cloud_quota_project=defaults.google_cloud_quota_project,
        google_cloud_project=defaults.google_cloud_project,
        google_cloud_location=defaults.google_cloud_location,
        google_genai_use_enterprise=defaults.google_genai_use_enterprise,
        gemini_model_id=args.gemini_model_id,
    )
    processed = run_worker(settings, daemon=args.daemon and not args.once)
    print("processed one job" if processed else "no queued jobs")


if __name__ == "__main__":
    main()
