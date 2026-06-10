import asyncio
import importlib
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.database import init_db
from backend.models import JobModel, SessionModel
from backend.settings import Settings
from backend.storage import now_utc

ADMIN_HEADERS = {"Authorization": "Bearer test-admin"}
WORKER_HEADERS = {"Authorization": "Bearer test-worker"}
backend_app_module = importlib.import_module("backend.app")
backend_security_module = importlib.import_module("backend.security")
app = backend_app_module.app
get_db = backend_app_module.get_db


def make_image_bytes(format_name: str = "JPEG") -> bytes:
    image = Image.new("RGB", (128, 96), color=(82, 180, 155))
    output = BytesIO()
    image.save(output, format=format_name)
    return output.getvalue()


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    settings = Settings(
        backend_public_url="http://backend.test",
        frontend_public_url="http://frontend.test",
        admin_token="test-admin",
        worker_token="test-worker",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        upload_dir=tmp_path / "uploads",
        cors_origins=["http://frontend.test"],
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    asyncio.run(init_db(engine))

    async def override_db():
        async with session_factory() as session:
            yield session

    monkeypatch.setattr(backend_app_module, "get_settings", lambda: settings)
    monkeypatch.setattr(backend_security_module, "get_settings", lambda: settings)
    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as test_client:
        test_client.test_session_factory = session_factory
        test_client.test_settings = settings
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def create_session(client: TestClient) -> dict:
    response = client.post("/api/sessions", headers=ADMIN_HEADERS)
    assert response.status_code == 201
    return response.json()


def upload_photo(client: TestClient, session_payload: dict) -> dict:
    token = parse_qs(urlparse(session_payload["uploadUrl"]).query)["token"][0]
    response = client.post(
        f"/api/sessions/{session_payload['id']}/upload",
        params={"token": token},
        data={"display_name": "Mariam", "consent": "true"},
        files={"file": ("photo.jpg", make_image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_create_session_requires_admin_and_returns_upload_url(client: TestClient):
    rejected = client.post("/api/sessions")
    assert rejected.status_code == 401

    payload = create_session(client)

    assert payload["id"].startswith("MG-")
    assert payload["status"] == "waiting"
    assert payload["uploadUrl"].startswith("http://frontend.test/upload/")
    assert "token=" in payload["uploadUrl"]


def test_upload_validation_rejects_missing_consent_bad_token_and_non_image(client: TestClient):
    session_payload = create_session(client)

    missing_consent = client.post(
        f"/api/sessions/{session_payload['id']}/upload",
        params={"token": "bad"},
        data={"display_name": "Mariam", "consent": "false"},
        files={"file": ("photo.jpg", make_image_bytes(), "image/jpeg")},
    )
    assert missing_consent.status_code == 400

    bad_token = client.post(
        f"/api/sessions/{session_payload['id']}/upload",
        params={"token": "bad"},
        data={"display_name": "Mariam", "consent": "true"},
        files={"file": ("photo.jpg", make_image_bytes(), "image/jpeg")},
    )
    assert bad_token.status_code == 401

    token = parse_qs(urlparse(session_payload["uploadUrl"]).query)["token"][0]
    non_image = client.post(
        f"/api/sessions/{session_payload['id']}/upload",
        params={"token": token},
        data={"display_name": "Mariam", "consent": "true"},
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert non_image.status_code == 400


def test_valid_upload_sanitizes_image_and_worker_can_complete(client: TestClient):
    session_payload = create_session(client)
    uploaded = upload_photo(client, session_payload)

    assert uploaded["status"] == "uploaded"
    assert uploaded["displayName"] == "Mariam"

    async def inspect_upload():
        async with client.test_session_factory() as db:
            session = await db.get(SessionModel, session_payload["id"])
            job = (await db.execute(select(JobModel).where(JobModel.session_id == session.id))).scalar_one()
            return session.image_path, job.status

    image_path, job_status = asyncio.run(inspect_upload())
    assert job_status == "queued"
    assert image_path
    assert Path(image_path).exists()
    assert not list(client.test_settings.upload_dir.glob("*.raw"))

    claim = client.post("/api/worker/jobs/claim", headers=WORKER_HEADERS)
    assert claim.status_code == 200
    claim_payload = claim.json()
    assert claim_payload["status"] == "processing"

    image_response = client.get(
        f"/api/worker/jobs/{claim_payload['id']}/image",
        headers=WORKER_HEADERS,
    )
    assert image_response.status_code == 200

    report = {
        "riskScore": 72,
        "observed": [{"title": "Visible scene", "confidence": "high", "items": ["one person in frame"]}],
        "speculative": [{"title": "Weak guesses", "confidence": "low", "items": ["student or visitor"]}],
        "targeting": ["AI literacy"],
        "safetyNotes": ["Protected traits are unsafe overreach examples, not predictions."],
        "model": {"name": "test-model", "version": "0.1"},
    }
    complete = client.post(
        f"/api/worker/jobs/{claim_payload['id']}/complete",
        headers=WORKER_HEADERS,
        json=report,
    )
    assert complete.status_code == 200

    ready = client.get(f"/api/sessions/{session_payload['id']}")
    assert ready.status_code == 200
    ready_payload = ready.json()
    assert ready_payload["status"] == "ready"
    assert ready_payload["report"]["riskScore"] == 72


def test_session_preview_requires_admin_and_streams_sanitized_image(client: TestClient):
    session_payload = create_session(client)

    waiting_preview = client.get(f"/api/sessions/{session_payload['id']}/preview", headers=ADMIN_HEADERS)
    assert waiting_preview.status_code == 404

    upload_photo(client, session_payload)

    rejected = client.get(f"/api/sessions/{session_payload['id']}/preview")
    assert rejected.status_code == 401

    preview = client.get(f"/api/sessions/{session_payload['id']}/preview", headers=ADMIN_HEADERS)
    assert preview.status_code == 200
    assert preview.headers["cache-control"] == "no-store"

    with Image.open(BytesIO(preview.content)) as image:
        assert image.size == (128, 96)
        assert image.mode == "RGB"


def test_finish_deletes_files_report_and_jobs(client: TestClient):
    session_payload = create_session(client)
    upload_photo(client, session_payload)

    claim = client.post("/api/worker/jobs/claim", headers=WORKER_HEADERS).json()
    report = {
        "riskScore": 10,
        "observed": [{"title": "Visible scene", "confidence": "high", "items": ["campus"]}],
        "speculative": [],
        "targeting": [],
        "safetyNotes": ["No protected traits are predicted."],
        "model": {"name": "test-model", "version": "0.1"},
    }
    client.post(f"/api/worker/jobs/{claim['id']}/complete", headers=WORKER_HEADERS, json=report)

    async def get_before():
        async with client.test_session_factory() as db:
            session = await db.get(SessionModel, session_payload["id"])
            return session.image_path

    image_path = asyncio.run(get_before())
    assert Path(image_path).exists()

    finish = client.post(f"/api/sessions/{session_payload['id']}/finish", headers=ADMIN_HEADERS)
    assert finish.status_code == 200
    assert not Path(image_path).exists()

    async def inspect_after():
        async with client.test_session_factory() as db:
            session = await db.get(SessionModel, session_payload["id"])
            jobs = (await db.execute(select(JobModel))).scalars().all()
            return session, jobs

    session, jobs = asyncio.run(inspect_after())
    assert session.status == "deleted"
    assert session.display_name is None
    assert session.report_json is None
    assert jobs == []


def test_expiry_cleanup_removes_abandoned_uploads(client: TestClient):
    session_payload = create_session(client)
    upload_photo(client, session_payload)

    async def expire_row():
        async with client.test_session_factory() as db:
            session = await db.get(SessionModel, session_payload["id"])
            image_path = session.image_path
            session.expires_at = now_utc()
            await db.commit()
            return image_path

    image_path = asyncio.run(expire_row())
    response = client.get(f"/api/sessions/{session_payload['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "expired"
    assert not Path(image_path).exists()


def test_worker_auth_is_required(client: TestClient):
    response = client.post("/api/worker/jobs/claim")
    assert response.status_code == 401


def test_worker_heartbeat_updates_health(client: TestClient):
    initial = client.get("/health")
    assert initial.status_code == 200
    assert initial.json()["workerStatus"] == "offline"

    heartbeat = client.post(
        "/api/worker/heartbeat",
        headers=WORKER_HEADERS,
        json={
            "status": "ready",
            "modelId": "Qwen/Qwen3-VL-30B-A3B-Thinking",
            "modelVersion": "test",
        },
    )
    assert heartbeat.status_code == 200

    health = client.get("/health").json()
    assert health["workerStatus"] == "ready"
    assert health["modelId"] == "Qwen/Qwen3-VL-30B-A3B-Thinking"
    assert health["lastSeenAt"]


def test_stuck_processing_job_is_requeued_then_failed(client: TestClient):
    session_payload = create_session(client)
    upload_photo(client, session_payload)
    claim = client.post("/api/worker/jobs/claim", headers=WORKER_HEADERS).json()

    async def make_stale(attempts: int):
        async with client.test_session_factory() as db:
            job = await db.get(JobModel, claim["id"])
            job.attempts = attempts
            job.claimed_at = now_utc().replace(year=2000)
            await db.commit()

    asyncio.run(make_stale(attempts=1))
    health = client.get("/health").json()
    assert health["jobs"]["queued"] == 1

    async def inspect_requeued():
        async with client.test_session_factory() as db:
            session = await db.get(SessionModel, session_payload["id"])
            job = await db.get(JobModel, claim["id"])
            return session.status, job.status, job.claimed_at

    session_status, job_status, claimed_at = asyncio.run(inspect_requeued())
    assert session_status == "uploaded"
    assert job_status == "queued"
    assert claimed_at is None

    client.post("/api/worker/jobs/claim", headers=WORKER_HEADERS)
    asyncio.run(make_stale(attempts=2))
    health = client.get("/health").json()
    assert health["jobs"]["failed"] == 1

    async def inspect_failed():
        async with client.test_session_factory() as db:
            session = await db.get(SessionModel, session_payload["id"])
            job = await db.get(JobModel, claim["id"])
            return session.status, session.error_message, job.status

    session_status, error_message, job_status = asyncio.run(inspect_failed())
    assert session_status == "error"
    assert "timed out" in error_message
    assert job_status == "failed"
