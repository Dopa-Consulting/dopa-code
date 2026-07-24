from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from inti.database import get_db
from inti.audit import get_audit_trail
from inti.policies import ActorType

router = APIRouter()


@router.get("/trail/{job_id}")
async def get_trail(
    job_id: str,
    limit: int = Query(100, le=500),
    actor_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    entries = await get_audit_trail(
        job_id=job_id,
        limit=limit,
        actor_type=actor_type,
    )
    return {
        "entries": [
            {
                "id": e.id,
                "actor_type": e.actor_type,
                "actor_id": e.actor_id,
                "device_id": e.device_id,
                "action": e.action,
                "summary": e.summary,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
        "total": len(entries),
    }
