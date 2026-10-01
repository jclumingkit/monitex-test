from enum import Enum
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator


SITE_NOT_DEFINED = "site-not-defined"


def generate_event_id() -> str:
    return f"evt_{uuid4().hex[:10]}"


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def is_missing_string(value: Any) -> bool:
    return value is None or isinstance(value, str) and not value.strip()


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
    TYPE_NOT_DEFINED = "type_not_defined"


class DetectionEventSource(str, Enum):
    CAMERA = "camera"
    SENSOR = "sensor"
    SOURCE_NOT_DEFINED = "SOURCE_NOT_DEFINED"


class DetectionEvent(BaseModel):
    event_id: str = Field(default_factory=generate_event_id)
    site_id: str = SITE_NOT_DEFINED
    zone: str = "zone-not-defined"
    type: DetectionEventType = DetectionEventType.TYPE_NOT_DEFINED
    source: DetectionEventSource = DetectionEventSource.SOURCE_NOT_DEFINED
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=current_utc_time)
    timezone: str | None = None
    snapshot_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def apply_missing_field_fallbacks(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        event = value.copy()
        if is_missing_string(event.get("event_id")):
            event["event_id"] = generate_event_id()
        if is_missing_string(event.get("site_id")):
            event["site_id"] = SITE_NOT_DEFINED
        if is_missing_string(event.get("zone")):
            event["zone"] = "zone-not-defined"
        if is_missing_string(event.get("type")):
            event["type"] = DetectionEventType.TYPE_NOT_DEFINED.value
        if is_missing_string(event.get("source")):
            event["source"] = DetectionEventSource.SOURCE_NOT_DEFINED.value
        if event.get("confidence") is None:
            event["confidence"] = 0.0
        if is_missing_string(event.get("timestamp")):
            event["timestamp"] = current_utc_time().isoformat()
        if is_missing_string(event.get("timezone")):
            event["timezone"] = None
        if is_missing_string(event.get("snapshot_url")):
            event["snapshot_url"] = None
        if event.get("metadata") is None:
            event["metadata"] = {}
        return event

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
