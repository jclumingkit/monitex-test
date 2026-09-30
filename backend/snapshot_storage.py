import re
import uuid
from pathlib import Path

import cv2


SNAPSHOT_DIR = Path(__file__).resolve().parent / "tmp" / "snapshots"
SNAPSHOT_ID_PATTERN = re.compile(r"[0-9a-f]{32}")


def save_frame_snapshot(frame) -> str | None:
    snapshot_id = uuid.uuid4().hex
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = SNAPSHOT_DIR / f"{snapshot_id}.jpg"

    if not cv2.imwrite(str(snapshot_path), frame):
        return None

    return snapshot_id


def get_snapshot_path(snapshot_id: str) -> Path | None:
    if not SNAPSHOT_ID_PATTERN.fullmatch(snapshot_id):
        return None

    return SNAPSHOT_DIR / f"{snapshot_id}.jpg"
