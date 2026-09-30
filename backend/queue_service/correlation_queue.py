import asyncio


CORRELATION_QUEUE_SIZE = 1000

correlation_queue: asyncio.Queue[str] = asyncio.Queue(
    maxsize=CORRELATION_QUEUE_SIZE
)
