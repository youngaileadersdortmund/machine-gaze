from io import BytesIO
from pathlib import Path
import sys
from types import SimpleNamespace

from PIL import Image

import pytest

from inference import PrivacyReport, StubAnalyzer, analyze_image
from inference.analyzer import (
    GeminiAnalyzer,
    GoogleVisionAnalyzer,
    build_analyzer,
    parse_creative_report_text,
    parse_report_text,
)
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
    assert all(group.confidence == "low" for group in parsed.speculative)


def test_stub_does_not_inject_safety_overreach_examples(tmp_path: Path):
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (64, 64), color=(197, 34, 123)).save(image_path)

    report = analyze_image(image_path)
    speculative_text = " ".join(item for group in report.speculative for item in group.items).lower()

    assert "unsafe overreach" not in speculative_text
    assert report.safetyNotes == []


def test_parser_preserves_model_claims_without_safety_filtering():
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

    assert "political" in observed
    assert "campus badge" in observed
    assert report.speculative == []
    assert report.safetyNotes == []
    assert report.riskScore == 20


def test_parser_normalizes_overlong_model_output():
    report = parse_report_text(
        """
        {
          "riskScore": 120,
          "observed": [
            {
              "title": "This title is deliberately valid",
              "confidence": "certain",
              "items": ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
            }
          ],
          "speculative": [
            {
              "title": "Guesses",
              "confidence": "high",
              "items": ["guess one", "guess two"]
            }
          ],
          "targeting": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"],
          "safetyNotes": [],
          "model": {}
        }
        """
    )

    assert report.riskScore == 100
    assert report.observed[0].confidence == "medium"
    assert len(report.observed[0].items) == 8
    assert report.speculative[0].confidence == "low"
    assert len(report.targeting) == 12
    assert report.model.name == "unknown"


def test_creative_parser_does_not_add_safety_boilerplate():
    report = parse_creative_report_text(
        """
        {
          "riskScore": 67,
          "observed": [
            {
              "title": "First impression",
              "confidence": "high",
              "items": ["projects polish, restraint, and practiced camera awareness"]
            }
          ],
          "speculative": [],
          "targeting": ["executive coaching"],
          "safetyNotes": [],
          "model": {"name": "fake", "version": "test"}
        }
        """
    )

    assert report.safetyNotes == []
    assert report.speculative == []
    assert report.riskScore == 0
    assert report.observed[0].title == "First impression"


def test_google_vision_analyzer_formats_safe_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (64, 64), color=(82, 180, 155)).save(image_path)

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "responses": [
                    {
                        "labelAnnotations": [
                            {"description": "Suit", "score": 0.91},
                            {"description": "Building", "score": 0.82},
                        ],
                        "localizedObjectAnnotations": [
                            {"name": "Person", "score": 0.94},
                            {"name": "Glasses", "score": 0.77},
                        ],
                        "textAnnotations": [
                            {"description": "ACME HQ\nVisitor"},
                            {"description": "ACME", "score": 0.88},
                        ],
                        "faceAnnotations": [
                            {
                                "joyLikelihood": "POSSIBLE",
                                "sorrowLikelihood": "VERY_UNLIKELY",
                                "angerLikelihood": "VERY_UNLIKELY",
                                "surpriseLikelihood": "UNLIKELY",
                            }
                        ],
                        "logoAnnotations": [{"description": "Acme", "score": 0.76}],
                        "safeSearchAnnotation": {
                            "adult": "VERY_UNLIKELY",
                            "violence": "VERY_UNLIKELY",
                            "racy": "UNLIKELY",
                            "medical": "UNLIKELY",
                            "spoof": "UNLIKELY",
                        },
                    }
                ]
            }

    class FakeCredentials:
        valid = False
        token = None
        quota_project_id = "quota-project"

        def refresh(self, _request) -> None:
            self.valid = True
            self.token = "adc-token"

    fake_credentials = FakeCredentials()

    def fake_default(*, scopes):
        assert scopes == GoogleVisionAnalyzer.scopes
        return fake_credentials, "adc-project"

    def fake_post(*_args, **kwargs):
        assert kwargs["headers"]["Authorization"] == "Bearer adc-token"
        assert kwargs["headers"]["x-goog-user-project"] == "quota-project"
        return FakeResponse()

    monkeypatch.setattr("inference.analyzer.google.auth.default", fake_default)
    monkeypatch.setattr("inference.analyzer.Request", lambda: object())
    monkeypatch.setattr("inference.analyzer.httpx.post", fake_post)

    report = GoogleVisionAnalyzer(InferenceSettings(analyzer="google-vision")).analyze(image_path)

    observed_text = " ".join(item for group in report.observed for item in group.items).lower()
    group_titles = [group.title for group in report.observed]

    assert "visible face-like region" in observed_text
    assert "biometric-style matching" in observed_text
    assert "glasses" in observed_text
    assert "suit" in observed_text
    assert "building" in observed_text
    assert "unknown (94% confidence)" not in observed_text
    assert "adult likelihood" not in observed_text
    assert "readable text detected" in observed_text
    assert "Clothing and accessories" in group_titles
    assert "Scene and background" in group_titles
    assert "formalwear" in report.targeting
    assert "business attire" in report.targeting
    assert report.safetyNotes == []
    assert report.model.name == "google-cloud-vision"
    assert report.riskScore > 35


def test_build_analyzer_uses_google_vision_when_requested(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "inference.analyzer.google.auth.default",
        lambda **_kwargs: (SimpleNamespace(valid=True, token="token"), "project"),
    )
    monkeypatch.setattr("inference.analyzer.Request", lambda: object())

    analyzer = build_analyzer(InferenceSettings(analyzer="google-vision"))

    assert isinstance(analyzer, GoogleVisionAnalyzer)


def test_gemini_analyzer_formats_rich_safe_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (64, 64), color=(23, 27, 50)).save(image_path)
    calls: list[dict] = []

    class FakeResponse:
        text = """
        {
          "riskScore": 76,
          "observed": [
            {
              "title": "First impression",
              "confidence": "high",
              "items": [
                "projects polish, restraint, and a controlled public-facing persona",
                "the slight smile reads as approachable but carefully managed"
              ]
            },
            {
              "title": "Style and status signals",
              "confidence": "high",
              "items": [
                "formal styling performs competence more than relaxation",
                "glasses and tailoring create an intellectual-professional silhouette"
              ]
            }
          ],
          "speculative": [
            {
              "title": "Likely operating mode",
              "confidence": "low",
              "items": ["probably prefers situations where presentation, timing, and credibility matter"]
            }
          ],
          "targeting": ["executive coaching", "premium eyewear", "networking events", "reputation management"],
          "safetyNotes": [],
          "model": {"name": "ignored", "version": "ignored"}
        }
        """

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs):
            calls.append({"client": kwargs})
            self.models = FakeModels()

    monkeypatch.setattr("google.genai.Client", FakeClient)

    report = GeminiAnalyzer(
        InferenceSettings(
            analyzer="gemini",
            google_cloud_project="project-1",
            google_cloud_location="global",
            gemini_model_id="gemini-2.5-flash",
        )
    ).analyze(image_path)

    observed_text = " ".join(item for group in report.observed for item in group.items).lower()

    assert calls[0]["client"]["enterprise"] is True
    assert calls[0]["client"]["vertexai"] is True
    assert calls[0]["client"]["project"] == "project-1"
    assert calls[1]["model"] == "gemini-2.5-flash"
    assert calls[1]["config"].response_schema is PrivacyReport
    assert "controlled public-facing persona" in observed_text
    assert "premium eyewear" in report.targeting
    assert report.safetyNotes == []
    assert report.riskScore == 0
    assert report.model.name == "gemini-2.5-flash"
    assert report.model.version == "vertex-ai:global"


def test_gemini_analyzer_does_not_inject_unsafe_overreach_or_safety_notes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (64, 64), color=(23, 27, 50)).save(image_path)

    class FakeResponse:
        text = """
        {
          "riskScore": 44,
          "observed": [
            {
              "title": "First impression",
              "confidence": "high",
              "items": ["reads as controlled, deliberate, and image-aware"]
            }
          ],
          "speculative": [],
          "targeting": ["eyewear"],
          "safetyNotes": [],
          "model": {"name": "ignored", "version": "ignored"}
        }
        """

    class FakeModels:
        def generate_content(self, **_kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, **_kwargs):
            self.models = FakeModels()

    monkeypatch.setattr("google.genai.Client", FakeClient)

    report = GeminiAnalyzer(
        InferenceSettings(analyzer="gemini", google_cloud_project="project-1")
    ).analyze(image_path)

    speculative_text = " ".join(item for group in report.speculative for item in group.items).lower()

    assert "unsafe overreach" not in speculative_text
    assert report.safetyNotes == []


def test_build_analyzer_uses_gemini_when_requested(monkeypatch: pytest.MonkeyPatch):
    class FakeClient:
        def __init__(self, **_kwargs):
            self.models = SimpleNamespace()

    monkeypatch.setattr("google.genai.Client", FakeClient)

    analyzer = build_analyzer(
        InferenceSettings(analyzer="gemini", google_cloud_project="project-1")
    )

    assert isinstance(analyzer, GeminiAnalyzer)


def test_worker_cli_accepts_gemini(monkeypatch: pytest.MonkeyPatch):
    import inference.worker as worker_module

    captured: list[InferenceSettings] = []

    def fake_run_worker(settings: InferenceSettings, *, daemon: bool):
        captured.append(settings)
        assert daemon is False
        return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "inference-worker",
            "--once",
            "--analyzer",
            "gemini",
            "--gemini-model-id",
            "gemini-test",
        ],
    )
    monkeypatch.setattr(worker_module, "run_worker", fake_run_worker)

    worker_module.main()

    assert captured[0].analyzer == "gemini"
    assert captured[0].gemini_model_id == "gemini-test"


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
