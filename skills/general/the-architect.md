# the_architect

Meta-agente que diseña blueprints completos de software. Describe que queres construir y te hace preguntas inteligentes, diseña todo el sistema, y genera un blueprint que Inti puede ejecutar autonomamente.

**Origen**: [Hainrixz/the-architect](https://github.com/Hainrixz/the-architect) (MIT, 371 stars)
**Tags**: general, planning, design, architecture, universal

## El concepto

```
Humano: "Quiero un SaaS de reservas para restaurantes"
         ↓
The Architect: hace preguntas, diseña todo
         ↓
Blueprint.md: plan completo con 16 secciones
         ↓
Inti + OpenCode: lee el blueprint → construye la app
```

## 4 Fases

### Fase 1: Discovery (Descubrimiento)

El agente hace 2-3 preguntas para entender la idea:
- Que estas construyendo?
- Para quien es?
- Que tan grande debe ser?

Clasifica el proyecto en uno de 6 arquetipos:
1. **SaaS / Web App**: apps multi-tenant con auth, pagos, dashboards
2. **Marketing Site**: landing pages, portafolios, sitios estaticos
3. **Mobile App**: apps iOS/Android
4. **API / Backend**: REST APIs, microservicios
5. **Internal Tool**: paneles admin, dashboards internos
6. **Content Platform**: blogs, docs, CMS

### Fase 2: Deep Dive (Profundizacion)

Preguntas especificas segun el tipo de proyecto:
- Necesitas cuentas de usuario? Que roles?
- Pagos? Que PSP? (Stripe, MercadoPago, etc.)
- Funciones en tiempo real? WebSockets?
- Base de datos? SQL o NoSQL?
- Autenticacion? OAuth, magic link, passkeys?
- Multi-tenant? BYOK?

Investiga mejores practicas usando memoria de proyecto y skills relevantes.

### Fase 3: Architecture (Arquitectura)

Presenta el tech stack completo con razones para cada decision:
- Framework frontend + libreria de componentes
- Backend + ORM + base de datos
- Auth provider
- Payment provider
- Hosting + CI/CD
- Sistema de diseño (colores, fuentes, espaciado)

Si el proyecto es DopaWeb, usa el stack Dopa por defecto y sugiere personalizaciones.

El humano confirma o ajusta.

### Fase 4: Generate Blueprint

Genera un archivo `.md` con 16 secciones:

## Las 16 secciones del Blueprint

| # | Seccion | Contenido |
|---|---------|-----------|
| 1 | Project Overview | Vision, objetivos, metricas |
| 2 | Tech Stack | Cada tecnologia con justificacion |
| 3 | Directory Structure | Arbol de archivos completo |
| 4 | Data Model | Entidades, campos, relaciones, SQL |
| 5 | API Design | Rutas, endpoints, request/response |
| 6 | Frontend Architecture | Paginas, componentes, estado |
| 7 | Design System | Colores, fuentes, espaciado |
| 8 | Auth & Authorization | Login, roles, permisos |
| 9 | **Build Order** | Paso a paso: que construir primero |
| 10 | Environment Setup | Prerequisitos, env vars, comandos |
| 11 | Dependencies | Cada paquete con su proposito |
| 12 | Deployment | Hosting, CI/CD, dominios |
| 13 | Testing | Que testear, herramientas, cuando |
| 14 | Skills to Use | Skills de Dopa Code que ayudan |
| 15 | **AGENTS.md** | Instrucciones completas para el builder |
| 16 | Rules | Restricciones no negociables |

**La seccion 9 (Build Order) es la mas importante.** Define exactamente que construir y en que orden.

## Discovery Mode

Cuando Inti entra en modo discovery:
1. No ejecuta codigo - solo pregunta, investiga, y diseña
2. Cada respuesta del humano refina el diseño
3. El agente investiga en background (memoria de proyecto, skills, guardrails)
4. Al finalizar, genera el blueprint y lo guarda como `docs/blueprints/<project>-blueprint.md`

## Best Practices

### Preguntas inteligentes

- No mas de 2-3 preguntas por turno
- Preguntas abiertas que revelen requisitos ocultos
- Nunca asumir - siempre confirmar
- Si el proyecto es DopaWeb: preguntar sobre integracion ERP, metodos de pago, facturacion

### Diseño de arquitectura

- Stack por defecto basado en el arquetipo
- Justificar cada decision (no "porque es popular")
- Considerar trade-offs: simplicidad vs escalabilidad
- Si el proyecto ya existe en Dopa, respetar el stack actual

### Blueprint de calidad

- Lo suficientemente detallado para que un agente junior lo ejecute
- Build order priorizado: fundamentos → features → polish
- Cada paso debe ser independiente y testeable
- Incluir comandos exactos (no "instalar dependencias" sino `npm install react react-dom`)

### Herencia de Dopa Code

Si el proyecto usa el ecosistema Dopa:
- Stack: Next.js + React + Tailwind (frontend), Express + Sequelize + PG (backend)
- Auth: JWT + WebAuthn via Dopa
- Pagos: MercadoPago nativo + BYOK para otros PSPs
- Deploy: Easypanel via Dopa Code
- Guardrails: heredados del project_type
