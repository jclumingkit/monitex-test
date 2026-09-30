import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from ingestion.summarizer import fallback_summary, summarize_event
from models.detection_event import DetectionEvent


def make_event() -> DetectionEvent:
    return DetectionEvent.model_validate({
        "event_id": "evt_test",
        "site_id": "site-100",
        "zone": "lobby",
        "type": "person_detected",
        "source": "camera",
        "confidence": 0.87,
        "timestamp": datetime.fromisoformat("2026-09-15T02:30:00+00:00"),
        "snapshot_url": None,
        "metadata": {"object": "person"},
    })


class SummarizeEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_disables_reasoning(self):
        response = MagicMock()
        response.json.return_value = {
            "choices": [{"message": {"content": "Person detected."}}]
        }

        with (
            patch("ingestion.summarizer.OPENROUTER_KEY", "test-key"),
            patch(
                "ingestion.summarizer.client.post",
                new=AsyncMock(return_value=response),
            ) as post,
        ):
            summary = await summarize_event(make_event())

        self.assertEqual(summary, "Person detected.")
        self.assertEqual(
            post.await_args.kwargs["json"]["reasoning"],
            {"effort": "none"},
        )

    async def test_falls_back_when_content_is_null(self):
        response = MagicMock()
        response.json.return_value = {
            "choices": [{"message": {"content": None}}]
        }
        event = make_event()

        with (
            patch("ingestion.summarizer.OPENROUTER_KEY", "test-key"),
            patch(
                "ingestion.summarizer.client.post",
                new=AsyncMock(return_value=response),
            ),
        ):
            summary = await summarize_event(event)

        self.assertEqual(summary, fallback_summary(event))


if __name__ == "__main__":
    unittest.main()
