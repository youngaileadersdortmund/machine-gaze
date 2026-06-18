from __future__ import annotations

import argparse
from dataclasses import dataclass
import tempfile
import time
from pathlib import Path
from typing import Protocol

import httpx

from .analyzer import Analyzer, build_analyzer
from .settings import InferenceSettings


@dataclass(frozen=True)
class DownloadedImage:
    data: bytes
    content_type: str


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

    def download_image(self, job_id: str) -> DownloadedImage:
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

    def download_image(self, job_id: str) -> DownloadedImage:
        response = self.client.get(f"/api/worker/jobs/{job_id}/image")
        response.raise_for_status()
        return DownloadedImage(
            data=response.content,
            content_type=response.headers.get("content-type", "image/jpeg").split(";", 1)[0],
        )

    def complete(self, job_id: str, report: dict) -> None:
        response = self.client.post(f"/api/worker/jobs/{job_id}/complete", json=report)
        response.raise_for_status()

    def fail(self, job_id: str, error_message: str) -> None:
        response = self.client.post(
            f"/api/worker/jobs/{job_id}/fail",
            json={"errorMessage": error_message[:500]},
        )
        response.raise_for_status()


def _suffix_for_content_type(content_type: str) -> str:
    if content_type == "image/png":
        return ".png"
    if content_type == "image/webp":
        return ".webp"
    return ".jpg"


def process_one_job(backend: WorkerBackend, analyzer: Analyzer) -> bool:
    claim = backend.claim()
    if claim is None:
        return False

    job_id = claim["id"]
    try:
        image = backend.download_image(job_id)
        with tempfile.NamedTemporaryFile(suffix=_suffix_for_content_type(image.content_type)) as image_file:
            image_file.write(image.data)
            image_file.flush()
            report = analyzer.analyze(Path(image_file.name))
        backend.complete(job_id, report.model_dump(mode="json"))
    except Exception as exc:
        backend.fail(job_id, f"Inference failed: {exc}")
    return True


def run_worker(
    settings: InferenceSettings,
    *,
    daemon: bool,
    analyzer: Analyzer | None = None,
    backend: WorkerBackend | None = None,
) -> bool:
    active_backend = backend or BackendClient(settings.backend_url, settings.worker_token)
    should_close = hasattr(active_backend, "close")
    processed_any = False
    try:
        active_backend.heartbeat("warming", model_id=settings.gemini_model_id)
        active_analyzer = analyzer or build_analyzer(settings)
        active_backend.heartbeat(
            "ready",
            model_id=active_analyzer.model_name,
            model_version=active_analyzer.model_version,
        )

        while True:
            processed = process_one_job(active_backend, active_analyzer)
            processed_any = processed_any or processed
            if not daemon:
                return processed
            if not processed:
                active_backend.heartbeat(
                    "ready",
                    model_id=active_analyzer.model_name,
                    model_version=active_analyzer.model_version,
                )
                time.sleep(settings.poll_seconds)
    except Exception as exc:
        active_backend.heartbeat("error", model_id=settings.gemini_model_id, error_message=str(exc)[:500])
        raise
    finally:
        if should_close:
            close = getattr(active_backend, "close", None)
            if callable(close):
                close()
    return processed_any


def main() -> None:
    defaults = InferenceSettings.from_env()
    parser = argparse.ArgumentParser(description="Run the Machine Gaze Gemini inference worker.")
    parser.add_argument("--backend-url", default=defaults.backend_url)
    parser.add_argument("--worker-token", default=defaults.worker_token)
    parser.add_argument("--poll-seconds", type=float, default=defaults.poll_seconds)
    parser.add_argument("--gemini-model-id", default=defaults.gemini_model_id)
    parser.add_argument("--google-cloud-project", default=defaults.google_cloud_project)
    parser.add_argument("--google-cloud-location", default=defaults.google_cloud_location)
    parser.add_argument("--max-output-tokens", type=int, default=defaults.max_output_tokens)
    parser.add_argument("--temperature", type=float, default=defaults.temperature)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    settings = InferenceSettings(
        backend_url=args.backend_url,
        worker_token=args.worker_token,
        poll_seconds=args.poll_seconds,
        gemini_model_id=args.gemini_model_id,
        google_cloud_project=args.google_cloud_project,
        google_cloud_location=args.google_cloud_location,
        max_output_tokens=args.max_output_tokens,
        temperature=args.temperature,
    )
    processed = run_worker(settings, daemon=args.daemon and not args.once)
    print("processed one job" if processed else "no queued jobs")


if __name__ == "__main__":
    main()
