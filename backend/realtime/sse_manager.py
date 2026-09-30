import asyncio
from typing import Any


class SSEManager:
    def __init__(self):
        self.subscribers: set[asyncio.Queue] = set()

    async def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)

        self.subscribers.add(queue)

        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self.subscribers.discard(queue)

    async def publish(self, event: Any):
        for queue in self.subscribers:
            await queue.put(event)


sse_manager = SSEManager()