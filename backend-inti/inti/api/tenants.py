from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inti.database import get_db
from inti.models.tenant import Tenant
from inti.tenant_resolver import tenant_resolver

router = APIRouter()


@router.get("/")
async def list_tenants(
    project_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    tenants = await tenant_resolver.list_tenants(project_type)
    return {"tenants": tenants, "total": len(tenants)}


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str):
    tenant = await tenant_resolver.get_tenant(tenant_id)
    if not tenant:
        return {"error": "Tenant not found"}
    return tenant


@router.post("/")
async def register_tenant(
    name: str,
    project_type: str = "dopaweb_theme",
    repo_url: str | None = None,
    dopaweb_url: str | None = None,
    erp_endpoint: str | None = None,
):
    tenant = await tenant_resolver.register_tenant(
        name=name,
        project_type=project_type,
        repo_url=repo_url,
        dopaweb_url=dopaweb_url,
        erp_endpoint=erp_endpoint,
    )
    return tenant


@router.get("/{tenant_id}/context")
async def get_tenant_context(tenant_id: str):
    tenant = await tenant_resolver.get_tenant(tenant_id)
    if not tenant:
        return {"error": "Tenant not found"}

    from inti.erp_context import erp_context

    schemas = await erp_context.get_erp_schemas(tenant_id)
    rules = await erp_context.get_business_rules(tenant_id)

    return {
        "tenant": tenant,
        "erp_schemas": schemas,
        "business_rules": rules,
    }
