import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inti.database import get_db
from inti.models.device import Device
from inti.config import settings

router = APIRouter()


@router.get("/")
async def list_devices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).order_by(Device.registered_at.desc()))
    devices = result.scalars().all()
    return {
        "devices": [
            {
                "id": d.id,
                "device_name": d.device_name,
                "device_type": d.device_type,
                "registered_at": d.registered_at.isoformat() if d.registered_at else None,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
            }
            for d in devices
        ],
        "total": len(devices),
    }


@router.post("/register")
async def register_device(
    device_name: str,
    device_type: str = "mobile",
    public_key: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    device = Device(
        device_name=device_name,
        device_type=device_type,
        public_key=public_key,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    from inti.audit import log_action
    await log_action(
        actor_type="human",
        action="device_registered",
        device_id=device.id,
        summary=f"Dispositivo registrado: {device_name} ({device_type})",
    )

    return {
        "device_id": device.id,
        "device_name": device.device_name,
        "status": "registered",
    }


@router.post("/pair")
async def pair_device():
    token = secrets.token_urlsafe(32)
    return {
        "token": token,
        "expires_in": 300,
        "qr_data": f"dopa-code://pair?token={token}",
    }
