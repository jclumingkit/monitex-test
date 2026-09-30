from collections.abc import AsyncIterable

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from realtime.sse_manager import sse_manager


router = APIRouter()


@router.get(
    "/api/events/stream",
    response_class=EventSourceResponse,
)
async def stream_events() -> AsyncIterable[ServerSentEvent]:
    queue = await sse_manager.subscribe()

    try:
        while True:
            event = await queue.get()

            if event is None:
                break

            yield ServerSentEvent(
                data=event,
                event="alarm",
                id=event["event_id"],
            )

    finally:
        sse_manager.unsubscribe(queue)