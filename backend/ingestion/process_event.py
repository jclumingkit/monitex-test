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
        # still persist in a "dump" table for logs and audit
        print(
            f"Event {event.event_id} rejected as likely false positive "
            f"({triage.false_positive_probability:.0%})"
        )
        return

    summary = await summarize_event(event)

    classified_event = ClassifiedEvent(
        **event.model_dump(),
        **triage.model_dump(),
        summary=summary,
    )

    print(classified_event.model_dump_json())
