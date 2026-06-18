from io import BytesIO
from pathlib import Path

from PIL import Image

from inference.contracts import BigFiveReport
from inference.settings import InferenceSettings
from inference.worker import DownloadedImage, process_one_job, run_worker


def image_bytes() -> bytes:
    image = Image.new("RGB", (64, 64), color=(82, 180, 155))
    output = BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


def report_payload() -> dict:
    return {
        "traits": [
            {
                "key": "openness",
                "name": "Openness",
                "scorePercent": 70,
                "lowLabel": "Practical",
                "highLabel": "Curious",
                "summary": "Curious energy.",
            },
            {
                "key": "conscientiousness",
                "name": "Conscientiousness",
                "scorePercent": 60,
                "lowLabel": "Spontaneous",
                "highLabel": "Organized",
                "summary": "Organized surface.",
            },
            {
                "key": "extraversion",
                "name": "Extraversion",
                "scorePercent": 55,
                "lowLabel": "Introverted",
                "highLabel": "Extraverted",
                "summary": "Moderate social charge.",
            },
            {
                "key": "agreeableness",
                "name": "Agreeableness",
                "scorePercent": 66,
                "lowLabel": "Skeptical",
                "highLabel": "Cooperative",
                "summary": "Warm read.",
            },
            {
                "key": "neuroticism",
                "name": "Neuroticism",
                "scorePercent": 30,
                "lowLabel": "Calm",
                "highLabel": "Reactive",
                "summary": "Calm read.",
            },
        ],
        "machineGuess": {
            "probablyStudies": "Design, media, or something with too many deadlines.",
            "campusRole": "The person who quietly becomes project lead.",
            "futureForecast": "Will accidentally become responsible for the group chat.",
            "classicStruggle": "Says yes because it looks quick.",
        },
        "model": {"name": "fake-model", "version": "test"},
    }


class FakeBackend:
    def __init__(self, claim: dict | None = None):
        self.claim_payload = claim
        self.completed: list[tuple[str, dict]] = []
        self.failed: list[tuple[str, str]] = []
        self.heartbeats: list[tuple[str, str | None, str | None]] = []
        self.closed = False

    def heartbeat(self, status: str, *, model_id=None, model_version=None, error_message=None) -> None:
        self.heartbeats.append((status, model_id, model_version))

    def claim(self):
        return self.claim_payload

    def download_image(self, job_id: str) -> DownloadedImage:
        return DownloadedImage(data=image_bytes(), content_type="image/jpeg")

    def complete(self, job_id: str, report: dict) -> None:
        self.completed.append((job_id, report))

    def fail(self, job_id: str, error_message: str) -> None:
        self.failed.append((job_id, error_message))

    def close(self) -> None:
        self.closed = True


class FakeAnalyzer:
    model_name = "fake-model"
    model_version = "test"

    def analyze(self, image_path: str | Path) -> BigFiveReport:
        assert Path(image_path).exists()
        return BigFiveReport.model_validate(report_payload())


class FailingAnalyzer(FakeAnalyzer):
    def analyze(self, image_path: str | Path) -> BigFiveReport:
        raise RuntimeError("nope")


def test_process_one_job_completes_report():
    backend = FakeBackend(claim={"id": "job-1"})

    processed = process_one_job(backend, FakeAnalyzer())

    assert processed is True
    assert backend.failed == []
    assert backend.completed[0][0] == "job-1"
    assert backend.completed[0][1]["traits"][0]["key"] == "openness"
    assert backend.completed[0][1]["machineGuess"]["futureForecast"] == "Will accidentally become responsible for the group chat."


def test_process_one_job_fails_job_when_analyzer_errors():
    backend = FakeBackend(claim={"id": "job-1"})

    processed = process_one_job(backend, FailingAnalyzer())

    assert processed is True
    assert backend.completed == []
    assert backend.failed[0][0] == "job-1"
    assert "Inference failed" in backend.failed[0][1]


def test_run_worker_once_sends_heartbeats_and_closes_backend():
    backend = FakeBackend(claim=None)

    processed = run_worker(
        InferenceSettings(gemini_model_id="gemini-2.5-flash"),
        daemon=False,
        analyzer=FakeAnalyzer(),
        backend=backend,
    )

    assert processed is False
    assert backend.heartbeats == [
        ("warming", "gemini-2.5-flash", None),
        ("ready", "fake-model", "test"),
    ]
    assert backend.closed is True
