from enum import Enum

from pydantic import BaseModel, Field


class DetectionEventType(str, Enum):
    MOTION_DETECTED = "motion_detected"
    PERIMETER_BREACH = "perimeter_breach"
    DOOR_FORCED = "door_forced"
    GLASS_BREAK = "glass_break"
    SMOKE_DETECTED = "smoke_detected"
    FIRE_ALARM = "fire_alarm"
    OBJECT_DETECTED = "object_detected"
    LOITERING = "loitering"
    CAMERA_OFFLINE = "camera_offline"
    SENSOR_FAULT = "sensor_fault"
    PANIC_BUTTON = "panic_button"


class DetectionEvent(BaseModel):
    event_id: str
    site_id: str
    type: DetectionEventType
    confidence: float = Field(gt=0.0, lt=1.0)