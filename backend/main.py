from fastapi import FastAPI
from realtime.sse_manager import sse_manager
from queue_service.event_queue import event_queue
from models.detection_event import DetectionEvent
from workers.event_worker import event_worker
from workers.loop_video_worker.detection import loop_video_worker
from database.sqlite import connect_db, initialize_db, EventRepository
from api.processed_events import router as processed_events_router
from api.stream_events import router as stream_events
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
import asyncio

WORKER_COUNT = 5
VIDEO_WORKER_SHUTDOWN_TIMEOUT = 10

@asynccontextmanager
async def lifespan(app: FastAPI):
    # -----------------------
    # STARTUP
    # -----------------------

    # Connect to database
    db = await connect_db()
    repository = EventRepository(db)
    await initialize_db(db)

    app.state.db = db
    app.state.repository = repository

    # Wake up workers
    worker_tasks = [
        asyncio.create_task(event_worker(worker_id, repository))
        for worker_id in range(WORKER_COUNT)
    ]

    video_stop_event = asyncio.Event()
    video_worker_task = asyncio.create_task(
        loop_video_worker(video_stop_event)
    )
    app.state.video_stop_event = video_stop_event
    app.state.video_worker_task = video_worker_task

    try:
        yield
    finally:
        # -----------------------
        # SHUTDOWN
        # -----------------------

        print("Stopping loop video worker...")
        video_stop_event.set()
        try:
            await asyncio.wait_for(
                video_worker_task,
                timeout=VIDEO_WORKER_SHUTDOWN_TIMEOUT,
            )
        except asyncio.TimeoutError:
            print("Loop video worker did not stop before timeout")
            video_worker_task.cancel()
            await asyncio.gather(video_worker_task, return_exceptions=True)
        except Exception as error:
            print(f"Loop video worker failed: {error}")

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

        await sse_manager.shutdown()

        print("Stopping workers...")

        for task in worker_tasks:
            task.cancel()

        await asyncio.gather(
            *worker_tasks,
            return_exceptions=True,
        )

        print("Stopping database...")
        await db.close()

        print("Shutdown complete")


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# GET processed events
app.include_router(processed_events_router)

# SSE realtime
app.include_router(stream_events)

