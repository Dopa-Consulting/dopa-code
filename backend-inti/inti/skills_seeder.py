import json
import logging

from sqlalchemy import select

from inti.database import async_session
from inti.models.skill_definition import SkillDefinition

logger = logging.getLogger("inti.skills_seeder")

DOPAWEB_SKILLS = [
    {
        "name": "customize_product_page",
        "description": "Modificar layout de pagina de producto sin tocar checkout ni ERP",
        "steps_json": json.dumps([
            "Analizar el template actual de producto",
            "Identificar zonas editables (componentes, estilos)",
            "Aplicar cambios solo en src/components/product/ y src/styles/",
            "Verificar que useCheckout y ERP siguen intactos",
            "Test visual y funcional",
        ]),
        "best_practices_json": json.dumps([
            "Nunca modificar src/hooks/useCheckout.ts",
            "No tocar imports de erp-client, facturacion, o tax-calculator",
            "Los datos del producto vienen del ERP via API, no modificar el fetch",
            "Probar en mobile y desktop",
        ]),
        "tags_json": json.dumps(["dopaweb", "theme", "product", "safe"]),
    },
    {
        "name": "customize_checkout_ui",
        "description": "Ajustar estilos del checkout sin romper flujo de pago",
        "steps_json": json.dumps([
            "Identificar componentes visuales del checkout",
            "Modificar solo CSS/styling, nunca la logica de flujo",
            "Verificar que useCheckout.ts no fue modificado",
            "Probar flujo completo en sandbox",
        ]),
        "best_practices_json": json.dumps([
            "Solo CSS y layout. Cero logica de negocio",
            "El checkout se integra con ERP via webhooks, no tocar",
            "Probar con metodo de pago de prueba antes de deploy",
        ]),
        "tags_json": json.dumps(["dopaweb", "checkout", "theme", "restricted"]),
    },
    {
        "name": "add_payment_method_byok",
        "description": "Integrar un PSP externo (Stripe, MercadoPago, etc.) via BYOK",
        "steps_json": json.dumps([
            "Crear modulo en src/integrations/payments/ con el nuevo PSP",
            "Implementar checkout UI especifico del PSP en src/components/checkout/",
            "Configurar webhook en src/api/webhooks/",
            "Mapear estados de pago del PSP a estados de factura ERP",
            "Test en sandbox del PSP antes de produccion",
            "Ejecutar QA y CI antes de deploy",
        ]),
        "best_practices_json": json.dumps([
            "Credenciales via variables de entorno, nunca en codigo",
            "Webhook con verificacion de firma del PSP",
            "Mapping de estados: pending→pending, paid→paid, refunded→refunded",
            "Facturacion SUNAT se consume via API, no se modifica",
            "Modo sandbox primero, produccion solo despues de QA y aprobacion humana",
        ]),
        "tags_json": json.dumps(["dopaweb", "payment", "byok", "restricted"]),
    },
    {
        "name": "customize_branding",
        "description": "Cambiar colores, tipografia, logo y assets de marca",
        "steps_json": json.dumps([
            "Modificar variables CSS/tailwind en src/styles/",
            "Reemplazar logo en public/",
            "Ajustar componentes de layout para reflejar branding",
            "Verificar contraste y accesibilidad",
        ]),
        "best_practices_json": json.dumps([
            "Solo cambios visuales. Cero logica",
            "Mantener estructura de componentes intacta",
            "Probar en todos los breakpoints",
        ]),
        "tags_json": json.dumps(["dopaweb", "theme", "branding", "safe"]),
    },
    {
        "name": "add_custom_section",
        "description": "Agregar una nueva seccion a la pagina (hero, features, testimonials)",
        "steps_json": json.dumps([
            "Crear componente en src/components/",
            "Integrar en el layout deseado",
            "Conectar con datos del ERP si es necesario (productos, categorias)",
            "Test visual y responsive",
        ]),
        "best_practices_json": json.dumps([
            "Componentes autocontenidos, no acoplados a logica de negocio",
            "Usar datos del ERP via hooks existentes, no crear nuevos endpoints",
            "Probar que el resto de la pagina sigue funcionando",
        ]),
        "tags_json": json.dumps(["dopaweb", "theme", "section", "safe"]),
    },
    {
        "name": "dopacrm_backend_safe_refactor",
        "description": "Refactorizar codigo del backend ERP sin romper APIs existentes",
        "steps_json": json.dumps([
            "Identificar el alcance del refactor",
            "Ejecutar suite de tests actual como baseline",
            "Aplicar cambios incrementales",
            "Correr tests despues de cada cambio",
            "QA agente revisa diffs",
            "CI debe pasar antes de merge",
        ]),
        "best_practices_json": json.dumps([
            "Nunca cambiar firmas de API publicas sin migracion",
            "Migraciones de DB siempre con rollback",
            "Facturacion SUNAT es intocable sin doble aprobacion",
            "Correr tests E2E antes de PR",
        ]),
        "tags_json": json.dumps(["dopacrm", "backend", "refactor", "restricted"]),
    },
]


async def seed_dopaweb_skills() -> int:
    seeded = 0
    async with async_session() as session:
        for skill_data in DOPAWEB_SKILLS:
            result = await session.execute(
                select(SkillDefinition).where(
                    SkillDefinition.name == skill_data["name"]
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.description = skill_data["description"]
                existing.steps_json = skill_data["steps_json"]
                existing.best_practices_json = skill_data["best_practices_json"]
                existing.tags_json = skill_data["tags_json"]
            else:
                skill = SkillDefinition(
                    name=skill_data["name"],
                    description=skill_data["description"],
                    steps_json=skill_data["steps_json"],
                    best_practices_json=skill_data["best_practices_json"],
                    tags_json=skill_data["tags_json"],
                    success_rate=0.5,
                    total_executions=0,
                )
                session.add(skill)

            seeded += 1

        await session.commit()

    logger.info(f"Seeded {seeded} DopaWeb skills")
    return seeded
