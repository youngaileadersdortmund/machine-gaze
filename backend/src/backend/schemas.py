from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SessionStatus = Literal["waiting", "uploaded", "processing", "ready", "deleted", "expired", "error"]
JobStatus = Literal["queued", "processing", "done", "failed"]
WorkerStatus = Literal["offline", "warming", "ready", "error"]
TraitKey = Literal["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]

REQUIRED_TRAIT_KEYS: tuple[TraitKey, ...] = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)


class TraitReport(BaseModel):
    key: TraitKey
    name: str = Field(min_length=1, max_length=40)
    scorePercent: int = Field(ge=0, le=100)
    lowLabel: str = Field(min_length=1, max_length=40)
    highLabel: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=220)


class ModelMetadata(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=80)


class MachineGuess(BaseModel):
    probablyStudies: str = Field(min_length=1, max_length=160)
    campusRole: str = Field(min_length=1, max_length=160)
    futureForecast: str = Field(min_length=1, max_length=180)
    classicStruggle: str = Field(min_length=1, max_length=180)


class PersonalityReport(BaseModel):
    traits: list[TraitReport]
    machineGuess: MachineGuess
    model: ModelMetadata

    @model_validator(mode="after")
    def validate_trait_set(self) -> "PersonalityReport":
        keys = [trait.key for trait in self.traits]
        if len(keys) != len(REQUIRED_TRAIT_KEYS):
            raise ValueError("Report must include exactly five Big Five traits.")
        if len(set(keys)) != len(keys):
            raise ValueError("Report contains duplicate Big Five traits.")
        missing = set(REQUIRED_TRAIT_KEYS) - set(keys)
        extra = set(keys) - set(REQUIRED_TRAIT_KEYS)
        if missing or extra:
            raise ValueError("Report must include exactly the Big Five trait keys.")

        trait_by_key = {trait.key: trait for trait in self.traits}
        self.traits = [trait_by_key[key] for key in REQUIRED_TRAIT_KEYS]
        return self


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
    report: PersonalityReport | None = None


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
