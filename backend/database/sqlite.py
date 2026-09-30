import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

import aiosqlite

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "monitex.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"

async def connect_db() -> aiosqlite.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    db = await aiosqlite.connect(DB_PATH)

    # Lets SELECT results behave more like dictionaries.
    db.row_factory = aiosqlite.Row

    return db


async def initialize_db(db: aiosqlite.Connection) -> None:
    schema = SCHEMA_PATH.read_text()
    await db.executescript(schema)

    pass


class EventRepository:
    PROCESSED_EVENTS_PAGE_SIZE = 10

    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def save_event(self, event):
        await self.db.execute(
            """
            INSERT INTO events (
                event_id,
                site_id,
                zone,
                type,
                source,
                confidence,
                timestamp,
                timezone,
                snapshot_url,
                metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.site_id,
                event.zone,
                event.type.value,
                event.source.value,
                event.confidence,
                event.timestamp,
                event.timezone,
                event.snapshot_url,
                json.dumps(event.metadata),
            ),
        )

        await self.db.commit()

    async def get_processed_events(
        self,
        page: int = 1,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        status: str | None = None,
        sort_by: Literal["severity", "date_created"] = "severity",
        date_order: Literal["asc", "desc"] = "desc",
    ) -> list[aiosqlite.Row]:
        if page < 1:
            raise ValueError("page must be at least 1")
        if sort_by not in {"severity", "date_created"}:
            raise ValueError("sort_by must be 'severity' or 'date_created'")
        if date_order not in {"asc", "desc"}:
            raise ValueError("date_order must be 'asc' or 'desc'")
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be before or equal to date_to")

        filters = []
        parameters = []

        if date_from:
            filters.append("events.date_created >= ?")
            parameters.append(date_from)
        if date_to:
            filters.append("events.date_created <= ?")
            parameters.append(date_to)
        if status:
            filters.append("processed_events.status = ?")
            parameters.append(status)

        where_clause = ""
        if filters:
            where_clause = "WHERE " + " AND ".join(filters)

        if sort_by == "severity":
            order_clause = """
                CASE processed_events.severity
                    WHEN 'critical' THEN 1
                    WHEN 'warning' THEN 2
                    WHEN 'info' THEN 3
                END ASC,
                events.date_created DESC,
                processed_events.id ASC
            """
        else:
            order_clause = f"events.date_created {date_order.upper()}, processed_events.id ASC"

        offset = (page - 1) * self.PROCESSED_EVENTS_PAGE_SIZE
        parameters.extend([self.PROCESSED_EVENTS_PAGE_SIZE, offset])

        cursor = await self.db.execute(
            f"""
            SELECT
                processed_events.id,
                processed_events.event_id,
                processed_events.severity,
                processed_events.summary,
                processed_events.status,
                processed_events.date_created,
                processed_events.date_updated,
                events.site_id,
                events.zone,
                events.type,
                events.source,
                events.confidence,
                events.timestamp,
                events.snapshot_url,
                events.date_created AS event_date_created
            FROM processed_events
            JOIN events ON events.event_id = processed_events.event_id
            {where_clause}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
            """,
            parameters,
        )
        return await cursor.fetchall()

    async def save_processed_event(self, event):
        processed_event_id = str(uuid4())

        await self.db.execute(
            """
            INSERT INTO processed_events (
                id,
                event_id,
                severity,
                false_positive_probability,
                summary
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                processed_event_id,
                event.event_id,
                event.severity.value,
                event.false_positive_probability,
                event.summary,
            ),
        )

        await self.db.commit()
        return processed_event_id
