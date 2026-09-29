import os
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, Field

from models.detection_event import DetectionEvent, DetectionEventSeverity


openrouter_key = os.getenv("OPEN_ROUTER_API")
client = httpx.AsyncClient(timeout=15.0)


class TriageResult(BaseModel):
    severity: DetectionEventSeverity
    false_positive: bool
    false_positive_probability: float = Field(ge=0.0, le=1.0)


# Events that represent explicit operational/system state.
# Don't reject these simply because their confidence is low.
ALWAYS_ACCEPT = {
    "panic_button",
    "fire_alarm",
    "camera_offline",
}


STATIC_SEVERITY = {
    "panic_button": "critical",
    "fire_alarm": "critical",
    "camera_offline": "warning",
}


SEVERITY_CRITERIA = {
    "critical": {
        "what": (
            "Credible evidence of an immediate threat to life, safety, property, "
            "or active site security."
        ),
        "not_for": (
            "Routine motion, weak detections, or suspicious timing without "
            "supporting evidence."
        ),
        "examples": [
            "High-confidence forced entry in a sensitive zone",
            "Credible perimeter breach during overnight hours",
            "Explicit panic or fire signal",
        ],
    },
    "warning": {
        "what": (
            "Suspicious, uncertain, or operationally important activity requiring "
            "timely human review."
        ),
        "not_for": (
            "Clearly routine activity or an immediately confirmed emergency."
        ),
        "examples": [
            "Moderate-confidence motion overnight",
            "Loitering near a restricted zone",
            "Degraded monitoring equipment",
        ],
    },
    "info": {
        "what": (
            "Routine awareness with little evidence of an immediate threat."
        ),
        "not_for": (
            "Events with credible danger or meaningful suspicious context."
        ),
        "examples": [
            "Low-confidence motion during normal daytime activity",
            "Likely harmless object detection",
        ],
    },
}


QUESTIONS = {
    "severity": {
        "type": "choice",
        "instructions": {
            "question": (
                "What operational response level does this event require?"
            ),
            "inspect": [
                "`event.type`",
                "`event.confidence`",
                "`event.source`",
                "`event.zone`",
                "`event.metadata`",
                "`event.snapshot_url`",
                "`time_context.period`",
                "`time_context.day_of_week`",
            ],
            "focus": (
                "Judge the available evidence and operational consequences. "
                "Timing changes context but must not determine severity by itself."
            ),
        },
        "criteria": SEVERITY_CRITERIA,
    },
    "false_positive": {
        "type": "noul",
        "instructions": {
            "question": (
                "Is this detection more likely to be noise or benign activity "
                "than a genuine security incident?"
            ),
            "inspect": [
                "`event.type`",
                "`event.confidence`",
                "`event.zone`",
                "`event.metadata`",
                "`time_context.period`",
            ],
            "focus": (
                "Nighttime may increase concern for motion, loitering, object, "
                "or perimeter events, but does not prove malicious activity."
            ),
        },
        "criteria": {
            "true": {
                "what": (
                    "Evidence favors detector noise, harmless activity, or an "
                    "unreliable detection."
                ),
                "signals": [
                    "Low confidence",
                    "Routine daytime motion",
                    "Metadata identifies a harmless animal",
                    "Weak supporting context",
                ],
            },
            "false": {
                "what": (
                    "Evidence supports a genuine event or an explicit "
                    "operational signal."
                ),
                "signals": [
                    "High confidence",
                    "Overnight activity in a sensitive zone",
                    "Person or vehicle near a perimeter",
                    "Panic, fire, forced-entry, or equipment-state signal",
                ],
            },
        },
    },
}


FALSE_POSITIVE_THRESHOLD = 0.80


def build_triage_state(event: DetectionEvent) -> dict:
    local_timestamp = event.timestamp
    if event.timezone:
        local_timestamp = local_timestamp.astimezone(ZoneInfo(event.timezone))

    hour = local_timestamp.hour

    if hour < 6:
        period = "overnight"
    elif hour < 12:
        period = "morning"
    elif hour < 18:
        period = "afternoon"
    elif hour < 22:
        period = "evening"
    else:
        period = "night"

    return {
        "event": event.model_dump(mode="json"),
        "time_context": {
            "local_timestamp": local_timestamp.isoformat(),
            "timezone": event.timezone,
            "day_of_week": local_timestamp.strftime("%A"),
            "local_hour": hour,
            "period": period,
        },
    }


async def event_classifier(state: DetectionEvent) -> TriageResult:
    event_type = state.type.value

    # Don't spend an AI call on events we explicitly trust.
    if event_type in ALWAYS_ACCEPT:
        return TriageResult(
            severity=STATIC_SEVERITY[event_type],
            false_positive=False,
            false_positive_probability=0.0,
        )

    if not openrouter_key:
        return static_classifier(state)

    response = await client.post(
        "https://openrouter.ai/api/alpha/decisions",
        headers={
            "Authorization": f"Bearer {openrouter_key}",
        },
        json={
            "model": "~typesafe/jev-latest",
            "state": build_triage_state(state),
            "questions": QUESTIONS,
        },
    )

    response.raise_for_status()

    answers = response.json()["answers"]

    severity = answers["severity"]["choice"]

    # Noul returns the probability that the proposition is true.
    false_positive_probability = answers["false_positive"]["noul"]

    return TriageResult(
        severity=severity,
        false_positive=(
            false_positive_probability >= FALSE_POSITIVE_THRESHOLD
        ),
        false_positive_probability=false_positive_probability,
    )


def static_classifier(event: DetectionEvent) -> TriageResult:
    """
    Degraded fallback when Jev isn't available.

    This isn't intended to reproduce Jev's semantic judgment.
    """
    event_type = event.type.value

    if event_type in ALWAYS_ACCEPT:
        return TriageResult(
            severity=STATIC_SEVERITY[event_type],
            false_positive=False,
            false_positive_probability=0.0,
        )

    confidence = event.confidence

    if confidence < 0.50:
        false_positive_probability = 0.90
    elif confidence < 0.70:
        false_positive_probability = 0.60
    else:
        false_positive_probability = 0.10

    # Conservative fallback severity.
    if event_type in {
        "perimeter_breach",
        "door_forced",
        "glass_break",
        "fire_alarm",
    }:
        severity = "critical" if confidence >= 0.70 else "warning"

    elif event_type in {
        "smoke_detected",
        "loitering",
    }:
        severity = "warning"

    else:
        severity = "info"

    return TriageResult(
        severity=severity,
        false_positive=(
            false_positive_probability >= FALSE_POSITIVE_THRESHOLD
        ),
        false_positive_probability=false_positive_probability,
    )
