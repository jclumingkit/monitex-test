import asyncio
from datetime import datetime
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo

import cv2
from ultralytics import YOLO

from models.detection_event import (
    DetectionEvent,
    DetectionEventSource,
    DetectionEventType,
)
from queue_service.event_queue import event_queue
from snapshot_storage import save_frame_snapshot


WORKER_DIR = Path(__file__).resolve().parent
DEFAULT_VIDEO_PATH = WORKER_DIR / "test_video.mp4"
DEFAULT_MODEL_PATH = WORKER_DIR / "yolo26n.pt"
EVENT_TIMEZONE = ZoneInfo("America/New_York")
SITE_ID = "site-test-1"
ZONE = "frontyard"
PERSON_CLASS_ID = 0
DEFAULT_FPS = 30.0


def make_person_detection_event(
    *,
    track_id: int,
    confidence: float,
    frame_index: int,
    box: list[float],
) -> DetectionEvent:
    return DetectionEvent(
        event_id=f"evt_{uuid.uuid4().hex}",
        site_id=SITE_ID,
        zone=ZONE,
        type=DetectionEventType.PERSON_DETECTED,
        source=DetectionEventSource.CAMERA,
        confidence=confidence,
        timestamp=datetime.now(EVENT_TIMEZONE),
        timezone=str(EVENT_TIMEZONE),
        snapshot_url=None,
        metadata={
            "object": "person",
            "track_id": track_id,
            "frame": frame_index,
            "box": box,
        },
    )


def get_new_person_events(
    result,
    frame_index: int,
    emitted_track_ids: set[int],
) -> list[DetectionEvent]:
    events = []
    if result.boxes is None:
        return events

    for detected_box in result.boxes:
        if not detected_box.is_track or detected_box.id is None:
            continue

        track_id = int(detected_box.id.item())
        if track_id in emitted_track_ids:
            continue

        emitted_track_ids.add(track_id)
        events.append(
            make_person_detection_event(
                track_id=track_id,
                confidence=float(detected_box.conf.item()),
                frame_index=frame_index,
                box=[float(value) for value in detected_box.xyxy[0].tolist()],
            )
        )

    return events


def _open_video(source: Path):
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"Could not open loop video: {source}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    return capture, fps if fps > 0 else DEFAULT_FPS


async def _wait_for_next_frame(
    stop_event: asyncio.Event,
    started_at: float,
    frame_interval: float,
) -> None:
    delay = frame_interval - (asyncio.get_running_loop().time() - started_at)
    if delay <= 0:
        return

    try:
        await asyncio.wait_for(stop_event.wait(), timeout=delay)
    except TimeoutError:
        pass


async def loop_video_worker(
    stop_event: asyncio.Event,
    *,
    source: Path = DEFAULT_VIDEO_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    queue: asyncio.Queue[DetectionEvent] = event_queue,
) -> None:
    model = await asyncio.to_thread(YOLO, str(model_path))
    capture, fps = await asyncio.to_thread(_open_video, source)
    frame_interval = 1 / fps
    frame_index = 0
    emitted_track_ids: set[int] = set()

    print(f"Loop video worker started: {source}")

    try:
        while not stop_event.is_set():
            started_at = asyncio.get_running_loop().time()
            success, frame = await asyncio.to_thread(capture.read)

            if not success:
                await asyncio.to_thread(capture.release)
                capture, fps = await asyncio.to_thread(_open_video, source)
                frame_interval = 1 / fps
                frame_index = 0
                emitted_track_ids.clear()
                continue

            results = await asyncio.to_thread(
                model.track,
                frame,
                persist=frame_index > 0,
                classes=[PERSON_CLASS_ID],
                verbose=False,
            )

            if stop_event.is_set():
                break

            result = results[0]
            events = get_new_person_events(
                result,
                frame_index,
                emitted_track_ids,
            )
            snapshot_id = None

            if events:
                try:
                    snapshot_id = await asyncio.to_thread(
                        save_frame_snapshot,
                        frame,
                    )
                except (OSError, cv2.error) as error:
                    print(f"Could not save detection snapshot: {error}")

            for event in events:
                if snapshot_id:
                    event.snapshot_url = f"/api/snapshots/{snapshot_id}"

                await queue.put(event)
                print(
                    f"Person detected: frame={frame_index} "
                    f"track_id={event.metadata['track_id']} "
                    f"confidence={event.confidence:.2f}"
                )

            frame_index += 1
            await _wait_for_next_frame(
                stop_event,
                started_at,
                frame_interval,
            )
    except asyncio.CancelledError:
        print("Loop video worker cancelled")
        raise
    finally:
        await asyncio.to_thread(capture.release)
        print("Loop video worker stopped")
