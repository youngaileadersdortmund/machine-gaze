from io import BytesIO
from pathlib import Path

from PIL import Image

import pytest

from inference import PrivacyReport, StubAnalyzer, analyze_image
from inference.analyzer import parse_report_text
from inference.worker import process_one_job, run_worker
from inference.settings import InferenceSettings


def test_stub_analyzer_returns_valid_privacy_report(tmp_path: Path):
    image_path = tmp_path / "sample.jpg"
    image = Image.new("RGB", (128, 128), color=(237, 169, 19))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    image_path.write_bytes(buffer.getvalue())

    report = analyze_image(image_path)
    parsed = PrivacyReport.model_validate(report.model_dump())

    assert parsed.riskScore >= 0
    assert parsed.observed
    assert parsed.safetyNotes
    assert all(group.confidence == "low" for group in parsed.speculative)


def test_stub_keeps_sensitive_traits_as_overreach_examples(tmp_path: Path):
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (64, 64), color=(197, 34, 123)).save(image_path)

    report = analyze_image(image_path)
    observed_text = " ".join(item for group in report.observed for item in group.items).lower()
    safety_text = " ".join(report.safetyNotes).lower()
    speculative_text = " ".join(item for group in report.speculative for item in group.items).lower()

    assert "religion" not in observed_text
    assert "politics" not in observed_text
    assert "unsafe overreach" in safety_text or "overreach" in speculative_text


def test_parser_removes_sensitive_observed_claims():
    report = parse_report_text(
        """
        {
          "riskScore": 20,
          "observed": [
            {"title": "Bad facts", "confidence": "high", "items": ["person appears political", "visible campus badge"]}
          ],
          "speculative": [],
          "targeting": ["student events"],
          "safetyNotes": [],
          "model": {"name": "fake", "version": "test"}
        }
        """
    )

    observed = " ".join(item for group in report.observed for item in group.items).lower()
    speculative = " ".join(item for group in report.speculative for item in group.items).lower()

    assert "political" not in observed
    assert "campus badge" in observed
    assert "politics" in speculative
    assert report.riskScore >= 20


class FakeBackend:
    def __init__(self, claim_payload: dict | None = None):
        self.claim_payload = claim_payload
        self.completed: list[tuple[str, dict]] = []
        self.failed: list[tuple[str, str]] = []
        self.heartbeats: list[tuple[str, str | None, str | None, str | None]] = []
        self.closed = False

    def heartbeat(
        self,
        status: str,
        *,
        model_id: str | None = None,
        model_version: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self.heartbeats.append((status, model_id, model_version, error_message))

    def claim(self) -> dict | None:
        return self.claim_payload

    def download_image(self, job_id: str) -> bytes:
        assert job_id == "job-1"
        image = Image.new("RGB", (64, 64), color=(82, 180, 155))
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        return buffer.getvalue()

    def complete(self, job_id: str, report: dict) -> None:
        self.completed.append((job_id, report))

    def fail(self, job_id: str, error_message: str) -> None:
        self.failed.append((job_id, error_message))

    def close(self) -> None:
        self.closed = True


def test_worker_processes_one_claimed_job():
    backend = FakeBackend({"id": "job-1", "imageUrl": "http://backend/image.jpg"})

    processed = process_one_job(backend, StubAnalyzer())

    assert processed is True
    assert backend.completed[0][0] == "job-1"
    assert backend.completed[0][1]["model"]["name"] == "machine-gaze-stub"
    assert backend.failed == []


def test_worker_marks_job_failed_when_analyzer_raises():
    class BrokenAnalyzer(StubAnalyzer):
        model_name = "broken"
        model_version = "test"

        def analyze(self, image_path: str | Path) -> PrivacyReport:
            raise RuntimeError("boom")

    backend = FakeBackend({"id": "job-1", "imageUrl": "http://backend/image.jpg"})

    processed = process_one_job(backend, BrokenAnalyzer())

    assert processed is True
    assert backend.completed == []
    assert backend.failed[0][0] == "job-1"
    assert "boom" in backend.failed[0][1]


def test_run_worker_once_sends_warming_and_ready_heartbeats(monkeypatch: pytest.MonkeyPatch):
    import inference.worker as worker_module

    backend = FakeBackend(None)
    monkeypatch.setattr(worker_module, "BackendClient", lambda *_args, **_kwargs: backend)
    monkeypatch.setattr(worker_module, "build_analyzer", lambda _settings: StubAnalyzer())

    processed = run_worker(InferenceSettings(analyzer="stub"), daemon=False)

    assert processed is False
    assert backend.heartbeats[0][0] == "warming"
    assert backend.heartbeats[1][0] == "ready"
    assert backend.closed is True
