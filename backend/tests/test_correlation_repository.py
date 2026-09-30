import unittest

import aiosqlite

from database.sqlite import EventRepository, SCHEMA_PATH


class CorrelationRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = await aiosqlite.connect(":memory:")
        self.db.row_factory = aiosqlite.Row
        await self.db.executescript(SCHEMA_PATH.read_text())
        self.repository = EventRepository(self.db)

    async def asyncTearDown(self):
        await self.db.close()

    async def insert_processed_event(
        self,
        event_id: str,
        *,
        site_id: str = "site-100",
        event_type: str = "person_detected",
        created_at: str = "2026-10-01 12:00:00",
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO events (
                event_id, site_id, zone, type, source, confidence,
                timestamp, snapshot_url, metadata, date_created
            ) VALUES (?, ?, 'lobby', ?, 'camera', 0.9, ?, NULL, '{}', ?)
            """,
            (event_id, site_id, event_type, created_at, created_at),
        )
        await self.db.execute(
            """
            INSERT INTO processed_events (
                id, event_id, severity, false_positive_probability,
                summary, date_created, date_updated
            ) VALUES (?, ?, 'info', 0.1, 'Summary', ?, ?)
            """,
            (event_id, event_id, created_at, created_at),
        )
        await self.db.commit()

    async def test_recent_events_are_limited_to_same_site_and_window(self):
        await self.insert_processed_event(
            "recent-same-site", created_at="2026-10-01 11:59:30"
        )
        await self.insert_processed_event(
            "old-same-site", created_at="2026-10-01 11:57:00"
        )
        await self.insert_processed_event(
            "recent-other-site",
            site_id="site-200",
            created_at="2026-10-01 11:59:45",
        )
        await self.insert_processed_event("current")
        for event_id in (
            "recent-same-site",
            "old-same-site",
            "recent-other-site",
        ):
            await self.repository.complete_event_correlation(
                event_id, "info", "info", None
            )

        rows = await self.repository.get_recent_processed_events(
            "current", 120
        )

        self.assertEqual([row["id"] for row in rows], ["recent-same-site"])

    async def test_escalation_is_idempotent(self):
        await self.insert_processed_event("current")

        first_update = await self.repository.complete_event_correlation(
            "current",
            "info",
            "warning",
            "Repeated activity",
        )
        second_update = await self.repository.complete_event_correlation(
            "current",
            "warning",
            "critical",
            "Duplicate job",
        )
        row = await self.repository.get_processed_event_by_id("current")

        self.assertTrue(first_update)
        self.assertFalse(second_update)
        self.assertEqual(row["severity"], "warning")


if __name__ == "__main__":
    unittest.main()
