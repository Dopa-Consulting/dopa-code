from fastapi import APIRouter

from inti.template_service import template_service

router = APIRouter()


@router.get("/")
async def list_templates(tenant_id: str | None = None):
    templates = await template_service.list_templates(tenant_id)
    return {"templates": templates, "total": len(templates)}


@router.post("/{template_id}/customize")
async def customize_template(
    template_id: str,
    tenant_id: str,
    prompt: str,
):
    result = await template_service.customize_template(
        template_id=template_id,
        tenant_id=tenant_id,
        prompt=prompt,
    )
    return result
