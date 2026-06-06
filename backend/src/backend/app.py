import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .cleanup import cleanup_loop, expire_old_sessions
from .database import SessionLocal, engine, get_db, init_db
from .models import JobModel, SessionModel
from .schemas import (
    AdminSessionsResponse,
    HealthResponse,
    MessageResponse,
    PrivacyReport,
    SessionAdminRow,
    SessionCreateResponse,
    SessionPublicResponse,
    WorkerClaimResponse,
    WorkerEmptyClaimResponse,
    WorkerFailRequest,
    WorkerHeartbeatRequest,
)
from .security import require_admin, require_worker
from .service import (
    build_upload_url,
    build_worker_image_url,
    claim_next_job,
    complete_job,
    count_by_status,
    create_job_for_session,
    create_session,
    ensure_active_session,
    ensure_image_exists,
    ensure_upload_token,
    fail_job,
    finish_session,
    get_job_or_404,
    get_session_or_404,
    get_worker_health,
    record_worker_heartbeat,
    recover_stuck_jobs,
)
from .settings import get_settings
from .storage import now_utc, read_limited_upload, sanitize_and_store_image


def session_response(session: SessionModel) -> SessionPublicResponse:
    report = PrivacyReport.model_validate(session.report_json) if session.report_json else None
    return SessionPublicResponse(
        id=session.id,
        status=session.status,
        displayName=session.display_name,
        expiresAt=session.expires_at,
        uploadedAt=session.uploaded_at,
        processedAt=session.processed_at,
        errorMessage=session.error_message,
        report=report if session.status == "ready" else None,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    await init_db(engine)
    cleanup_task = asyncio.create_task(cleanup_loop(SessionLocal, settings))
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


app = FastAPI(title="Machine Gaze Backend", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    await recover_stuck_jobs(db)
    worker_health = await get_worker_health(db)
    return HealthResponse(
        status="ok",
        sessions=await count_by_status(db, SessionModel),
        jobs=await count_by_status(db, JobModel),
        **worker_health,
    )


@app.post(
    "/api/sessions",
    response_model=SessionCreateResponse,
    dependencies=[Depends(require_admin)],
    status_code=status.HTTP_201_CREATED,
)
async def create_session_route(db: AsyncSession = Depends(get_db)) -> SessionCreateResponse:
    settings = get_settings()
    session, upload_token = await create_session(db, settings)
    return SessionCreateResponse(
        id=session.id,
        status=session.status,
        uploadUrl=build_upload_url(session.id, upload_token, settings),
        expiresAt=session.expires_at,
    )


@app.get("/api/sessions/{session_id}", response_model=SessionPublicResponse)
async def get_session_route(session_id: str, db: AsyncSession = Depends(get_db)) -> SessionPublicResponse:
    session = await get_session_or_404(db, session_id)
    if session.status not in {"deleted", "expired"} and session.expires_at <= now_utc():
        await finish_session(db, session, terminal_status="expired")
        await db.refresh(session)
    return session_response(session)


@app.post("/api/sessions/{session_id}/upload", response_model=SessionPublicResponse)
async def upload_photo_route(
    session_id: str,
    token: str | None = Query(default=None),
    display_name: str = Form(min_length=1, max_length=80),
    consent: bool = Form(),
    file: UploadFile = File(),
    db: AsyncSession = Depends(get_db),
) -> SessionPublicResponse:
    if not consent:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consent is required.")

    session = await get_session_or_404(db, session_id)
    await ensure_active_session(session)
    ensure_upload_token(session, token)
    if session.status != "waiting":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This session already has an uploaded photo.",
        )

    settings = get_settings()
    data = await read_limited_upload(file, settings.max_upload_bytes)
    image_path = sanitize_and_store_image(data, session.id, settings)

    session.display_name = display_name.strip()
    session.original_filename = file.filename
    session.image_path = str(image_path)
    session.uploaded_at = now_utc()
    await create_job_for_session(db, session)
    await db.refresh(session)
    return session_response(session)


@app.post(
    "/api/sessions/{session_id}/finish",
    response_model=MessageResponse,
    dependencies=[Depends(require_admin)],
)
async def finish_session_route(session_id: str, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    session = await get_session_or_404(db, session_id)
    await finish_session(db, session)
    return MessageResponse(status="deleted")


@app.get(
    "/api/admin/sessions",
    response_model=AdminSessionsResponse,
    dependencies=[Depends(require_admin)],
)
async def admin_sessions_route(db: AsyncSession = Depends(get_db)) -> AdminSessionsResponse:
    await expire_old_sessions(db)
    await recover_stuck_jobs(db)
    rows = await db.execute(select(SessionModel).order_by(SessionModel.created_at.desc()).limit(50))
    sessions = [
        SessionAdminRow(
            id=session.id,
            status=session.status,
            displayName=session.display_name,
            createdAt=session.created_at,
            expiresAt=session.expires_at,
            uploadedAt=session.uploaded_at,
            processedAt=session.processed_at,
            errorMessage=session.error_message,
        )
        for session in rows.scalars().all()
    ]
    return AdminSessionsResponse(sessions=sessions)


@app.post(
    "/api/worker/jobs/claim",
    response_model=WorkerClaimResponse | WorkerEmptyClaimResponse,
    dependencies=[Depends(require_worker)],
)
async def worker_claim_route(
    db: AsyncSession = Depends(get_db),
) -> WorkerClaimResponse | WorkerEmptyClaimResponse:
    job = await claim_next_job(db)
    if job is None:
        return WorkerEmptyClaimResponse()
    settings = get_settings()
    return WorkerClaimResponse(
        id=job.id,
        sessionId=job.session_id,
        status=job.status,
        imageUrl=build_worker_image_url(job.id, settings),
    )


@app.post(
    "/api/worker/heartbeat",
    response_model=MessageResponse,
    dependencies=[Depends(require_worker)],
)
async def worker_heartbeat_route(
    payload: WorkerHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await record_worker_heartbeat(
        db,
        status=payload.status,
        model_id=payload.modelId,
        model_version=payload.modelVersion,
        error_message=payload.errorMessage,
    )
    return MessageResponse(status="ok")


@app.get("/api/worker/jobs/{job_id}/image", dependencies=[Depends(require_worker)])
async def worker_image_route(job_id: str, db: AsyncSession = Depends(get_db)) -> FileResponse:
    job = await get_job_or_404(db, job_id)
    session = await get_session_or_404(db, job.session_id)
    await ensure_active_session(session)
    image_path = ensure_image_exists(session)
    return FileResponse(path=image_path)


@app.post(
    "/api/worker/jobs/{job_id}/complete",
    response_model=MessageResponse,
    dependencies=[Depends(require_worker)],
)
async def worker_complete_route(
    job_id: str,
    report: PrivacyReport,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    job = await get_job_or_404(db, job_id)
    if job.status != "processing":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is not processing.")
    await complete_job(db, job, report)
    return MessageResponse(status="ready")


@app.post(
    "/api/worker/jobs/{job_id}/fail",
    response_model=MessageResponse,
    dependencies=[Depends(require_worker)],
)
async def worker_fail_route(
    job_id: str,
    payload: WorkerFailRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    job = await get_job_or_404(db, job_id)
    await fail_job(db, job, payload.errorMessage)
    return MessageResponse(status="error")
