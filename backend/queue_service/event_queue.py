import asyncio

from models.detection_event import DetectionEvent

# Adjust depending on your server processing power
EVENT_QUEUE_SIZE = 1000

event_queue: asyncio.Queue[DetectionEvent] = asyncio.Queue(
    maxsize=EVENT_QUEUE_SIZE
)