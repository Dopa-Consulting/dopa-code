from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inti.database import get_db
from inti.models.device import Device
from inti.webauthn import webauthn

router = APIRouter()


@router.post("/register/begin")
async def begin_registration(
    user_id: str = "local",
    user_name: str = "Developer",
    device_name: str = "PWA",
):
    options = webauthn.generate_registration_options(
        user_id=user_id,
        user_name=user_name,
        device_name=device_name,
    )
    return {"options": options, "challenge": options["challenge"]}


@router.post("/register/complete")
async def complete_registration(
    challenge: str,
    credential_id: str,
    public_key: str,
    device_name: str = "PWA",
    db: AsyncSession = Depends(get_db),
):
    result = webauthn.verify_registration(challenge, credential_id, public_key)
    if not result["verified"]:
        return result

    device = Device(
        user_id=result["user_id"],
        device_name=device_name,
        device_type="mobile",
        public_key=result["public_key"],
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    from inti.audit import log_action
    await log_action(
        actor_type="human",
        action="webauthn_registered",
        device_id=device.id,
        summary=f"Passkey registrada para {device_name}",
    )

    return {
        "verified": True,
        "device_id": device.id,
        "credential_id": credential_id,
    }


@router.post("/authenticate/begin")
async def begin_authentication(
    user_id: str = "local",
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Device)
        .where(Device.user_id == user_id)
        .order_by(Device.registered_at.desc())
        .limit(1)
    )
    device = result.scalar_one_or_none()
    if not device or not device.public_key:
        return {"error": "No passkey registered. Register first."}

    options = webauthn.generate_assertion_options(
        user_id=user_id,
        credential_id=device.public_key,
    )
    return {
        "options": options,
        "challenge": options["challenge"],
        "device_id": device.id,
    }


@router.post("/authenticate/complete")
async def complete_authentication(
    challenge: str,
    credential_id: str,
    user_id: str = "local",
    db: AsyncSession = Depends(get_db),
):
    result = webauthn.verify_assertion(challenge, credential_id, user_id)
    if not result["verified"]:
        return result

    result_device = await db.execute(
        select(Device).where(Device.user_id == user_id)
    )
    device = result_device.scalar_one_or_none()

    from inti.audit import log_action
    await log_action(
        actor_type="human",
        action="webauthn_authenticated",
        device_id=device.id if device else None,
        summary="Autenticacion biometrica exitosa",
    )

    return {
        "verified": True,
        "signature": result["signature"],
        "user_id": user_id,
    }
