from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inti.database import get_db
from inti.models.event import Event

router = APIRouter()


@router.get("/")
async def list_events(
    job_id: str | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(Event)
    if job_id:
        query = query.where(Event.job_id == job_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
    query = query.order_by(Event.created_at.desc()).limit(limit)

    result = await db.execute(query)
    events_list = result.scalars().all()

    return {
        "events": [
            {
                "id": e.id,
                "job_id": e.job_id,
                "event_type": e.event_type,
                "payload_json": e.payload_json,
                "emitted_by": e.emitted_by,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events_list
        ],
        "total": len(events_list),
    }
