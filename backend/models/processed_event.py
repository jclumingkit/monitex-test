from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from models.detection_event import (
    DetectionEventSeverity,
    DetectionEventSource,
    DetectionEventType,
)


class ProcessedEventResponse(BaseModel):
    id: str
    event_id: str
    site_id: str
    zone: str
    type: DetectionEventType
    source: DetectionEventSource
    confidence: float
    timestamp: datetime
    snapshot_url: str | None = None
    severity: DetectionEventSeverity
    summary: str
    status: Literal["pending_operator_review", "acknowledged", "resolved"]
    date_created: datetime
    date_updated: datetime


class UpdateEventStatusRequest(BaseModel):
    status: Literal["acknowledged", "resolved"]


class UpdateEventStatusResponse(BaseModel):
    id: str
    status: Literal["acknowledged", "resolved"]


class BulkUpdateEventStatusRequest(BaseModel):
    event_ids: list[str] = Field(min_length=1)
    status: Literal["acknowledged", "resolved"]


class BulkUpdateEventStatusResponse(BaseModel):
    ids: list[str]
    status: Literal["acknowledged", "resolved"]
