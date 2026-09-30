import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from models.detection_event import DetectionEventSource, DetectionEventType
from workers.loop_video_worker.detection import (
    get_new_person_events,
    loop_video_worker,
    make_person_detection_event,
)


class FakeScalar:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


class FakeCoordinates:
    def __init__(self, values):
        self.values = values

    def __getitem__(self, index):
        return self

    def tolist(self):
        return self.values


def make_box(track_id=7, confidence=0.91):
    return SimpleNamespace(
        is_track=True,
        id=FakeScalar(track_id),
        conf=FakeScalar(confidence),
        xyxy=FakeCoordinates([10.0, 20.0, 30.0, 40.0]),
    )


class PersonDetectionEventTests(unittest.TestCase):
    def test_builds_expected_detection_event(self):
        event = make_person_detection_event(
            track_id=7,
            confidence=0.91,
            frame_index=12,
            box=[10.0, 20.0, 30.0, 40.0],
        )

        self.assertTrue(event.event_id.startswith("evt_"))
        self.assertEqual(event.site_id, "site-test-1")
        self.assertEqual(event.zone, "frontyard")
        self.assertEqual(event.type, DetectionEventType.PERSON_DETECTED)
        self.assertEqual(event.source, DetectionEventSource.CAMERA)
        self.assertEqual(event.timezone, "America/New_York")
        self.assertIsNotNone(event.timestamp.utcoffset())
        self.assertIsNone(event.snapshot_url)
        self.assertEqual(
            event.metadata,
            {
                "object": "person",
                "track_id": 7,
                "frame": 12,
                "box": [10.0, 20.0, 30.0, 40.0],
            },
        )

    def test_emits_each_track_once_per_video_loop(self):
        result = SimpleNamespace(boxes=[make_box()])
        emitted_track_ids = set()

        first_events = get_new_person_events(result, 1, emitted_track_ids)
        repeated_events = get_new_person_events(result, 2, emitted_track_ids)
        emitted_track_ids.clear()
        next_loop_events = get_new_person_events(result, 1, emitted_track_ids)

        self.assertEqual(len(first_events), 1)
        self.assertEqual(repeated_events, [])
        self.assertEqual(len(next_loop_events), 1)


class LoopVideoWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_saves_frame_snapshot_for_new_events(self):
        stop_event = asyncio.Event()

        class StoppingQueue(asyncio.Queue):
            async def put(self, item):
                await super().put(item)
                stop_event.set()

        queue = StoppingQueue()
        frame = object()
        capture = MagicMock()
        capture.read.return_value = (True, frame)
        model = MagicMock()
        model.track.return_value = [SimpleNamespace(boxes=[make_box()])]

        with (
            patch(
                "workers.loop_video_worker.detection.YOLO",
                return_value=model,
            ),
            patch(
                "workers.loop_video_worker.detection._open_video",
                return_value=(capture, 30.0),
            ),
            patch(
                "workers.loop_video_worker.detection.save_frame_snapshot",
                return_value="0123456789abcdef0123456789abcdef",
            ) as save_snapshot,
        ):
            await loop_video_worker(
                stop_event,
                source=Path("video.mp4"),
                model_path=Path("model.pt"),
                queue=queue,
            )

        event = queue.get_nowait()
        self.assertEqual(
            event.snapshot_url,
            "/api/snapshots/0123456789abcdef0123456789abcdef",
        )
        save_snapshot.assert_called_once_with(frame)
        capture.release.assert_called_once_with()

    async def test_does_not_enqueue_after_shutdown_is_requested(self):
        stop_event = asyncio.Event()
        queue = asyncio.Queue()
        capture = MagicMock()
        capture.read.return_value = (True, object())
        model = MagicMock()

        def stop_during_inference(*args, **kwargs):
            stop_event.set()
            return [SimpleNamespace(boxes=[make_box()])]

        model.track.side_effect = stop_during_inference

        with (
            patch(
                "workers.loop_video_worker.detection.YOLO",
                return_value=model,
            ),
            patch(
                "workers.loop_video_worker.detection._open_video",
                return_value=(capture, 30.0),
            ),
        ):
            await loop_video_worker(
                stop_event,
                source=Path("video.mp4"),
                model_path=Path("model.pt"),
                queue=queue,
            )

        self.assertTrue(queue.empty())
        capture.release.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
