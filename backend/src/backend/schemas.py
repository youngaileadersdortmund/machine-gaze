from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Confidence = Literal["high", "medium", "low"]
SessionStatus = Literal["waiting", "uploaded", "processing", "ready", "deleted", "expired", "error"]
JobStatus = Literal["queued", "processing", "done", "failed"]
WorkerStatus = Literal["offline", "warming", "ready", "error"]


class InsightGroup(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    confidence: Confidence
    items: list[str] = Field(min_length=1, max_length=8)


class ModelMetadata(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=80)


class PrivacyReport(BaseModel):
    riskScore: int = Field(ge=0, le=100)
    observed: list[InsightGroup] = Field(min_length=1, max_length=8)
    speculative: list[InsightGroup] = Field(default_factory=list, max_length=8)
    targeting: list[str] = Field(default_factory=list, max_length=12)
    safetyNotes: list[str] = Field(default_factory=list, max_length=8)
    model: ModelMetadata


class SessionCreateResponse(BaseModel):
    id: str
    status: SessionStatus
    uploadUrl: str
    expiresAt: datetime


class SessionPublicResponse(BaseModel):
    id: str
    status: SessionStatus
    displayName: str | None = None
    expiresAt: datetime
    uploadedAt: datetime | None = None
    processedAt: datetime | None = None
    errorMessage: str | None = None
    report: PrivacyReport | None = None


class SessionAdminRow(BaseModel):
    id: str
    status: SessionStatus
    displayName: str | None = None
    createdAt: datetime
    expiresAt: datetime
    uploadedAt: datetime | None = None
    processedAt: datetime | None = None
    errorMessage: str | None = None


class AdminSessionsResponse(BaseModel):
    sessions: list[SessionAdminRow]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    sessions: dict[str, int]
    jobs: dict[str, int]
    workerStatus: WorkerStatus
    modelId: str | None = None
    modelVersion: str | None = None
    lastSeenAt: datetime | None = None
    workerErrorMessage: str | None = None


class WorkerClaimResponse(BaseModel):
    id: str
    sessionId: str
    status: JobStatus
    imageUrl: str


class WorkerEmptyClaimResponse(BaseModel):
    job: None = None


class WorkerFailRequest(BaseModel):
    errorMessage: str = Field(min_length=1, max_length=500)


class WorkerHeartbeatRequest(BaseModel):
    status: Literal["warming", "ready", "error"]
    modelId: str | None = Field(default=None, max_length=255)
    modelVersion: str | None = Field(default=None, max_length=120)
    errorMessage: str | None = Field(default=None, max_length=500)


class MessageResponse(BaseModel):
    status: str


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
