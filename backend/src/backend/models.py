from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    upload_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(80))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    image_path: Mapped[str | None] = mapped_column(Text)
    report_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(), index=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime())

    jobs: Mapped[list["JobModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(), index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime())

    session: Mapped[SessionModel] = relationship(back_populates="jobs")


class WorkerHeartbeatModel(Base):
    __tablename__ = "worker_heartbeats"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    model_id: Mapped[str | None] = mapped_column(String(255))
    model_version: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(), index=True)
