from datetime import timedelta
from pathlib import Path
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import Select, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import JobModel, SessionModel, WorkerHeartbeatModel
from .schemas import PersonalityReport
from .security import hash_token, verify_token
from .settings import Settings
from .storage import delete_path, now_utc


def make_session_id() -> str:
    return f"MG-{uuid4().hex[:4].upper()}"


async def create_session(db: AsyncSession, settings: Settings) -> tuple[SessionModel, str]:
    upload_token = token_urlsafe(24)
    now = now_utc()

    for _ in range(10):
        session = SessionModel(
            id=make_session_id(),
            status="waiting",
            upload_token_hash=hash_token(upload_token),
            created_at=now,
            expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
        )
        db.add(session)
        try:
            await db.commit()
            await db.refresh(session)
            return session, upload_token
        except IntegrityError:
            await db.rollback()

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not allocate a unique session ID.",
    )


def build_upload_url(session_id: str, token: str, settings: Settings) -> str:
    return f"{settings.upload_url_base}/upload/{session_id}?token={token}"


def build_worker_image_url(job_id: str, settings: Settings) -> str:
    return f"{str(settings.backend_public_url).rstrip('/')}/api/worker/jobs/{job_id}/image"


async def get_session_or_404(db: AsyncSession, session_id: str) -> SessionModel:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return session


async def ensure_active_session(session: SessionModel) -> None:
    if session.status in {"deleted", "expired"}:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Session is {session.status}.",
        )
    if session.expires_at <= now_utc():
        session.status = "expired"
        await scrub_session_data(session)
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Session has expired.")


async def scrub_session_data(session: SessionModel) -> None:
    delete_path(session.image_path)
    session.display_name = None
    session.original_filename = None
    session.image_path = None
    session.report_json = None
    session.error_message = None


async def finish_session(db: AsyncSession, session: SessionModel, terminal_status: str = "deleted") -> None:
    await scrub_session_data(session)
    session.status = terminal_status
    session.finished_at = now_utc()
    session.deleted_at = now_utc()

    await db.execute(delete(JobModel).where(JobModel.session_id == session.id))
    await db.commit()


async def create_job_for_session(db: AsyncSession, session: SessionModel) -> JobModel:
    await db.execute(select(JobModel).where(JobModel.session_id == session.id))
    job = JobModel(
        id=uuid4().hex,
        session_id=session.id,
        status="queued",
        created_at=now_utc(),
    )
    db.add(job)
    session.status = "uploaded"
    await db.commit()
    await db.refresh(job)
    return job


async def claim_next_job(db: AsyncSession) -> JobModel | None:
    await recover_stuck_jobs(db)
    stmt: Select[tuple[JobModel]] = (
        select(JobModel)
        .where(JobModel.status == "queued")
        .order_by(JobModel.created_at.asc())
        .limit(1)
    )
    job = (await db.execute(stmt)).scalar_one_or_none()
    if job is None:
        return None

    session = await get_session_or_404(db, job.session_id)
    if session.status in {"deleted", "expired"} or session.expires_at <= now_utc():
        session.status = "expired"
        await scrub_session_data(session)
        job.status = "failed"
        job.error_message = "Session expired before worker claim."
        await db.commit()
        return None

    job.status = "processing"
    job.attempts += 1
    job.claimed_at = now_utc()
    session.status = "processing"
    await db.commit()
    await db.refresh(job)
    return job


async def complete_job(db: AsyncSession, job: JobModel, report: PersonalityReport) -> None:
    session = await get_session_or_404(db, job.session_id)
    await ensure_active_session(session)
    job.status = "done"
    job.completed_at = now_utc()
    session.status = "ready"
    session.report_json = report.model_dump(mode="json")
    session.processed_at = now_utc()
    session.error_message = None
    await db.commit()


async def fail_job(db: AsyncSession, job: JobModel, error_message: str) -> None:
    session = await get_session_or_404(db, job.session_id)
    job.status = "failed"
    job.error_message = error_message
    job.completed_at = now_utc()
    session.status = "error"
    session.error_message = error_message
    await db.commit()


async def get_job_or_404(db: AsyncSession, job_id: str) -> JobModel:
    job = await db.get(JobModel, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return job


def ensure_upload_token(session: SessionModel, token: str | None) -> None:
    if not token or not verify_token(token, session.upload_token_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid upload token.")


def ensure_image_exists(session: SessionModel) -> Path:
    if not session.image_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image is no longer available.")
    image_path = Path(session.image_path)
    if not image_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file is missing.")
    return image_path


async def count_by_status(db: AsyncSession, model: type[SessionModel] | type[JobModel]) -> dict[str, int]:
    rows = await db.execute(select(model.status, func.count()).group_by(model.status))
    return {status_name: count for status_name, count in rows.all()}


async def recover_stuck_jobs(db: AsyncSession, settings: Settings | None = None) -> int:
    from .settings import get_settings

    active_settings = settings or get_settings()
    cutoff = now_utc() - timedelta(seconds=active_settings.worker_job_timeout_seconds)
    rows = await db.execute(
        select(JobModel).where(
            JobModel.status == "processing",
            JobModel.claimed_at.is_not(None),
            JobModel.claimed_at <= cutoff,
        )
    )
    jobs = rows.scalars().all()
    recovered = 0

    for job in jobs:
        session = await db.get(SessionModel, job.session_id)
        if session is None or session.status in {"deleted", "expired", "ready"}:
            job.status = "failed"
            job.error_message = "Session closed while worker job was processing."
            job.completed_at = now_utc()
            recovered += 1
            continue

        if job.attempts < active_settings.worker_max_attempts:
            job.status = "queued"
            job.claimed_at = None
            job.error_message = "Requeued after worker timeout."
            session.status = "uploaded"
        else:
            job.status = "failed"
            job.error_message = "Inference worker timed out too many times."
            job.completed_at = now_utc()
            session.status = "error"
            session.error_message = job.error_message
        recovered += 1

    if recovered:
        await db.commit()

    return recovered


async def record_worker_heartbeat(
    db: AsyncSession,
    *,
    status: str,
    model_id: str | None,
    model_version: str | None,
    error_message: str | None,
) -> WorkerHeartbeatModel:
    heartbeat = await db.get(WorkerHeartbeatModel, "default")
    if heartbeat is None:
        heartbeat = WorkerHeartbeatModel(id="default", status=status, last_seen_at=now_utc())
        db.add(heartbeat)

    heartbeat.status = status
    heartbeat.model_id = model_id
    heartbeat.model_version = model_version
    heartbeat.error_message = error_message
    heartbeat.last_seen_at = now_utc()
    await db.commit()
    await db.refresh(heartbeat)
    return heartbeat


async def get_worker_health(db: AsyncSession, settings: Settings | None = None) -> dict[str, object]:
    from .settings import get_settings

    active_settings = settings or get_settings()
    heartbeat = await db.get(WorkerHeartbeatModel, "default")
    if heartbeat is None:
        return {
            "workerStatus": "offline",
            "modelId": None,
            "modelVersion": None,
            "lastSeenAt": None,
            "workerErrorMessage": None,
        }

    is_stale = heartbeat.last_seen_at <= now_utc() - timedelta(seconds=active_settings.worker_heartbeat_ttl_seconds)
    return {
        "workerStatus": "offline" if is_stale else heartbeat.status,
        "modelId": heartbeat.model_id,
        "modelVersion": heartbeat.model_version,
        "lastSeenAt": heartbeat.last_seen_at,
        "workerErrorMessage": heartbeat.error_message if heartbeat.status == "error" else None,
    }
