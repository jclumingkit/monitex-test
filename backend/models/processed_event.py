from datetime import datetime

from pydantic import BaseModel

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
    status: str
    date_created: datetime
    date_updated: datetime
