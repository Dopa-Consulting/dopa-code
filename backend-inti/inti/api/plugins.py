from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inti.database import get_db
from inti.models.plugin_definition import PluginDefinition
from inti.models.skill_definition import SkillDefinition

router = APIRouter()


@router.get("/")
async def list_plugins(db: AsyncSession = Depends(get_db)):
    """Lista todos los plugins instalados."""
    result = await db.execute(select(PluginDefinition).order_by(PluginDefinition.name))
    plugins = result.scalars().all()

    items = []
    for p in plugins:
        # Contar skills asociadas por tag
        tag_result = await db.execute(
            select(SkillDefinition).where(SkillDefinition.tags_json.contains(p.name))
        )
        skills_count = len(tag_result.scalars().all())

        items.append({
            "id": p.id,
            "name": p.name,
            "version": p.version,
            "description": p.description,
            "enabled": p.enabled,
            "path": p.path,
            "skills_count": skills_count,
            "installed_at": p.installed_at.isoformat() if p.installed_at else None,
        })

    return {"plugins": items, "total": len(items)}


@router.post("/scan")
async def scan_plugins():
    """Re-descubre plugins en la carpeta plugins/ sin reiniciar."""
    from inti.plugin_loader import plugin_loader
    result = await plugin_loader.register_plugins()
    return {"status": "ok", **result}


@router.patch("/{plugin_id}")
async def toggle_plugin(plugin_id: str, enabled: bool = True, db: AsyncSession = Depends(get_db)):
    """Activa o desactiva un plugin."""
    result = await db.execute(select(PluginDefinition).where(PluginDefinition.id == plugin_id))
    plugin = result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    plugin.enabled = enabled
    await db.commit()

    return {"id": plugin.id, "name": plugin.name, "enabled": plugin.enabled}
