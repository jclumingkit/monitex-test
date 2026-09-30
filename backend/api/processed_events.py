from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from database.sqlite import EventRepository
from models.processed_event import (
    BulkUpdateEventStatusRequest,
    BulkUpdateEventStatusResponse,
    ProcessedEventResponse,
    UpdateEventStatusRequest,
    UpdateEventStatusResponse,
)

router = APIRouter(prefix="/api")


@router.patch(
    "/processed-events/status",
    response_model=BulkUpdateEventStatusResponse,
)
async def bulk_update_event_status(
    update: BulkUpdateEventStatusRequest,
    request: Request,
) -> BulkUpdateEventStatusResponse:
    repository: EventRepository = request.app.state.repository

    try:
        updated_ids = await repository.bulk_update_event_status(
            update.event_ids, update.status
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return BulkUpdateEventStatusResponse(ids=updated_ids, status=update.status)


@router.patch(
    "/processed-events/{event_id}/status",
    response_model=UpdateEventStatusResponse,
)
async def update_event_status(
    event_id: str,
    update: UpdateEventStatusRequest,
    request: Request,
) -> UpdateEventStatusResponse:
    repository: EventRepository = request.app.state.repository

    try:
        updated = await repository.update_event_status(event_id, update.status)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if not updated:
        raise HTTPException(status_code=404, detail="Processed event not found")

    return UpdateEventStatusResponse(id=event_id, status=update.status)


@router.get(
    "/get-processed-events",
    response_model=list[ProcessedEventResponse],
)
async def get_processed_events(
    request: Request,
    page: int = Query(default=1, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    status: Literal[
        "pending_operator_review", "acknowledged", "resolved"
    ]
    | None = Query(default=None),
    sort_by: Literal["severity", "date_created"] = Query(default="severity"),
    date_order: Literal["asc", "desc"] = Query(default="desc"),
) -> list[ProcessedEventResponse]:
    repository: EventRepository = request.app.state.repository

    try:
        rows = await repository.get_processed_events(
            page=page,
            date_from=date_from,
            date_to=date_to,
            status=status,
            sort_by=sort_by,
            date_order=date_order,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return [ProcessedEventResponse.model_validate(dict(row)) for row in rows]
