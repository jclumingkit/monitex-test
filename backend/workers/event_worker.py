import asyncio
from queue_service.event_queue import event_queue
from ingestion.process_event import process_event


async def event_worker(worker_id: int):
    try:
        while True:
            event = await event_queue.get()
            try:
                print(f"Started worker {worker_id} processing event {event.event_id}")
                await process_event(event)
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
