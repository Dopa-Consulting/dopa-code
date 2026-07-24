import json
import logging
from pathlib import Path

from inti.config import settings
from inti.database import async_session
from inti.models.job import Job
from inti.tenant_resolver import tenant_resolver

logger = logging.getLogger("inti.templates")


class TemplateService:
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent.parent / "agent-runtime" / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    async def list_templates(self, tenant_id: str | None = None) -> list[dict]:
        if settings.dopa_code_dummy:
            return self._dummy_templates()

        templates = []
        for d in self.templates_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                templates.append({
                    "id": d.name,
                    "name": d.name.replace("-", " ").title(),
                    "path": str(d),
                    "has_git": (d / ".git").exists(),
                })

        if not templates:
            templates = self._dummy_templates()

        return templates

    async def customize_template(
        self, template_id: str, tenant_id: str, prompt: str
    ) -> dict:
        context = await tenant_resolver.get_tenant(tenant_id)
        if not context:
            return {"error": "Tenant not found"}

        repo_path = Path(context["workspace_path"])

        async with async_session() as session:
            job = Job(
                title=f"Customize {template_id} for {context['name']}",
                description=prompt,
                profile="dopaweb_theme",
                tenant_id=tenant_id,
                repo_id=str(repo_path),
                branch_name=f"intl/customize-{template_id}",
                status="planned",
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)

            from inti.audit import log_action
            await log_action(
                actor_type="human",
                action="template_customization_requested",
                job_id=job.id,
                summary=f"Customize template {template_id} for tenant {tenant_id}",
            )

            return {
                "job_id": job.id,
                "template_id": template_id,
                "tenant_id": tenant_id,
                "status": "planned",
                "workspace": str(repo_path),
            }

    def _dummy_templates(self) -> list[dict]:
        return [
            {
                "id": "dopa-store-classic",
                "name": "Dopa Store Classic",
                "path": str(self.templates_dir / "dopa-store-classic"),
                "has_git": False,
            },
            {
                "id": "dopa-store-minimal",
                "name": "Dopa Store Minimal",
                "path": str(self.templates_dir / "dopa-store-minimal"),
                "has_git": False,
            },
            {
                "id": "dopa-store-pro",
                "name": "Dopa Store Pro",
                "path": str(self.templates_dir / "dopa-store-pro"),
                "has_git": False,
            },
        ]


template_service = TemplateService()
