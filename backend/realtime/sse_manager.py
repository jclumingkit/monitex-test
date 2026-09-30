import asyncio
from typing import Any


class SSEManager:
    def __init__(self):
        self.subscribers: set[asyncio.Queue] = set()
        self.closed = False
        
    async def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)

        self.subscribers.add(queue)

        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self.subscribers.discard(queue)

    async def publish(self, event: Any):
        for queue in self.subscribers:
            await queue.put(event)

    async def shutdown(self):
        self.closed = True

        for queue in list(self.subscribers):
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass


sse_manager = SSEManager()