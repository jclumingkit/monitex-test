import unittest

from ingestion.correlator import correlate_event


def make_current(
    *,
    event_type: str = "person_detected",
    severity: str = "info",
) -> dict:
    return {
        "type": event_type,
        "severity": severity,
        "date_created": "2026-10-01 12:00:00",
    }


def make_recent(
    event_type: str = "person_detected",
    created_at: str = "2026-10-01 11:59:30",
) -> dict:
    return {"type": event_type, "date_created": created_at}


class CorrelateEventTests(unittest.TestCase):
    def test_escalates_third_repeated_event_one_level(self):
        decision = correlate_event(
            make_current(),
            [make_recent(), make_recent(created_at="2026-10-01 11:59:45")],
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.severity.value, "warning")
        self.assertIn("3 person_detected events", decision.reason)

    def test_does_not_escalate_two_repeated_events(self):
        decision = correlate_event(make_current(), [make_recent()])

        self.assertIsNone(decision)

    def test_ignores_repeated_events_outside_one_minute(self):
        decision = correlate_event(
            make_current(),
            [
                make_recent(created_at="2026-10-01 11:58:30"),
                make_recent(created_at="2026-10-01 11:58:45"),
            ],
        )

        self.assertIsNone(decision)

    def test_escalates_combined_intrusion_signals_to_critical(self):
        decision = correlate_event(
            make_current(),
            [make_recent(event_type="door_forced")],
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.severity.value, "critical")
        self.assertIn("Combined", decision.reason)

    def test_does_not_escalate_an_already_critical_event(self):
        decision = correlate_event(
            make_current(severity="critical"),
            [make_recent(), make_recent(created_at="2026-10-01 11:59:45")],
        )

        self.assertIsNone(decision)


if __name__ == "__main__":
    unittest.main()
