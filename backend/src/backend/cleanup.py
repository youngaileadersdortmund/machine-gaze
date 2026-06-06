import asyncio
from contextlib import suppress

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SessionModel
from .service import finish_session, recover_stuck_jobs
from .settings import Settings
from .storage import now_utc


async def expire_old_sessions(db: AsyncSession) -> int:
    rows = await db.execute(
        select(SessionModel).where(
            SessionModel.expires_at <= now_utc(),
            SessionModel.status.not_in(["deleted", "expired"]),
        )
    )
    sessions = rows.scalars().all()
    for session in sessions:
        await finish_session(db, session, terminal_status="expired")
    return len(sessions)


async def cleanup_loop(session_factory, settings: Settings) -> None:
    while True:
        await asyncio.sleep(settings.cleanup_interval_seconds)
        with suppress(Exception):
            async with session_factory() as db:
                await expire_old_sessions(db)
                await recover_stuck_jobs(db, settings)
