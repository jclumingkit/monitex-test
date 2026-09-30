import json
from pathlib import Path
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

    async def save_processed_event(self, event):
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
                str(uuid4()),
                event.event_id,
                event.severity.value,
                event.false_positive_probability,
                event.summary,
            ),
        )

        await self.db.commit()
