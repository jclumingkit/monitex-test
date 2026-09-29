from fastapi import FastAPI
from queue_service.event_queue import event_queue
from models.detection_event import DetectionEvent
from workers.event_worker import event_worker

from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI

WORKER_COUNT = 5

@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_tasks = [
        asyncio.create_task(event_worker(worker_id))
        for worker_id in range(WORKER_COUNT)
    ]

    yield

    print("Shutting down: draining event queue...")

    try:
        await asyncio.wait_for(
            event_queue.join(),
            timeout=10,
        )
    except asyncio.TimeoutError:
        print(
            f"Queue did not drain before timeout. "
            f"Remaining queued events: {event_queue.qsize()}"
        )

    print("Stopping workers...")

    for task in worker_tasks:
        task.cancel()

    await asyncio.gather(
        *worker_tasks,
        return_exceptions=True,
    )

    print("Shutdown complete")


app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Hello Monitex Security"}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "queue_size": event_queue.qsize(),
        "queue_capacity": event_queue.maxsize,
    }

@app.post("/api/webhook")
async def api_webhook(event: DetectionEvent):
    # queue event here
    await event_queue.put(event)

    return {
        "status": "ok",
        "message": "Message received"
    }