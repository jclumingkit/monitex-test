from ingestion.summarizer import summarize_event
from models.detection_event import DetectionEvent, DetectionEventSeverity
from ingestion.classifier import event_classifier

class ClassifiedEvent(DetectionEvent):
    severity: DetectionEventSeverity
    false_positive_probability: float
    summary: str

async def process_event(event: DetectionEvent):
    triage = await event_classifier(event)

    if triage.false_positive:
        return None

    summary = await summarize_event(event)

    return ClassifiedEvent(
        **event.model_dump(),
        **triage.model_dump(),
        summary=summary,
    )
