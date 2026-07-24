import base64
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from inti.config import settings
from inti.database import async_session
from inti.models.payment_integration import PaymentIntegration
from inti.models.job import Job
from inti.tenant_resolver import tenant_resolver
from inti.policies import PROJECT_TYPE_DEFAULTS

logger = logging.getLogger("inti.payments")


class PaymentService:

    @staticmethod
    async def start_byok_integration(
        tenant_id: str,
        psp_name: str,
        psp_display_name: str = "",
        credentials: dict | None = None,
        test_mode: bool = True,
    ) -> dict:
        if settings.dopa_code_dummy:
            return PaymentService._dummy_result(tenant_id, psp_name)

        encrypted = None
        if credentials:
            creds_json = json.dumps(credentials)
            encrypted = base64.b64encode(creds_json.encode()).decode()

        context = await tenant_resolver.get_tenant(tenant_id)
        if not context:
            return {"error": "Tenant not found"}

        async with async_session() as session:
            integration = PaymentIntegration(
                tenant_id=tenant_id,
                psp_name=psp_name,
                psp_display_name=psp_display_name or psp_name,
                credentials_encrypted=encrypted,
                status="planned",
                test_mode=test_mode,
                environment="sandbox" if test_mode else "production",
            )
            session.add(integration)
            await session.commit()
            await session.refresh(integration)

            erp_ctx = context.get("erp_endpoint", "")
            prompt = PaymentService._build_integration_prompt(
                psp_name, context, test_mode
            )

            policy = PROJECT_TYPE_DEFAULTS.get("dopaweb_payment", {})
            job = Job(
                title=f"Integrate {psp_name} for {context['name']}",
                description=prompt,
                profile="dopaweb_payment",
                tenant_id=tenant_id,
                repo_id=context.get("repo_url", str(PaymentService._workspace_for(tenant_id))),
                branch_name=f"intl/payment-{psp_name.lower()}",
                autonomy_level=policy.get("autonomy", "human_gatekeeper"),
                status="planned",
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)

            integration.job_id = job.id
            await session.commit()

            from inti.audit import log_action
            await log_action(
                actor_type="human",
                action="byok_payment_started",
                job_id=job.id,
                summary=f"Integracion BYOK de {psp_name} para tenant {tenant_id}",
            )

            return {
                "integration_id": integration.id,
                "job_id": job.id,
                "psp_name": psp_name,
                "status": "planned",
                "test_mode": test_mode,
            }

    @staticmethod
    async def list_integrations(tenant_id: str) -> list[dict]:
        async with async_session() as session:
            result = await session.execute(
                select(PaymentIntegration)
                .where(PaymentIntegration.tenant_id == tenant_id)
                .order_by(PaymentIntegration.created_at.desc())
            )
            integrations = result.scalars().all()
            return [
                {
                    "id": i.id,
                    "psp_name": i.psp_name,
                    "psp_display_name": i.psp_display_name,
                    "status": i.status,
                    "test_mode": i.test_mode,
                    "environment": i.environment,
                    "job_id": i.job_id,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in integrations
            ]

    @staticmethod
    async def get_integration(integration_id: str) -> dict | None:
        async with async_session() as session:
            result = await session.execute(
                select(PaymentIntegration).where(PaymentIntegration.id == integration_id)
            )
            i = result.scalar_one_or_none()
            if not i:
                return None
            return {
                "id": i.id,
                "tenant_id": i.tenant_id,
                "psp_name": i.psp_name,
                "psp_display_name": i.psp_display_name,
                "status": i.status,
                "test_mode": i.test_mode,
                "environment": i.environment,
                "job_id": i.job_id,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }

    @staticmethod
    def _build_integration_prompt(
        psp_name: str, tenant_context: dict, test_mode: bool
    ) -> str:
        return f"""Integrate {psp_name} as a payment method for DopaWeb ecommerce.

Project: {tenant_context.get('name', 'Unknown')}
DopaWeb URL: {tenant_context.get('dopaweb_url', 'N/A')}
ERP Endpoint: {tenant_context.get('erp_endpoint', 'N/A')}
Mode: {'sandbox (test)' if test_mode else 'production'}

Requirements:
1. Add {psp_name} checkout flow (frontend: React/Next.js component)
2. Configure webhook handler to receive payment events
3. Map {psp_name} payment states to Dopa ERP invoice states (pending, paid, refunded, failed)
4. Ensure country-specific tax rules are respected (from ERP)
5. Add test coverage for success, failure, and cancel flows
6. Keep existing ERP integrations intact (facturacion SUNAT, etc.)
"""

    @staticmethod
    def _workspace_for(tenant_id: str) -> Path:
        from pathlib import Path
        return Path.home() / "dopa-workspaces" / tenant_id

    @staticmethod
    def _dummy_result(tenant_id: str, psp_name: str) -> dict:
        return {
            "integration_id": f"dummy-{tenant_id[:8]}",
            "job_id": f"dummy-job-{tenant_id[:8]}",
            "psp_name": psp_name,
            "status": "planned",
            "test_mode": True,
            "message": "[DUMMY] BYOK integration simulated",
        }

from pathlib import Path
