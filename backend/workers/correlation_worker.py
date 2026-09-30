import asyncio

from ingestion.correlator import CORRELATION_WINDOW_SECONDS, correlate_event
from models.processed_event import ProcessedEventResponse
from queue_service.correlation_queue import correlation_queue
from realtime.sse_manager import sse_manager


async def correlation_worker(repository):
    try:
        while True:
            processed_event_id = await correlation_queue.get()

            try:
                current = await repository.get_processed_event_by_id(
                    processed_event_id
                )
                if current is None:
                    continue

                recent_events = await repository.get_recent_processed_events(
                    processed_event_id,
                    CORRELATION_WINDOW_SECONDS,
                )
                decision = correlate_event(current, recent_events)
                final_severity = (
                    decision.severity.value
                    if decision is not None
                    else current["severity"]
                )
                updated = await repository.complete_event_correlation(
                    processed_event_id,
                    current["severity"],
                    final_severity,
                    decision.reason if decision is not None else None,
                )
                if not updated:
                    continue

                updated_event = await repository.get_processed_event_by_id(
                    processed_event_id
                )
                if updated_event is not None:
                    normalized_event = ProcessedEventResponse.model_validate(
                        dict(updated_event)
                    )
                    await sse_manager.publish(
                        normalized_event.model_dump(mode="json")
                    )
            except Exception as error:
                print(
                    "Correlation worker failed processed event "
                    f"{processed_event_id}: {error}"
                )
            finally:
                correlation_queue.task_done()
    except asyncio.CancelledError:
        print("Correlation worker shutting down")
        raise
