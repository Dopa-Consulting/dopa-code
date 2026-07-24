import json
import logging
from datetime import datetime, timezone
from typing import Any

from inti.database import async_session
from inti.models.audit_log import AuditLog
from inti.policies import ActorType

logger = logging.getLogger("inti.audit")


async def log_action(
    actor_type: ActorType,
    action: str,
    job_id: str | None = None,
    summary: str | None = None,
    actor_id: str | None = None,
    device_id: str | None = None,
    signature: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        device_id=device_id,
        action=action,
        job_id=job_id,
        summary=summary,
        signature=signature,
        metadata_json=json.dumps(metadata) if metadata else None,
        created_at=datetime.now(timezone.utc),
    )
    try:
        async with async_session() as session:
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
    return entry


async def get_audit_trail(
    job_id: str,
    limit: int = 100,
    actor_type: ActorType | None = None,
) -> list[AuditLog]:
    from sqlalchemy import select

    async with async_session() as session:
        query = select(AuditLog).where(AuditLog.job_id == job_id)
        if actor_type:
            query = query.where(AuditLog.actor_type == actor_type)
        query = query.order_by(AuditLog.created_at.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())
