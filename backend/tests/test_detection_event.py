import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from models.detection_event import (
    DetectionEvent,
    DetectionEventSource,
    DetectionEventType,
    SITE_NOT_DEFINED,
)


class DetectionEventFallbackTests(unittest.TestCase):
    def assert_fallbacks(self, event: DetectionEvent) -> None:
        self.assertRegex(event.event_id, r"^evt_[0-9a-f]{10}$")
        self.assertEqual(event.site_id, SITE_NOT_DEFINED)
        self.assertEqual(event.zone, "zone-not-defined")
        self.assertEqual(event.type, DetectionEventType.TYPE_NOT_DEFINED)
        self.assertEqual(
            event.source,
            DetectionEventSource.SOURCE_NOT_DEFINED,
        )
        self.assertEqual(event.confidence, 0.0)
        self.assertEqual(event.timestamp.utcoffset(), timezone.utc.utcoffset(None))
        self.assertIsNone(event.timezone)
        self.assertIsNone(event.snapshot_url)
        self.assertEqual(event.metadata, {})

    def test_applies_fallbacks_to_omitted_fields(self):
        self.assert_fallbacks(DetectionEvent.model_validate({}))

    def test_applies_fallbacks_to_null_fields(self):
        event = DetectionEvent.model_validate({
            "event_id": None,
            "site_id": None,
            "zone": None,
            "type": None,
            "source": None,
            "confidence": None,
            "timestamp": None,
            "timezone": None,
            "snapshot_url": None,
            "metadata": None,
        })

        self.assert_fallbacks(event)

    def test_applies_fallbacks_to_blank_string_fields(self):
        event = DetectionEvent.model_validate({
            "event_id": "",
            "site_id": " ",
            "zone": "\t",
            "type": "\n",
            "source": "",
            "timestamp": "  ",
            "timezone": "\t",
            "snapshot_url": "",
        })

        self.assert_fallbacks(event)

    def test_generates_a_unique_event_id_for_each_event(self):
        first = DetectionEvent.model_validate({})
        second = DetectionEvent.model_validate({})

        self.assertNotEqual(first.event_id, second.event_id)

    def test_preserves_supplied_values(self):
        timestamp = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
        event = DetectionEvent.model_validate({
            "event_id": "evt_supplied",
            "site_id": "site-100",
            "zone": "lobby",
            "type": "motion_detected",
            "source": "camera",
            "confidence": 0.75,
            "timestamp": timestamp,
            "timezone": "UTC",
            "snapshot_url": "https://example.com/snapshot.jpg",
            "metadata": {"object": "person"},
        })

        self.assertEqual(event.event_id, "evt_supplied")
        self.assertEqual(event.site_id, "site-100")
        self.assertEqual(event.zone, "lobby")
        self.assertEqual(event.type, DetectionEventType.MOTION_DETECTED)
        self.assertEqual(event.source, DetectionEventSource.CAMERA)
        self.assertEqual(event.confidence, 0.75)
        self.assertEqual(event.timestamp, timestamp)
        self.assertEqual(event.timezone, "UTC")
        self.assertEqual(
            event.snapshot_url,
            "https://example.com/snapshot.jpg",
        )
        self.assertEqual(event.metadata, {"object": "person"})

    def test_rejects_invalid_non_null_confidence(self):
        with self.assertRaises(ValidationError):
            DetectionEvent.model_validate({"confidence": 1.1})

    def test_rejects_blank_confidence(self):
        with self.assertRaises(ValidationError):
            DetectionEvent.model_validate({"confidence": ""})


if __name__ == "__main__":
    unittest.main()
