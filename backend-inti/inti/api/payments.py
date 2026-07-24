from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from inti.database import get_db
from inti.payment_service import PaymentService

router = APIRouter()


@router.get("/")
async def list_integrations(
    tenant_id: str = Query(...),
):
    integrations = await PaymentService.list_integrations(tenant_id)
    return {"integrations": integrations, "total": len(integrations)}


@router.post("/byok")
async def start_byok_integration(
    tenant_id: str,
    psp_name: str,
    psp_display_name: str = "",
    test_mode: bool = True,
):
    result = await PaymentService.start_byok_integration(
        tenant_id=tenant_id,
        psp_name=psp_name,
        psp_display_name=psp_display_name or psp_name,
        test_mode=test_mode,
    )
    return result


@router.get("/{integration_id}")
async def get_integration(integration_id: str):
    result = await PaymentService.get_integration(integration_id)
    if not result:
        return {"error": "Integration not found"}
    return result
