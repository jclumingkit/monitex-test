from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from database.sqlite import EventRepository
from models.processed_event import ProcessedEventResponse

router = APIRouter(prefix="/api")


@router.get(
    "/get-processed-events",
    response_model=list[ProcessedEventResponse],
)
async def get_processed_events(
    request: Request,
    page: int = Query(default=1, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    status: str | None = Query(default=None),
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
