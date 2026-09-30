import asyncio
from collections import deque
from typing import Any


class SSEManager:
    def __init__(self, history_size: int = 100):
        self.subscribers: set[asyncio.Queue] = set()
        self.history: deque[Any] = deque(maxlen=history_size)
        self.closed = False
        
    async def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)

        for event in self.history:
            queue.put_nowait(event)
        self.subscribers.add(queue)

        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self.subscribers.discard(queue)

    async def publish(self, event: Any):
        self.history.append(event)
        for queue in list(self.subscribers):
            await queue.put(event)

    async def shutdown(self):
        self.closed = True

        for queue in list(self.subscribers):
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass


sse_manager = SSEManager()
