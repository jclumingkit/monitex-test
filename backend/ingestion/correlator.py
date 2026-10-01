from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from models.detection_event import (
    DetectionEventSeverity,
    DetectionEventType,
    SITE_NOT_DEFINED,
)


CORRELATION_WINDOW_SECONDS = 120
REPEATED_EVENT_WINDOW_SECONDS = 60
REPEATED_EVENT_THRESHOLD = 3

CRITICAL_COMBINATIONS = (
    frozenset(("person_detected", "perimeter_breach")),
    frozenset(("person_detected", "door_forced")),
    frozenset(("person_detected", "glass_break")),
    frozenset(("person_detected", "panic_button")),
    frozenset(("smoke_detected", "fire_alarm")),
)

SEVERITY_ORDER = (
    DetectionEventSeverity.INFO,
    DetectionEventSeverity.WARNING,
    DetectionEventSeverity.CRITICAL,
)


@dataclass(frozen=True)
class CorrelationDecision:
    severity: DetectionEventSeverity
    reason: str


def increase_severity(
    severity: DetectionEventSeverity,
) -> DetectionEventSeverity:
    index = SEVERITY_ORDER.index(severity)
    return SEVERITY_ORDER[min(index + 1, len(SEVERITY_ORDER) - 1)]


def correlate_event(
    current: Mapping,
    recent_events: list[Mapping],
) -> CorrelationDecision | None:
    if (
        current["site_id"] == SITE_NOT_DEFINED
        or current["type"] == DetectionEventType.TYPE_NOT_DEFINED.value
    ):
        return None

    current_type = current["type"]
    base_severity = DetectionEventSeverity(current["severity"])
    current_created = datetime.fromisoformat(current["date_created"])

    for related in recent_events:
        pair = frozenset((current_type, related["type"]))
        if pair in CRITICAL_COMBINATIONS:
            if base_severity == DetectionEventSeverity.CRITICAL:
                return None
            return CorrelationDecision(
                severity=DetectionEventSeverity.CRITICAL,
                reason=(
                    f"Combined {current_type} and {related['type']} signals "
                    "at the same site within 2 minutes"
                ),
            )

    repeated_count = 1
    for related in recent_events:
        related_created = datetime.fromisoformat(related["date_created"])
        age_seconds = (current_created - related_created).total_seconds()
        if (
            related["type"] == current_type
            and age_seconds <= REPEATED_EVENT_WINDOW_SECONDS
        ):
            repeated_count += 1

    if repeated_count < REPEATED_EVENT_THRESHOLD:
        return None

    escalated_severity = increase_severity(base_severity)
    if escalated_severity == base_severity:
        return None

    return CorrelationDecision(
        severity=escalated_severity,
        reason=(
            f"{repeated_count} {current_type} events at the same site "
            "within 1 minute"
        ),
    )
