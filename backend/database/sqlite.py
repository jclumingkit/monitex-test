import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

import aiosqlite

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "monitex.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def normalize_sqlite_datetime(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("date filters must be valid ISO 8601 values") from error

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed.isoformat(sep=" ", timespec="microseconds")

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
    PROCESSED_EVENTS_PAGE_SIZE = 14

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
        normalized_date_from = (
            normalize_sqlite_datetime(date_from) if date_from else None
        )
        normalized_date_to = (
            normalize_sqlite_datetime(date_to) if date_to else None
        )
        if (
            normalized_date_from
            and normalized_date_to
            and normalized_date_from > normalized_date_to
        ):
            raise ValueError("date_from must be before or equal to date_to")

        filters = []
        parameters = []

        if normalized_date_from:
            filters.append("processed_events.date_created >= ?")
            parameters.append(normalized_date_from)
        if normalized_date_to:
            filters.append("processed_events.date_created <= ?")
            parameters.append(normalized_date_to)
        if status:
            filters.append("processed_events.status = ?")
            parameters.append(status)

        where_clause = ""
        if filters:
            where_clause = "WHERE " + " AND ".join(filters)

        if sort_by == "severity":
            status_order = ""
            if not status:
                status_order = """
                    CASE processed_events.status
                        WHEN 'pending_operator_review' THEN 1
                        WHEN 'acknowledged' THEN 2
                        WHEN 'resolved' THEN 3
                        ELSE 4
                    END ASC,
                """
            order_clause = f"""
                {status_order}
                CASE processed_events.severity
                    WHEN 'critical' THEN 1
                    WHEN 'warning' THEN 2
                    WHEN 'info' THEN 3
                    ELSE 4
                END ASC,
                processed_events.date_created DESC,
                processed_events.id ASC
            """
        else:
            order_clause = (
                f"processed_events.date_created {date_order.upper()}, "
                "processed_events.id ASC"
            )

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

    async def update_event_status(
        self,
        event_id: str,
        status: Literal["acknowledged", "resolved"],
    ) -> bool:
        if status not in {"acknowledged", "resolved"}:
            raise ValueError("status must be 'acknowledged' or 'resolved'")

        cursor = await self.db.execute(
            """
            UPDATE processed_events
            SET status = ?, date_updated = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, event_id),
        )
        await self.db.commit()

        return cursor.rowcount > 0

    async def bulk_update_event_status(
        self,
        event_ids: list[str],
        status: Literal["acknowledged", "resolved"],
    ) -> list[str]:
        if status not in {"acknowledged", "resolved"}:
            raise ValueError("status must be 'acknowledged' or 'resolved'")
        if not event_ids:
            raise ValueError("event_ids must contain at least one event ID")

        unique_event_ids = list(dict.fromkeys(event_ids))
        placeholders = ", ".join("?" for _ in unique_event_ids)
        cursor = await self.db.execute(
            f"""
            UPDATE processed_events
            SET status = ?, date_updated = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
            RETURNING id
            """,
            (status, *unique_event_ids),
        )
        rows = await cursor.fetchall()
        await self.db.commit()

        return [row[0] for row in rows]

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

    async def get_processed_event_by_id(
        self, processed_event_id: str
    ) -> aiosqlite.Row | None:
        cursor = await self.db.execute(
            """
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
                events.snapshot_url
            FROM processed_events
            JOIN events ON events.event_id = processed_events.event_id
            WHERE processed_events.id = ?
            """,
            (processed_event_id,),
        )
        return await cursor.fetchone()

    async def get_recent_processed_events(
        self,
        processed_event_id: str,
        window_seconds: int,
    ) -> list[aiosqlite.Row]:
        cursor = await self.db.execute(
            """
            SELECT
                recent_processed.id,
                recent_events.type,
                recent_processed.date_created
            FROM processed_events AS recent_processed
            JOIN events AS recent_events
                ON recent_events.event_id = recent_processed.event_id
            JOIN event_correlations AS recent_correlation
                ON recent_correlation.processed_event_id = recent_processed.id
            JOIN processed_events AS current_processed
                ON current_processed.id = ?
            JOIN events AS current_event
                ON current_event.event_id = current_processed.event_id
            WHERE recent_processed.id != current_processed.id
              AND recent_events.site_id = current_event.site_id
              AND julianday(recent_processed.date_created)
                  <= julianday(current_processed.date_created)
              AND (
                  julianday(current_processed.date_created)
                  - julianday(recent_processed.date_created)
              ) * 86400 <= ?
            ORDER BY recent_processed.date_created DESC
            """,
            (processed_event_id, window_seconds),
        )
        return await cursor.fetchall()

    async def complete_event_correlation(
        self,
        processed_event_id: str,
        base_severity: str,
        final_severity: str,
        reason: str | None,
    ) -> bool:
        cursor = await self.db.execute(
            """
            INSERT OR IGNORE INTO event_correlations (
                processed_event_id,
                base_severity,
                final_severity,
                reason
            ) VALUES (?, ?, ?, ?)
            """,
            (
                processed_event_id,
                base_severity,
                final_severity,
                reason,
            ),
        )

        if cursor.rowcount == 0:
            await self.db.commit()
            return False

        if final_severity == base_severity:
            await self.db.commit()
            return False

        await self.db.execute(
            """
            UPDATE processed_events
            SET severity = ?, date_updated = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (final_severity, processed_event_id),
        )
        await self.db.commit()
        return True
