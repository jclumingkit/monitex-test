from enum import Enum
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class DetectionEventType(str, Enum):
    MOTION_DETECTED = "motion_detected"
    PERIMETER_BREACH = "perimeter_breach"
    DOOR_FORCED = "door_forced"
    GLASS_BREAK = "glass_break"
    SMOKE_DETECTED = "smoke_detected"
    FIRE_ALARM = "fire_alarm"
    OBJECT_DETECTED = "object_detected"
    PERSON_DETECTED = "person_detected"
    LOITERING = "loitering"
    CAMERA_OFFLINE = "camera_offline"
    SENSOR_FAULT = "sensor_fault"
    PANIC_BUTTON = "panic_button"


class DetectionEventSource(str, Enum):
    CAMERA = "camera"
    SENSOR = "sensor"


class DetectionEvent(BaseModel):
    event_id: str
    site_id: str
    zone: str
    type: DetectionEventType
    source: DetectionEventSource
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime
    timezone: str | None = None
    snapshot_url: str | None
    metadata: dict[str, Any]

    @field_validator("timestamp")
    @classmethod
    def require_timestamp_offset(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("timestamp must include a UTC offset")
        return value

    @field_validator("timezone")
    @classmethod
    def require_valid_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return value

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA timezone") from error
        return value


class DetectionEventSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info" 
