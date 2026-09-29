import asyncio
from queue_service.event_queue import event_queue


async def event_worker(worker_id: int):
    try:
        while True:
            event = await event_queue.get()
            try:
                print(f"Worker {worker_id} processing new event {event.event_id}")
                print(event)
                # await process_event(event)
            finally:
                event_queue.task_done()

    except asyncio.CancelledError:
        print(f"Worker {worker_id} shutting down")
        raise