from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from snapshot_storage import get_snapshot_path


router = APIRouter(prefix="/api/snapshots")


@router.get("/{snapshot_id}", response_class=FileResponse)
async def get_snapshot(snapshot_id: str) -> FileResponse:
    snapshot_path = get_snapshot_path(snapshot_id)

    if snapshot_path is None or not snapshot_path.is_file():
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return FileResponse(
        snapshot_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
