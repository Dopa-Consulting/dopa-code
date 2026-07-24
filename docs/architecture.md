# Arquitectura de Dopa Code

## Vision

Dopa Code es un entorno de desarrollo agentico **Local-First** que permite orquestar la escritura, revision y despliegue de codigo desde una PWA movil, sin depender de IDEs en la nube.

Inti, el agente andino, actua como el "sol" del sistema -- el centro desde el que se orquesta todo el flujo de desarrollo agentico.

---

## Diagrama de Componentes

```
[ PWA Movil ] (React + Tailwind + Dexie)
     |
     | Tailscale VPN + MagicDNS (HTTPS)
     | WebSocket (eventos en tiempo real) + REST (operaciones)
     |
[ PC Windows ] (Daemon Inti - FastAPI + SQLite)
     |
     ├── FSM Inti (Planificador → Ejecutor → QA → Aprobacion Humana)
     |
     ├── AgentRuntime (Python) ──subprocess──> [ OpenCode CLI ] (Node.js)
     |       │                                       │
     |       │ DOPA_CODE_DUMMY=1 → modo seguro       │ Modifica archivos
     |       │ simula cambios sin tocar el repo       │ en rama aislada
     |
     ├── policies.py → perfiles de tarea + roles de modelo
     |
     ├── events.py → tipos JSON para WebSocket
     |
     └── audit.py → audit_log forense
           │
           ▼
[ Conexiones Externas ]
     ├── OpenRouter (BYOK) → Claude Opus 4.8 / Sonnet 5, DeepSeek V4
     ├── Antigravity (API) → QA gratis (plan profesor)
     ├── GitHub (PRs, CI) → via n8n o directo
     └── Easypanel (Deploy) → via n8n
```

---

## Modulos del Backend (Inti)

### 1. agent_runtime.py -- Capa Inti ↔ OpenCode

Clase `AgentRuntime` que encapsula toda interaccion con el CLI de OpenCode.

**Metodos de alto nivel:**
- `plan_change(job, prompt)` -- Llama al architect_llm para generar un plan
- `apply_change(job, plan)` -- Ejecuta cambios via executor_llm + OpenCode
- `generate_diff(job)` -- Extrae el diff del workspace
- `run_tests(job)` -- Corre tests sobre los cambios

**Dummy Mode** (`DOPA_CODE_DUMMY=1`):
- No toca archivos reales
- No hace commits
- Genera diffs simulados en memoria
- Permite probar FSM, PWA y sincronizacion sin riesgo

### 2. policies.py -- Perfiles y permisos

Define perfiles de tarea con niveles de autonomia del LLM Architect.

**Roles de modelo configurables:**

| Rol | Opciones | Proveedor |
|-----|----------|-----------|
| architect_llm | Opus 4.8, Sonnet 5 | OpenRouter |
| executor_llm | DeepSeek V4 | OpenRouter |
| qa_llm | Antigravity | API directa |

**Perfiles de tarea:**

| Perfil | Architect | Executor | QA | Autonomia PR |
|--------|-----------|----------|-----|--------------|
| pro_mix | Opus/Sonnet | DeepSeek | Antigravity | human_gatekeeper |
| budget | DeepSeek | DeepSeek | DeepSeek | human_gatekeeper |
| premium | Opus/Sonnet | Opus/Sonnet | Opus/Sonnet | human_gatekeeper |

**Niveles de autonomia del Architect:**
- `human_gatekeeper` -- Todo requiere aprobacion humana
- `plan_and_pr_only` -- Abre PR automaticamente, merge requiere humano
- `auto_merge_staging` -- Merge automatico en staging si CI verde + confidence_high
- `full_auto` -- Solo para docs/refactors triviales (futuro)

### 3. events.py -- Tipos de eventos WebSocket

Define el formato JSON estandar para todos los eventos que Inti emite a la PWA:

| Evento | Descripcion |
|--------|-------------|
| `JobStateChanged` | El job cambio de estado en la FSM |
| `DiffReadyForApproval` | Hay un diff nuevo listo para revision |
| `TestsFinished` | Los tests terminaron (pass/fail) |
| `CiStatusUpdated` | Estado de CI cambio |
| `DeployTriggered` | Deploy iniciado |
| `DeployCompleted` | Deploy finalizado |
| `ArchitectPlanGenerated` | El plan del LLM Architect esta listo |

**Formato estandar:**
```json
{
  "event_type": "JobStateChanged",
  "job_id": "uuid",
  "timestamp": "ISO8601",
  "version": 1,
  "payload": {
    "previous_status": "executing",
    "new_status": "qa_pending"
  }
}
```

### 4. audit.py -- Auditoria forense

Tabla `audit_log` separada de `events`. Registra toda accion relevante con trazabilidad completa:

| Campo | Descripcion |
|-------|-------------|
| actor_type | llm_architect, llm_executor, llm_qa, human, system |
| actor_id | Identificador del actor |
| device_id | Dispositivo desde el que se hizo la accion |
| action | created_job, executed_plan, approved_diff, merged_pr, deployed |
| job_id | Job asociado |
| signature | Firma WebAuthn (si fue accion humana) |
| metadata | JSON con contexto adicional |

### 5. models/ -- Modelos SQLAlchemy

| Modelo | Tabla | Descripcion |
|--------|-------|-------------|
| Job | jobs | Tarea/pipeline de Inti. + columna `profile` |
| JobStep | job_steps | Pasos del FSM (planner, executor, qa, deploy) |
| Diff | diffs | Diffs generados por el ejecutor |
| Approval | approvals | Aprobaciones (QA agente, humano, auto) |
| AuditLog | audit_log | Registro forense de acciones |
| Event | events | Eventos de streaming para la PWA |
| CiRun | ci_runs | Estado de CI por job |
| Device | devices | Dispositivos vinculados |

### 6. config.py -- Settings

Configuracion via `pydantic-settings` con prefijo `DOPA_`:

- `DOPA_DATABASE_URL` -- SQLite por defecto
- `DOPA_CODE_DUMMY` -- Flag para modo dummy
- `DOPA_OPENROUTER_API_KEY` -- API key BYOK
- `DOPA_ANTIGRAVITY_API_KEY` -- API key QA
- `DOPA_JWT_SECRET` -- Firma de tokens

---

## Flujo de la FSM (Inti)

```
[ Brief del usuario ]
         │
         ▼
[ Planificador ] ── architect_llm (Opus/Sonnet)
         │
         ▼ Plan estructurado
[ Ejecutor ] ── executor_llm (DeepSeek) + OpenCode CLI
         │
         ▼ Rama aislada con cambios
[ QA Agente ] ── qa_llm (Antigravity)
         │
    ┌────┴────┐
    │  Pasa?  │
    └────┬────┘
     No  │  Si
     │   ▼
     └─→[ Ejecutor ] (loop de correccion)
         │
         ▼
[ Aprobacion Humana ] ── PWA movil (WebAuthn)
         │
    ┌────┴────┐
    │ Aprueba?│
    └────┬────┘
     No  │  Si
     │   ▼
     └─→[ Cancelado ]
         │
         ▼
[ CI/CD ] ── GitHub Actions → n8n → Easypanel
         │
         ▼
[ Desplegado ]
```

---

## Base de Datos

### Tablas principales

```
users ──< devices ──< sessions
  │
  └──< jobs ──< job_steps
         │
         ├──< diffs ──< approvals
         ├──< events
         ├──< audit_log
         └──< ci_runs
```

### IndexedDB (PWA)

| Store | Sync |
|-------|------|
| jobs | Copia parcial del backend |
| diffs | Vinculados a jobs visibles |
| pendingActions | Cola offline-first |
| events | Ultimos N eventos |

---

## Seguridad

- **Tailscale VPN + MagicDNS**: HTTPS en red privada
- **WebAuthn**: Firmas biometricas para aprobaciones criticas
- **QR Handshake**: JWT de un solo uso para vincular dispositivos
- **Workspace Jail**: Usuario Windows no-admin, allowlist de comandos
- **psutil**: Timeout y limites de RAM para procesos del agente
- **DOPA_CODE_DUMMY**: Modo seguro para desarrollo

---

## Integracion con el Ecosistema Dopa

### Proyectos del ecosistema

| Proyecto | Stack | Rol |
|----------|-------|-----|
| **Dopa** | Node.js 24 + Express + Sequelize + PostgreSQL | ERP agentico multi-tenant: facturacion SUNAT, POS, inventario, inbox omnicanal, AI agents, BYOK |
| **Dopa Frontend** | Vite + React 19 + MUI + ElevenLabs | Dashboard PWA: chat, inbox, POS, billing |
| **DopaWeb** | Next.js + React | Plataforma ecommerce multi-tenant integrada con Dopa |
| **Dopa Academy** | Web | Capacitacion y formacion en el ecosistema |
| **Dopa Code** | FastAPI + React + Node bridge + OpenCode | Constructor agentico nativo del ecosistema |

### Dopa Code como constructor agentico de DopaWeb

En lugar de un builder visual tipo Elementor, Dopa Code es el "constructor invisible" de DopaWeb:

```
[ Cliente DopaWeb ]
    │
    │ Crea tienda + elige template funcional
    │ Templates integrados con Dopa ERP (catalogo, checkout, facturacion)
    │
    ▼
[ Dopa Code / Inti ] ──── PWA movil
    │
    │ "Cambiar layout de pagina de producto"
    │ "Agregar metodo de pago BYOK (Stripe, MercadoPago)"
    │ "Ajustar branding segun guia de marca"
    │
    ▼
[ Pipeline agentico ]
    Planner → Executor (OpenCode) → QA → CI → Aprobacion humana → Deploy
    │
    │ Opera sobre el repositorio del tema de la tienda
    │ Branch aislada por job
    │
    ▼
[ Dopa / ERP ]
    │ APIs de productos, categorias, facturacion
    │ Integraciones de pago via BYOK
    │ Webhooks de CI/CD → n8n → Easypanel
```

### BYOK Payment Integration

Dopa Code permite integrar metodos de pago externos (Stripe, PayPal, MercadoPago, Culqi, etc.) sin plugins:

1. El cliente registra sus credenciales del PSP en DopaWeb
2. Inti crea un job `integrate_psp` con contexto del tenant
3. Architect LLM evalua docs del PSP y genera plan de integracion
4. Executor implementa: checkout, webhooks, mapping a Dopa ERP
5. QA verifica flujos en sandbox del PSP
6. CI ejecuta tests de integracion
7. Aprobacion y deploy desde la PWA

### Project Types en policies.py

Cada job se asigna a un tipo de proyecto del ecosistema:

| project_type | Descripcion | Autonomia default |
|-------------|-------------|-------------------|
| `dopa_backend` | Modificaciones al ERP core | human_gatekeeper |
| `dopa_frontend` | Dashboard y UI del ERP | plan_and_pr_only |
| `dopaweb_theme` | Personalizacion de templates ecommerce | auto_merge_staging |
| `dopaweb_payment` | Integracion BYOK de PSPs | human_gatekeeper |
| `dopa_code` | Desarrollo del propio Dopa Code | human_gatekeeper |

---

## Roadmap

| Fase | Estado |
|------|--------|
| 1. Inicializacion del Workspace | Completed |
| 2. Arquitectura core (modelos, AgentRuntime, politicas, eventos, auditoria, memoria) | Completed |
| 3. Integracion OpenCode CLI via bridge HTTP | Completed |
| 4. PWA offline-first + WebSockets + Visor de Diffs/PRs | Pending |
| 5. Seguridad (Tailscale, WebAuthn) + CI/CD (n8n + Easypanel) | Pending |
| 6. Integracion DopaWeb (templates, BYOK payments, agentes por tenant) | Pending |
| 7. Empaquetado final (PyInstaller + Windows Service) | Pending |
