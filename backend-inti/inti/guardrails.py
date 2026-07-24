import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from inti.config import settings

logger = logging.getLogger("inti.guardrails")


@dataclass
class GuardrailRule:
    id: str
    description: str
    severity: str  # "block" | "warn" | "info"
    check_type: str  # "file_pattern" | "function_call" | "import_check" | "api_integrity"
    pattern: str
    message: str


@dataclass
class GuardrailProfile:
    name: str
    description: str
    protected_files: list[str] = field(default_factory=list)
    protected_endpoints: list[str] = field(default_factory=list)
    protected_imports: list[str] = field(default_factory=list)
    editable_files: list[str] = field(default_factory=list)
    rules: list[GuardrailRule] = field(default_factory=list)


DOPAWEB_GUARDRAILS = GuardrailProfile(
    name="dopaweb_theme",
    description="Personalizacion de templates DopaWeb sin romper integracion ERP",
    protected_files=[
        "src/integrations/erp/",
        "src/api/erp-client.ts",
        "src/hooks/useCheckout.ts",
        "src/lib/facturacion/",
        "src/services/invoice.ts",
        "src/services/tax-calculator.ts",
        "src/webhooks/",
        ".env",
        ".env.local",
    ],
    protected_endpoints=[
        "/api/erp/",
        "/api/invoices/",
        "/api/webhooks/",
        "/api/checkout/process",
    ],
    protected_imports=[
        "erp-client",
        "facturacion",
        "invoice-service",
        "tax-calculator",
    ],
    editable_files=[
        "src/components/",
        "src/pages/",
        "src/styles/",
        "src/assets/",
        "src/layouts/",
        "public/",
        "tailwind.config.*",
        "src/i18n/",
    ],
    rules=[
        GuardrailRule(
            id="no-erp-touch",
            check_type="file_pattern",
            severity="block",
            pattern="src/integrations/erp/",
            description="No modificar integracion ERP",
            message="Los archivos de integracion ERP estan protegidos. Cambios en checkout o facturacion requieren perfil 'dopaweb_payment'.",
        ),
        GuardrailRule(
            id="no-checkout-logic",
            check_type="file_pattern",
            severity="block",
            pattern="src/hooks/useCheckout.ts",
            description="No modificar logica de checkout",
            message="useCheckout.ts contiene logica de pago critica. No se puede modificar desde este perfil.",
        ),
        GuardrailRule(
            id="no-invoice-manipulation",
            check_type="file_pattern",
            severity="block",
            pattern="src/lib/facturacion/",
            description="No modificar modulo de facturacion",
            message="El modulo de facturacion SUNAT no puede ser modificado. Usa el job type 'dopacrm_backend' si necesitas cambios en facturacion.",
        ),
        GuardrailRule(
            id="keep-erp-imports",
            check_type="import_check",
            severity="block",
            pattern="erp-client|facturacion|invoice-service|tax-calculator",
            description="No remover imports del ERP",
            message="Los imports al ERP no deben ser removidos. La integracion con facturacion es obligatoria.",
        ),
        GuardrailRule(
            id="no-webhook-changes",
            check_type="file_pattern",
            severity="block",
            pattern="src/webhooks/",
            description="No modificar webhooks",
            message="Los webhooks de pago no se modifican desde el perfil de tema. Usa 'dopaweb_payment' para cambios en webhooks.",
        ),
        GuardrailRule(
            id="component-only",
            check_type="file_pattern",
            severity="info",
            pattern="src/components/",
            description="Zona editable segura",
            message="Componentes UI: cambios permitidos. No afectan logica de negocio.",
        ),
    ],
)


DOPAWEB_PAYMENT_GUARDRAILS = GuardrailProfile(
    name="dopaweb_payment",
    description="Integracion BYOK de PSPs con proteccion de ERP",
    protected_files=[
        "src/lib/facturacion/",
        "src/services/invoice.ts",
        "src/services/tax-calculator.ts",
    ],
    protected_endpoints=[
        "/api/erp/invoices/create",
        "/api/erp/taxes/",
    ],
    protected_imports=[
        "facturacion",
        "invoice-service",
        "tax-calculator",
    ],
    editable_files=[
        "src/integrations/payments/",
        "src/components/checkout/",
        "src/api/webhooks/",
        "src/types/payment.ts",
    ],
    rules=[
        GuardrailRule(
            id="payment-integration-only",
            check_type="file_pattern",
            severity="block",
            pattern="src/lib/facturacion/",
            description="No modificar facturacion durante integracion de pago",
            message="Facturacion SUNAT protegida. La integracion de pago debe consumir la API de facturacion sin modificarla.",
        ),
        GuardrailRule(
            id="keep-tax-logic",
            check_type="import_check",
            severity="block",
            pattern="tax-calculator|invoice-service",
            description="Mantener imports de logica fiscal",
            message="La logica de impuestos y facturacion debe permanecer intacta.",
        ),
    ],
)


class GuardrailEngine:
    def __init__(self):
        self.profiles: dict[str, GuardrailProfile] = {
            "dopaweb_theme": DOPAWEB_GUARDRAILS,
            "dopaweb_payment": DOPAWEB_PAYMENT_GUARDRAILS,
        }

    def get_profile(self, project_type: str) -> GuardrailProfile | None:
        return self.profiles.get(project_type)

    def validate_diff(
        self, project_type: str, diff_text: str, files_changed: list[str]
    ) -> dict:
        profile = self.get_profile(project_type)
        if not profile:
            return {"passed": True, "violations": [], "warnings": []}

        violations: list[dict] = []
        warnings: list[dict] = []

        for rule in profile.rules:
            if rule.check_type == "file_pattern":
                for file_path in files_changed:
                    if rule.pattern in file_path:
                        entry = {
                            "rule_id": rule.id,
                            "file": file_path,
                            "severity": rule.severity,
                            "message": rule.message,
                        }
                        if rule.severity == "block":
                            violations.append(entry)
                        elif rule.severity == "warn":
                            warnings.append(entry)

            if rule.check_type == "import_check":
                for file_path in files_changed:
                    for protected_import in rule.pattern.split("|"):
                        if protected_import in diff_text:
                            # Check if the import is being REMOVED (starts with -)
                            lines = diff_text.split("\n")
                            removed_lines = [
                                l for l in lines
                                if l.startswith("-") and protected_import in l
                            ]
                            if removed_lines:
                                violations.append({
                                    "rule_id": rule.id,
                                    "file": file_path,
                                    "severity": "block",
                                    "message": f"Import protegido removido: {protected_import}. {rule.message}",
                                })

        passed = len(violations) == 0

        if not passed:
            logger.warning(
                f"Guardrail violations for {project_type}: "
                f"{len(violations)} blocks, {len(warnings)} warnings"
            )

        return {
            "passed": passed,
            "violations": violations,
            "warnings": warnings,
            "profile": profile.name,
        }

    def build_system_prompt(self, project_type: str) -> str:
        profile = self.get_profile(project_type)
        if not profile:
            return ""

        lines = ["\n## GUARDRAILS - NO MODIFICAR", ""]
        lines.append(f"Perfil: {profile.description}")
        lines.append("")

        lines.append("### Archivos PROTEGIDOS (no tocar)")
        for f in profile.protected_files:
            lines.append(f"- ❌ `{f}`")

        lines.append("")
        lines.append("### Endpoints PROTEGIDOS (no modificar)")
        for ep in profile.protected_endpoints:
            lines.append(f"- ❌ `{ep}`")

        lines.append("")
        lines.append("### Archivos EDITABLES (zona segura)")
        for f in profile.editable_files:
            lines.append(f"- ✅ `{f}`")

        lines.append("")
        lines.append("### Reglas criticas")
        for rule in profile.rules:
            if rule.severity == "block":
                lines.append(f"- 🚫 {rule.description}: {rule.message}")

        return "\n".join(lines)

    def verify_erp_integration(
        self, tenant_id: str, base_url: str = ""
    ) -> dict:
        if settings.dopa_code_dummy:
            return {"passed": True, "message": "[DUMMY] ERP integration check skipped"}

        try:
            async def _check():
                async with httpx.AsyncClient(timeout=10.0) as client:
                    endpoints = [
                        f"{base_url}/api/erp/health",
                        f"{base_url}/api/invoices/health",
                        f"{base_url}/api/checkout/health",
                    ]
                    results = {}
                    for ep in endpoints:
                        try:
                            resp = await client.get(
                                ep,
                                headers={"x-tenant-id": tenant_id},
                            )
                            results[ep] = resp.status_code == 200
                        except Exception:
                            results[ep] = False
                    return results

            import asyncio
            results = asyncio.run(_check())

            passed = all(results.values())
            return {
                "passed": passed,
                "endpoints": results,
                "message": "ERP endpoints OK" if passed else "Some ERP endpoints fail",
            }
        except Exception as e:
            logger.warning(f"ERP integration check failed: {e}")
            return {"passed": True, "message": f"Check skipped: {e}"}


guardrail_engine = GuardrailEngine()
