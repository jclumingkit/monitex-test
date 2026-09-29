import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from ingestion.classifier import (
    QUESTIONS,
    build_triage_state,
    event_classifier,
    static_classifier,
)
from models.detection_event import DetectionEvent


def make_event(**overrides) -> DetectionEvent:
    payload = {
        "event_id": "evt_test",
        "site_id": "site-100",
        "zone": "north-perimeter",
        "type": "motion_detected",
        "source": "camera",
        "confidence": 0.87,
        "timestamp": datetime.fromisoformat("2026-09-15T02:30:00+00:00"),
        "snapshot_url": None,
        "metadata": {"object": "person"},
    }
    payload.update(overrides)
    return DetectionEvent.model_validate(payload)


class BuildTriageStateTests(unittest.TestCase):
    def test_uses_explicit_timezone_when_available(self):
        state = build_triage_state(make_event(timezone="America/New_York"))

        self.assertEqual(state["time_context"]["timezone"], "America/New_York")
        self.assertEqual(state["time_context"]["local_hour"], 22)
        self.assertEqual(state["time_context"]["period"], "night")
        self.assertEqual(state["time_context"]["day_of_week"], "Monday")
        self.assertEqual(
            state["time_context"]["local_timestamp"],
            "2026-09-14T22:30:00-04:00",
        )
        self.assertEqual(state["event"]["event_id"], "evt_test")

    def test_uses_timestamp_offset_without_explicit_timezone(self):
        state = build_triage_state(
            make_event(
                timestamp=datetime.fromisoformat(
                    "2026-09-15T22:30:00-04:00"
                )
            )
        )

        self.assertIsNone(state["time_context"]["timezone"])
        self.assertEqual(
            state["time_context"]["local_timestamp"],
            "2026-09-15T22:30:00-04:00",
        )
        self.assertEqual(state["time_context"]["period"], "night")

    def test_assigns_expected_periods(self):
        expected_periods = {
            2: "overnight",
            8: "morning",
            14: "afternoon",
            19: "evening",
            23: "night",
        }

        for hour, expected in expected_periods.items():
            with self.subTest(hour=hour):
                event = make_event(
                    timestamp=datetime.fromisoformat(
                        f"2026-09-15T{hour:02}:00:00-04:00"
                    )
                )
                self.assertEqual(
                    build_triage_state(event)["time_context"]["period"],
                    expected,
                )


class DetectionEventTimezoneTests(unittest.TestCase):
    def test_rejects_invalid_timezone(self):
        with self.assertRaises(ValidationError):
            make_event(timezone="Not/A_Timezone")

    def test_rejects_timestamp_without_offset(self):
        with self.assertRaises(ValidationError):
            make_event(timestamp=datetime.fromisoformat("2026-09-15T22:30:00"))


class EventClassifierTests(unittest.IsolatedAsyncioTestCase):
    async def test_sends_enriched_state(self):
        response = MagicMock()
        response.json.return_value = {
            "answers": {
                "severity": {"choice": "warning"},
                "false_positive": {"noul": 0.10},
            }
        }

        with (
            patch("ingestion.classifier.openrouter_key", "test-key"),
            patch(
                "ingestion.classifier.client.post",
                new=AsyncMock(return_value=response),
            ) as post,
        ):
            result = await event_classifier(
                make_event(timezone="America/New_York")
            )

        request = post.await_args.kwargs["json"]
        self.assertEqual(request["questions"], QUESTIONS)
        self.assertEqual(request["state"]["time_context"]["period"], "night")
        self.assertEqual(result.severity.value, "warning")
        self.assertFalse(result.false_positive)
        response.raise_for_status.assert_called_once_with()

    def test_static_fallback_classifies_event(self):
        result = static_classifier(make_event())

        self.assertEqual(result.severity.value, "info")
        self.assertFalse(result.false_positive)
        self.assertEqual(result.false_positive_probability, 0.10)


if __name__ == "__main__":
    unittest.main()
