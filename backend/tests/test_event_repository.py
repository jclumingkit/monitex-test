import unittest

import aiosqlite

from database.sqlite import EventRepository


class UpdateEventStatusTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = await aiosqlite.connect(":memory:")
        await self.db.execute(
            """
            CREATE TABLE processed_events (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                date_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await self.db.execute(
            "INSERT INTO processed_events (id, status) VALUES (?, ?)",
            ("event-1", "pending_operator_review"),
        )
        await self.db.execute(
            "INSERT INTO processed_events (id, status) VALUES (?, ?)",
            ("event-2", "pending_operator_review"),
        )
        await self.db.commit()
        self.repository = EventRepository(self.db)

    async def asyncTearDown(self):
        await self.db.close()

    async def test_updates_status(self):
        updated = await self.repository.update_event_status(
            "event-1", "acknowledged"
        )

        cursor = await self.db.execute(
            "SELECT status FROM processed_events WHERE id = ?", ("event-1",)
        )
        row = await cursor.fetchone()

        self.assertTrue(updated)
        self.assertEqual(row[0], "acknowledged")

    async def test_returns_false_when_event_does_not_exist(self):
        updated = await self.repository.update_event_status(
            "missing", "resolved"
        )

        self.assertFalse(updated)

    async def test_rejects_unsupported_status(self):
        with self.assertRaisesRegex(ValueError, "acknowledged.*resolved"):
            await self.repository.update_event_status("event-1", "active")

    async def test_bulk_updates_existing_events(self):
        updated_ids = await self.repository.bulk_update_event_status(
            ["event-1", "event-2", "missing"], "resolved"
        )

        cursor = await self.db.execute(
            "SELECT id FROM processed_events WHERE status = ? ORDER BY id",
            ("resolved",),
        )
        rows = await cursor.fetchall()

        self.assertCountEqual(updated_ids, ["event-1", "event-2"])
        self.assertEqual([row[0] for row in rows], ["event-1", "event-2"])

    async def test_bulk_update_rejects_empty_event_ids(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            await self.repository.bulk_update_event_status([], "resolved")


class GetProcessedEventsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = await aiosqlite.connect(":memory:")
        self.db.row_factory = aiosqlite.Row
        await self.db.executescript(
            """
            CREATE TABLE events (
                event_id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                zone TEXT NOT NULL,
                type TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp TEXT NOT NULL,
                snapshot_url TEXT,
                date_created TEXT NOT NULL
            );
            CREATE TABLE processed_events (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                summary TEXT NOT NULL,
                status TEXT NOT NULL,
                date_created TEXT NOT NULL,
                date_updated TEXT NOT NULL
            );
            """
        )
        self.repository = EventRepository(self.db)
        self.repository.PROCESSED_EVENTS_PAGE_SIZE = 3

        events = [
            ("pending-critical-new", "pending_operator_review", "critical", "2026-01-06 00:00:00"),
            ("pending-critical-old", "pending_operator_review", "critical", "2026-01-01 00:00:00"),
            ("pending-warning", "pending_operator_review", "warning", "2026-01-05 13:00:00"),
            ("pending-info", "pending_operator_review", "info", "2026-01-04 00:00:00"),
            ("acknowledged-critical", "acknowledged", "critical", "2026-01-07 00:00:00"),
            ("acknowledged-info", "acknowledged", "info", "2026-01-08 00:00:00"),
            ("resolved-critical", "resolved", "critical", "2026-01-09 00:00:00"),
        ]
        for event_id, status, severity, created_at in events:
            await self.db.execute(
                """
                INSERT INTO events (
                    event_id, site_id, zone, type, source, confidence,
                    timestamp, snapshot_url, date_created
                ) VALUES (?, 'site', 'zone', 'motion_detected', 'camera', 0.9, ?, NULL, ?)
                """,
                (event_id, created_at, created_at),
            )
            await self.db.execute(
                """
                INSERT INTO processed_events (
                    id, event_id, severity, summary, status,
                    date_created, date_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event_id,
                    severity,
                    event_id,
                    status,
                    created_at,
                    created_at,
                ),
            )
        await self.db.commit()

    async def asyncTearDown(self):
        await self.db.close()

    async def test_default_order_prioritizes_status_then_severity(self):
        rows = []
        for page in range(1, 4):
            rows.extend(await self.repository.get_processed_events(page=page))

        self.assertEqual(
            [row["id"] for row in rows],
            [
                "pending-critical-new",
                "pending-critical-old",
                "pending-warning",
                "pending-info",
                "acknowledged-critical",
                "acknowledged-info",
                "resolved-critical",
            ],
        )

    async def test_status_filter_keeps_severity_order(self):
        rows = await self.repository.get_processed_events(
            status="acknowledged"
        )

        self.assertEqual(
            [row["id"] for row in rows],
            ["acknowledged-critical", "acknowledged-info"],
        )

    async def test_date_sort_is_globally_chronological(self):
        rows = await self.repository.get_processed_events(
            sort_by="date_created", date_order="desc"
        )

        self.assertEqual(
            [row["id"] for row in rows],
            [
                "resolved-critical",
                "acknowledged-info",
                "acknowledged-critical",
            ],
        )

    async def test_iso_date_filter_matches_sqlite_timestamps(self):
        rows = await self.repository.get_processed_events(
            date_from="2026-01-05T12:00:00Z",
            status="pending_operator_review",
        )

        self.assertEqual(
            [row["id"] for row in rows],
            ["pending-critical-new", "pending-warning"],
        )

    async def test_site_timeline_uses_event_timestamp_ascending(self):
        await self.db.execute(
            "UPDATE events SET timestamp = ? WHERE event_id = ?",
            ("2025-12-31 00:00:00", "pending-critical-new"),
        )
        await self.db.execute(
            "UPDATE events SET timestamp = ? WHERE event_id = ?",
            ("2026-02-01 00:00:00", "pending-critical-old"),
        )
        await self.db.commit()

        rows = []
        for page in range(1, 4):
            rows.extend(
                await self.repository.get_processed_events_by_site(
                    "site", page
                )
            )

        self.assertEqual(
            [row["id"] for row in rows],
            [
                "pending-critical-new",
                "pending-info",
                "pending-warning",
                "acknowledged-critical",
                "acknowledged-info",
                "resolved-critical",
                "pending-critical-old",
            ],
        )

    async def test_site_timeline_filters_and_paginates(self):
        await self.db.execute(
            "UPDATE events SET site_id = ? WHERE event_id = ?",
            ("other-site", "pending-warning"),
        )
        await self.db.commit()

        first_page = await self.repository.get_processed_events_by_site(
            "site", page=1
        )
        second_page = await self.repository.get_processed_events_by_site(
            "site", page=2
        )

        self.assertEqual(len(first_page), 3)
        self.assertEqual(len(second_page), 3)
        self.assertNotIn(
            "pending-warning",
            [row["id"] for row in first_page + second_page],
        )

    async def test_site_timeline_rejects_invalid_page(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            await self.repository.get_processed_events_by_site("site", page=0)


if __name__ == "__main__":
    unittest.main()
