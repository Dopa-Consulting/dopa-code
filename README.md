# Dopa Code

Entorno de desarrollo agentico **Local-First** para cualquier proyecto de software. Inti, el agente andino, orquesta la escritura, revision y despliegue de codigo desde tu PC, controlado desde tu movil via PWA.

Usalo con tu stack actual -- React, Next.js, Python, Node, lo que sea. Inti + OpenCode trabajan sobre tu repo local, en ramas aisladas, sin depender de SaaS externos. Tu codigo, tu PC, tus reglas.

## Ecosistema Dopa

Dopa Code es parte del ecosistema Dopa pero funciona con cualquier proyecto:

| Proyecto | Stack | Rol |
|----------|-------|-----|
| **DopaCRM** | Node.js 24 + Express + Sequelize + PostgreSQL | ERP multi-tenant: facturacion SUNAT, POS, inventario, inbox, AI agents |
| **DopaWeb** | Next.js + React | Ecommerce multi-tenant integrado nativamente con DopaCRM |
| **Dopacrm-landing** | Next.js 16 + GSAP + Stripe + Cloudflare | Landing page |
| **Dopa Code** | FastAPI + React + Node bridge + OpenCode | Orquestador agentico general |

**Integracion nativa con DopaWeb**: templates funcionales + BYOK payments + ERP context. Pero tambien funciona con tu proyecto personal, tu startup, o cualquier repo Git.

## Arquitectura

```
dopa-code/
├── backend-inti/     # Daemon FastAPI (Python) - FSM Inti, 14 tablas SQLite, 26 endpoints
├── frontend-pwa/     # PWA movil (React/Vite + Tailwind + Dexie + Service Worker)
├── agent-runtime/    # Bridge HTTP + OpenCode CLI + git submodule opencode/
└── docs/             # Arquitectura, FSM, historial de jobs auto-generado
```

```
[ PWA Movil ] <──Tailscale VPN──> [ PC Windows: Inti Daemon + Bridge + OpenCode CLI ]
                                        │
                                   [ n8n VPS ] (CI/CD, Webhooks)
                                   [ OpenRouter ] (Opus 4.8, Sonnet 5, DeepSeek, BYOK)
                                   [ Antigravity ] (QA via API)
                                   [ Easypanel ] (Deploy via token)
```

## Flujo agentico

```
Usuario: "Agregar endpoint de metricas"
Usuario: "Refactorizar modulo de pagos"
Usuario: "Actualizar dependencias y correr tests"
    │
    ▼
Inti → Plan (Architect LLM: Opus 4.8 o Sonnet 5)
    → Execute (Executor LLM: DeepSeek + OpenCode CLI)
    → QA (Antigravity o modelo configurado)
    → CI (GitHub Actions)
    → PWA (approve/reject con WebAuthn)
    → Deploy (Easypanel)
```

Cada job aprende: PostMortem genera lecciones, refina skills, y construye memoria de proyecto.

## Capacidades

| Modulo | Funcion |
|--------|---------|
| `agent_runtime` | Capa Inti ↔ OpenCode. Dummy mode para desarrollo seguro |
| `policies` | 3 perfiles de modelo + 6 tipos de proyecto + 4 niveles de autonomia |
| `events` | 10 tipos de eventos JSON para WebSocket en tiempo real |
| `audit` | Auditoria forense: quien hizo que, dispositivo, firma |
| `memory` | Memoria estilo Hermes: PostMortem, SkillRefiner, MemoryContext |
| `deploy` | Deploy via token Easypanel, CI webhooks, auto-merge |
| `templates` | Bridge de repos de templates multi-tenant |
| `payments` | BYOK payment integration con contexto ERP |
| `erp_context` | Inyeccion de schemas y reglas de negocio en prompts |

## Requisitos

- **Python** 3.11+
- **Node.js** 20+
- **Bun** 1.3+ (para el bridge)
- **OpenCode CLI** (global, via npm)
- **Git**

## Instalacion

### Produccion (Windows)

```powershell
# Como Administrador
Set-ExecutionPolicy Bypass -Scope Process
.\install.ps1

# Abre http://localhost:8000 en tu navegador
```

El instalador configura servicio Windows (auto-start), crea carpeta de workspaces, y genera `.env` para tus API keys.

### Desarrollo

```powershell
# Backend
cd backend-inti
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Bridge (otra terminal)
cd agent-runtime
bun bridge.js

# Frontend (otra terminal)
cd frontend-pwa
npm run dev
```

### Endpoints (26 total)

| Grupo | Endpoints |
|-------|-----------|
| `GET /health` | Estado del daemon |
| `/api/v1/jobs/*` | CRUD de jobs, approve, reject, deploy, merge, ci-status, ci-webhook, deploy-token |
| `/api/v1/devices/*` | Registro y pairing de dispositivos |
| `/api/v1/audit/*` | Traza forense por job |
| `/api/v1/events/*` | Eventos de streaming |
| `/api/v1/memory/*` | Lessons, skills, knowledge, postmortem, refine |
| `/api/v1/tenants/*` | Multi-tenant: registro, contexto, ERP schemas |
| `/api/v1/templates/*` | Listar y personalizar templates |
| `/api/v1/payments/*` | BYOK payment integrations |
| `WS /ws` | WebSocket eventos en tiempo real |

### PWA (frontend-pwa)

- Dashboard con stats en vivo + event log
- Lista de jobs con badges de estado por color
- Visor de diffs con sintaxis coloreada (git diff)
- Botones Approve/Reject offline-aware
- Indicador CI en vivo + botones Merge/Deploy
- Service Worker para uso offline

## Roadmap

| Fase | Commit | Estado |
|------|--------|--------|
| 1. Inicializacion del Workspace | `3fade3d` | Completed |
| 2. Arquitectura core (14 modelos, memoria, politicas) | `3fade3d` | Completed |
| 3. Integracion OpenCode CLI via bridge HTTP | `0bf6272` | Completed |
| 4. PWA offline-first + WebSocket + Visor de Diffs | `45823fb` | Completed |
| 5. Deploy Easypanel + CI/CD + Auto-merge | `27819de` | Completed |
| 6. DopaWeb + BYOK Payments + Multi-tenant | `722b1a2` | Completed |
| 7. Empaquetado final (PyInstaller + Bun compile) | `e06d002` | Completed |

## Pitch

Dopa Code es un orquestador de agentes de IA que vive en tu PC y se controla desde tu movil. No es otro IDE en la nube -- es tu control tower personal.

Elige tus modelos (Opus, Sonnet, DeepSeek via OpenRouter), define tus politicas de seguridad, y deja que Inti planifique, ejecute, revise y despliegue cambios en tu codigo -- mientras tu apruebas o rechazas desde el celular.

Funciona con cualquier proyecto, cualquier stack, cualquier repo Git. Y si estas en el ecosistema Dopa, tenes integracion nativa con ERP, ecommerce, templates y BYOK payments.
