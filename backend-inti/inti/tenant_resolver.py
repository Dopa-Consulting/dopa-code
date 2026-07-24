from pathlib import Path
from sqlalchemy import select

from inti.database import async_session
from inti.models.tenant import Tenant


class TenantResolver:
    def __init__(self, workspaces_root: Path | None = None):
        self.workspaces_root = workspaces_root or Path.home() / "dopa-workspaces"

    async def get_tenant(self, tenant_id: str) -> dict | None:
        async with async_session() as session:
            result = await session.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if not tenant:
                return None
            return self._to_context(tenant)

    async def get_tenant_by_name(self, name: str) -> dict | None:
        async with async_session() as session:
            result = await session.execute(
                select(Tenant).where(Tenant.name == name)
            )
            tenant = result.scalar_one_or_none()
            if not tenant:
                return None
            return self._to_context(tenant)

    async def list_tenants(self, project_type: str | None = None) -> list[dict]:
        async with async_session() as session:
            query = select(Tenant)
            if project_type:
                query = query.where(Tenant.project_type == project_type)
            result = await session.execute(query.order_by(Tenant.name))
            return [self._to_context(t) for t in result.scalars().all()]

    async def register_tenant(
        self,
        name: str,
        project_type: str = "dopaweb_theme",
        repo_url: str | None = None,
        dopaweb_url: str | None = None,
        erp_endpoint: str | None = None,
    ) -> dict:
        async with async_session() as session:
            tenant = Tenant(
                name=name,
                project_type=project_type,
                repo_url=repo_url,
                dopaweb_url=dopaweb_url,
                erp_endpoint=erp_endpoint or "http://localhost:3002/api",
            )
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            return self._to_context(tenant)

    async def get_context_for_job(self, job_id: str) -> dict:
        from inti.models.job import Job

        async with async_session() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job or not job.tenant_id:
                return {"tenant": None, "workspace_path": str(self.workspaces_root)}

            tenant = await self.get_tenant(job.tenant_id)
            workspace_path = (
                self.workspaces_root / job.tenant_id
                if not tenant or not tenant.get("repo_url")
                else Path(tenant["workspace_path"])
            )

            return {
                "tenant": tenant,
                "workspace_path": str(workspace_path),
                "project_type": job.profile if not tenant else tenant.get("project_type"),
                "erp_endpoint": tenant.get("erp_endpoint") if tenant else None,
            }

    def _to_context(self, tenant: Tenant) -> dict:
        workspace_path = (
            self.workspaces_root / tenant.id
            if not tenant.repo_url
            else Path(tenant.repo_url.replace("https://github.com/", ""))
        )
        return {
            "tenant_id": tenant.id,
            "name": tenant.name,
            "project_type": tenant.project_type,
            "repo_url": tenant.repo_url,
            "dopaweb_url": tenant.dopaweb_url,
            "erp_endpoint": tenant.erp_endpoint,
            "workspace_path": str(workspace_path),
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        }


tenant_resolver = TenantResolver()
