import logging

import httpx

from inti.config import settings

logger = logging.getLogger("inti.erp")


class ErpContext:
    def __init__(self, base_url: str = ""):
        self.base_url = base_url or "http://localhost:3002/api"

    async def get_erp_schemas(self, tenant_id: str) -> dict:
        if settings.dopa_code_dummy:
            return self._dummy_schemas()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/schemas",
                    headers={"x-tenant-id": tenant_id},
                )
                if resp.status_code == 200:
                    return resp.json()
                return self._dummy_schemas()
        except httpx.ConnectError:
            return self._dummy_schemas()

    async def get_business_rules(self, tenant_id: str, country: str = "PE") -> dict:
        if settings.dopa_code_dummy:
            return self._dummy_rules(country)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/business-rules",
                    headers={"x-tenant-id": tenant_id},
                    params={"country": country},
                )
                if resp.status_code == 200:
                    return resp.json()
                return self._dummy_rules(country)
        except httpx.ConnectError:
            return self._dummy_rules(country)

    async def build_prompt_context(self, tenant_id: str) -> str:
        schemas = await self.get_erp_schemas(tenant_id)
        rules = await self.get_business_rules(tenant_id)

        lines = ["## Dopa ERP Context (read-only)\n"]

        if schemas.get("entities"):
            lines.append("### Entidades principales")
            for entity in schemas["entities"]:
                lines.append(f"- **{entity['name']}**: {entity.get('description', '')}")

        if rules.get("tax_rules"):
            lines.append("\n### Reglas fiscales")
            for rule in rules["tax_rules"]:
                lines.append(f"- {rule}")

        if rules.get("invoice_states"):
            lines.append("\n### Estados de factura")
            for state in rules["invoice_states"]:
                lines.append(f"- `{state}`")

        lines.append("\n### Advertencias")
        lines.append("- NO modificar endpoints del ERP core")
        lines.append("- NO alterar la logica de facturacion SUNAT")
        lines.append("- Mantener compatibilidad con los webhooks existentes")
        lines.append("- Respetar el modelo multi-tenant (tenant_id en todas las queries)")

        return "\n".join(lines)

    def _dummy_schemas(self) -> dict:
        return {
            "entities": [
                {"name": "Invoice", "description": "Factura electronica (SUNAT)"},
                {"name": "Product", "description": "Catalogo de productos"},
                {"name": "Customer", "description": "Cliente con datos fiscales"},
                {"name": "Order", "description": "Pedido vinculado a factura"},
                {"name": "Payment", "description": "Pago registrado contra factura"},
            ]
        }

    def _dummy_rules(self, country: str = "PE") -> dict:
        return {
            "country": country,
            "tax_rules": [
                f"IGV 18% para {country}",
                "Retencion aplicable segun regimen",
            ],
            "invoice_states": [
                "pending",
                "paid",
                "refunded",
                "cancelled",
                "failed",
            ],
        }


erp_context = ErpContext()
