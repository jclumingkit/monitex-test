import asyncio
from datetime import datetime, timezone

from queue_service.event_queue import event_queue
from ingestion.process_event import process_event
from models.processed_event import ProcessedEventResponse
from realtime.sse_manager import sse_manager


async def event_worker(worker_id: int, repository):
    try:
        while True:
            event = await event_queue.get()
            try:
                print(f"Received event {event.event_id}")

                await repository.save_event(event)
                print(f"Event {event.event_id} saved to database")

                print(f"Started worker {worker_id} processing event {event.event_id}")

                result = await process_event(event)
                if result:
                    processed_event_id = await repository.save_processed_event(result)

                    now = datetime.now(timezone.utc)
                    normalized_result = ProcessedEventResponse(
                        id=processed_event_id,
                        event_id=result.event_id,
                        site_id=result.site_id,
                        zone=result.zone,
                        type=result.type,
                        source=result.source,
                        confidence=result.confidence,
                        timestamp=result.timestamp,
                        snapshot_url=result.snapshot_url,
                        severity=result.severity,
                        summary=result.summary,
                        status="pending_operator_review",
                        date_created=now,
                        date_updated=now,
                    )

                    # send to SSE for frontend real time update
                    await sse_manager.publish(
                        normalized_result.model_dump(mode="json")
                    )

                print(
                    f"Worker {worker_id} completed event {event.event_id}"
                )

            except Exception as error:
                print(
                    f"Worker {worker_id} failed event "
                    f"{event.event_id}: {error}"
                )
            finally:
                event_queue.task_done()

    except asyncio.CancelledError:
        print(f"Worker {worker_id} shutting down")
        raise
