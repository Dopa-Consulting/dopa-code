"""
Skills seeder para Dopa Code.

Skills adaptadas de:
- obra/superpowers (261k stars) — metodologia de desarrollo
- mattpocock/skills (187k stars) — patrones de TypeScript
- emilkowalski/skills (20k stars) — diseño y animaciones
- anthropics/skills (164k stars) — frontend-design y creatividad

Formato: name, description, steps_json, best_practices_json, tags_json
"""

import json
import logging

from sqlalchemy import select

from inti.database import async_session
from inti.models.skill_definition import SkillDefinition

logger = logging.getLogger("inti.skills_seeder")

# ===========================================================================
# SKILLS CATEGORIZADAS
# ===========================================================================

# --- General Development (adaptado de superpowers + mattpocock) ---

GENERAL_SKILLS = [
    {
        "name": "brainstorming",
        "description": "Refinar ideas antes de escribir codigo. Diseño socratico con preguntas y validacion",
        "steps_json": json.dumps([
            "Entender el problema real que se quiere resolver",
            "Explorar alternativas y trade-offs",
            "Presentar diseño en secciones cortas para validacion",
            "Guardar documento de diseño acordado",
        ]),
        "best_practices_json": json.dumps([
            "No saltar directo a codigo sin diseño aprobado",
            "Hacer preguntas que revelen requisitos ocultos",
            "Documentar decisiones de arquitectura",
            "Validar con el usuario antes de seguir",
        ]),
        "tags_json": json.dumps(["general", "planning", "design", "universal"]),
    },
    {
        "name": "test_driven_development",
        "description": "RED-GREEN-REFACTOR. Escribir tests primero, verlos fallar, escribir codigo minimo, verlos pasar",
        "steps_json": json.dumps([
            "RED: escribir test que falle",
            "Verificar que el test falla por la razon correcta",
            "GREEN: escribir el minimo codigo para que pase",
            "REFACTOR: mejorar el codigo sin romper tests",
            "Commit despues de cada ciclo",
        ]),
        "best_practices_json": json.dumps([
            "Nunca escribir codigo antes que el test",
            "Cada test prueba una sola cosa",
            "Eliminar codigo escrito antes de los tests",
            "Tests unitarios > tests de integracion > E2E",
        ]),
        "tags_json": json.dumps(["general", "testing", "tdd", "universal"]),
    },
    {
        "name": "systematic_debugging",
        "description": "Debugging estructurado en 4 fases: reproducir, aislar, root cause, fix + verify",
        "steps_json": json.dumps([
            "Reproducir el bug de forma confiable",
            "Aislar: reducir el scope hasta encontrar la causa",
            "Identificar root cause (no solo el sintoma)",
            "Fix con test que prevenga regresion",
            "Verify: confirmar que el fix funciona en todos los casos",
        ]),
        "best_practices_json": json.dumps([
            "Nunca arreglar sin entender la causa raiz",
            "Siempre agregar test de regresion",
            "Usar bisect para encontrar commits que introdujeron el bug",
            "Documentar el bug y la solucion para futuros agentes",
        ]),
        "tags_json": json.dumps(["general", "debugging", "qa", "universal"]),
    },
    {
        "name": "writing_plans",
        "description": "Crear planes de implementacion detallados con pasos de 2-5 min cada uno",
        "steps_json": json.dumps([
            "Descomponer el diseño en tareas atomicas",
            "Cada tarea: path exacto, codigo completo, pasos de verificacion",
            "Ordenar tareas por dependencias",
            "Estimar 2-5 minutos por tarea",
            "Validar que el plan cubre todo el diseño",
        ]),
        "best_practices_json": json.dumps([
            "Tareas demasiado grandes indican mal diseño",
            "Cada tarea debe ser independiente y testeable",
            "Incluir exactamente que archivos se modifican",
            "Plan debe ser ejecutable por un agente junior",
        ]),
        "tags_json": json.dumps(["general", "planning", "execution", "universal"]),
    },
    {
        "name": "requesting_code_review",
        "description": "Revision de codigo estructurada: spec compliance, code quality, security, tests",
        "steps_json": json.dumps([
            "Revisar contra el plan: todo lo planeado esta implementado?",
            "Code quality: naming, structure, DRY, complejidad",
            "Security: secrets, input validation, authz, SQL injection",
            "Tests: coverage, edge cases, regresiones",
            "Reportar issues por severidad (critical/high/medium/low)",
        ]),
        "best_practices_json": json.dumps([
            "Issues criticos bloquean el merge",
            "No hacer nitpicking - enfocarse en bugs y diseño",
            "Sugerir, no ordenar. El autor decide",
            "Revisar el diff completo, no solo las lineas cambiadas",
        ]),
        "tags_json": json.dumps(["general", "review", "qa", "universal"]),
    },
    {
        "name": "using_git_worktrees",
        "description": "Crear workspaces aislados con git worktree para desarrollo paralelo sin conflictos",
        "steps_json": json.dumps([
            "Crear worktree en rama nueva desde main/develop",
            "Ejecutar setup del proyecto en el worktree",
            "Verificar baseline de tests en limpio",
            "Desarrollar cambios en el worktree aislado",
            "Al terminar: merge/PR/descartar y limpiar worktree",
        ]),
        "best_practices_json": json.dumps([
            "Un worktree por feature",
            "Nunca trabajar en main directamente",
            "Limpiar worktrees viejos",
            "Cada worktree tiene su propio node_modules",
        ]),
        "tags_json": json.dumps(["general", "git", "workspace", "universal"]),
    },
    {
        "name": "subagent_driven_development",
        "description": "Despachar subagentes frescos por tarea con revision en dos etapas (spec + code quality)",
        "steps_json": json.dumps([
            "Por cada tarea del plan: despachar subagente nuevo (contexto limpio)",
            "Stage 1 review: cumple la spec? Si no, re-despachar",
            "Stage 2 review: code quality, tests, patrones",
            "Integrar cambios al branch principal",
            "Avanzar a la siguiente tarea",
        ]),
        "best_practices_json": json.dumps([
            "Subagente fresco = sin sesgo de tareas anteriores",
            "Revision en 2 etapas atrapa mas errores",
            "No despachar multiples subagentes sobre el mismo archivo",
            "Cada subagente usa el modelo mas barato que funcione",
        ]),
        "tags_json": json.dumps(["general", "execution", "parallel", "universal"]),
    },
]

# --- DopaWeb / Design (adaptado de emilkowalski + anthropics) ---

DOPAWEB_DESIGN_SKILLS = [
    {
        "name": "frontend_design_principles",
        "description": "Principios de diseño para interfaces web: jerarquia visual, espaciado, tipografia, color",
        "steps_json": json.dumps([
            "Analizar la jerarquia visual actual de la pagina",
            "Verificar consistencia de espaciado (grid de 4px/8px)",
            "Revisar tipografia: max 2 familias, scale consistente",
            "Paleta de colores: primario, secundario, accent, neutral, semanticos",
            "Asegurar contraste WCAG AA minimo",
            "Responsive: mobile-first, breakpoints consistentes",
        ]),
        "best_practices_json": json.dumps([
            "Menos es mas: eliminar antes de agregar",
            "Espaciado generoso > comprimido",
            "Sombras semi-transparentes en vez de bordes solidos",
            "Animaciones sutiles: ease-out para entrada, ease-in para salida",
            "No usar mas de 2 typefaces",
        ]),
        "tags_json": json.dumps(["dopaweb", "design", "ui", "frontend"]),
    },
    {
        "name": "animation_best_practices",
        "description": "Animaciones correctas: easing, duracion, proposito. Basado en emilkowalski/skills",
        "steps_json": json.dumps([
            "Identificar elementos que se beneficiarian de animacion",
            "Elegir easing correcto: ease-out para entrada, ease-in para salida",
            "Duracion: 150-300ms para micro-interacciones, 300-500ms para transiciones",
            "No animar elementos que distraigan del contenido principal",
            "Respetar prefers-reduced-motion",
        ]),
        "best_practices_json": json.dumps([
            "Ease-out para elementos que aparecen",
            "Ease-in para elementos que desaparecen",
            "Nunca usar ease-in para entradas (se siente lento)",
            "Transform y opacity son las propiedades mas performantes",
            "No animar width/height (causa reflow)",
        ]),
        "tags_json": json.dumps(["dopaweb", "design", "animation", "ui"]),
    },
    {
        "name": "brand_guidelines_integration",
        "description": "Aplicar guia de marca consistente en todos los componentes",
        "steps_json": json.dumps([
            "Cargar paleta de colores de la marca",
            "Configurar variables CSS/tailwind con los tokens de diseño",
            "Aplicar tipografia corporativa",
            "Reemplazar logo y assets de marca",
            "Verificar consistencia en todas las paginas",
        ]),
        "best_practices_json": json.dumps([
            "Usar design tokens (no hardcodear colores)",
            "Mantener consistencia con el ERP",
            "Probar en light y dark mode",
            "Documentar decisiones de diseño",
        ]),
        "tags_json": json.dumps(["dopaweb", "design", "branding", "theme"]),
    },
    {
        "name": "canvas_design_generation",
        "description": "Generar diseños visuales con HTML/CSS para banners, hero sections, y landing pages",
        "steps_json": json.dumps([
            "Definir el proposito y audiencia del diseño",
            "Crear layout con HTML semantico",
            "Estilizar con CSS/Tailwind siguiendo la guia de marca",
            "Optimizar para mobile y desktop",
            "Exportar como componente reutilizable",
        ]),
        "best_practices_json": json.dumps([
            "Diseños responsivos desde el inicio",
            "Usar gradientes y sombras con moderacion",
            "Tipografia grande y legible en hero sections",
            "CTA visible y accionable",
        ]),
        "tags_json": json.dumps(["dopaweb", "design", "canvas", "landing"]),
    },
]

# --- Dopa-specific (nuestro) ---

DOPA_CUSTOM_SKILLS = [
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
        "name": "dopa_backend_safe_refactor",
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
        "tags_json": json.dumps(["dopa", "backend", "refactor", "restricted"]),
    },
]

# --- Meta (skill creation) ---

META_SKILLS = [
    {
        "name": "writing_skills",
        "description": "Crear nuevas skills siguiendo el formato de Dopa Code",
        "steps_json": json.dumps([
            "Identificar el proposito de la skill (que problema resuelve)",
            "Definir pasos concretos y verificables",
            "Agregar mejores practicas basadas en experiencia",
            "Categorizar con tags adecuados (dopaweb, general, design, etc.)",
            "Testear la skill con un job de prueba",
        ]),
        "best_practices_json": json.dumps([
            "Pasos atomicos y ejecutables (2-5 min cada uno)",
            "Best practices basadas en experiencia real, no teoria",
            "Tags semantico: project_type + domain + safety_level",
            "Cada skill debe ser autocontenida",
        ]),
        "tags_json": json.dumps(["meta", "skills", "universal"]),
    },
    {
        "name": "using_dopa_skills",
        "description": "Guia de uso del sistema de skills de Dopa Code. El agente debe consultar skills relevantes antes de cada tarea",
        "steps_json": json.dumps([
            "Al recibir una tarea, buscar skills relevantes por tags",
            "Cargar steps + best_practices de las skills encontradas",
            "Seguir los pasos definidos en orden",
            "Reportar si alguna best practice no se pudo aplicar",
            "Al completar, sugerir mejoras a la skill si corresponde",
        ]),
        "best_practices_json": json.dumps([
            "Skills son obligatorias, no sugerencias",
            "Si una skill no aplica bien, sugerir mejora via writing_skills",
            "Usar subagent_driven_development para tareas complejas",
            "Consultar skills antes de empezar, no durante",
        ]),
        "tags_json": json.dumps(["meta", "skills", "universal"]),
    },
]

ALL_SKILLS = GENERAL_SKILLS + DOPAWEB_DESIGN_SKILLS + DOPA_CUSTOM_SKILLS + META_SKILLS


async def seed_all_skills() -> dict:
    seeded = 0
    updated = 0

    async with async_session() as session:
        for skill_data in ALL_SKILLS:
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
                updated += 1
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

    logger.info(f"Skills: {seeded} new, {updated} updated, {len(ALL_SKILLS)} total")
    return {"new": seeded, "updated": updated, "total": len(ALL_SKILLS)}
