from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]


class InsightGroup(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    confidence: Confidence
    items: list[str] = Field(min_length=1, max_length=8)


class ModelMetadata(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=80)


class PrivacyReport(BaseModel):
    observed: list[InsightGroup] = Field(min_length=1, max_length=8)
    speculative: list[InsightGroup] = Field(default_factory=list, max_length=8)
    targeting: list[str] = Field(default_factory=list, max_length=12)
    safetyNotes: list[str] = Field(default_factory=list, max_length=8)
    model: ModelMetadata
