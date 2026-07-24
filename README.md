# Dopa Code

Constructor agentico nativo del ecosistema **Dopa**. Inti, el agente andino, orquesta la escritura, revision y despliegue de codigo desde tu PC, controlado desde tu movil via PWA.

## Ecosistema Dopa

| Proyecto | Stack | Rol |
|----------|-------|-----|
| **DopaCRM** | Node.js 24 + Express + Sequelize + PostgreSQL | ERP multi-tenant: facturacion SUNAT, POS, inventario, inbox, AI agents, BYOK |
| **DopaCRM Frontend** | Vite + React 19 + MUI | Dashboard PWA: chat, inbox, POS, billing |
| **DopaWeb** | Next.js + React | Plataforma ecommerce multi-tenant integrada con DopaCRM |
| **Dopacrm-landing** | Next.js 16 + GSAP + Stripe + Cloudflare | Landing page |
| **Dopa Code** | FastAPI + React + Node bridge + OpenCode | Constructor agentico del ecosistema |

## Arquitectura

```
dopa-code
├── backend-inti/     # Daemon FastAPI (Python) - FSM Inti, API REST + WebSocket
├── frontend-pwa/     # PWA movil (React/Vite + Tailwind + Dexie) - ChatOps
├── agent-runtime/    # Bridge HTTP + OpenCode CLI + git submodule opencode/
└── docs/             # Arquitectura, FSM, historial de jobs
```

```
[ PWA Movil ] <──Tailscale VPN──> [ PC Windows: Inti Daemon + Bridge + OpenCode CLI ]
                                        │
                                   [ n8n VPS ] (CI/CD, Webhooks)
                                   [ OpenRouter ] (Opus 4.8, Sonnet 5, DeepSeek)
                                   [ Antigravity ] (QA gratis)
```

## Dopa Code como constructor nativo de DopaWeb

En lugar de un builder visual tipo Elementor, Dopa Code + Inti personalizan templates de ecommerce via lenguaje natural:

```
Cliente: "Cambiar layout de pagina de producto"
Cliente: "Agregar Stripe como metodo de pago"
Cliente: "Ajustar colores segun guia de marca"
    │
    ▼
Inti → Plan (Architect LLM) → Execute (OpenCode) → QA → CI → PWA (approve) → Deploy
```

**BYOK Payments**: el agente integra PSPs externos (Stripe, MercadoPago, PayPal) bajo demanda, con sandbox testing, webhooks y mapping a Dopa ERP.

## Requisitos

- **Python** 3.11+
- **Node.js** 20+
- **Bun** 1.3+ (para el bridge)
- **OpenCode CLI** (global, via npm)
- **Git**

## Desarrollo Local

### Backend (Inti Daemon)

```powershell
cd backend-inti
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints (17 total):
- `GET /health` - Health check
- `GET /api/v1/jobs/` - Lista de jobs
- `POST /api/v1/jobs/` - Crear job con perfil y autonomia
- `GET /api/v1/memory/skills` - Skills auto-mejorables
- `POST /api/v1/memory/postmortem/{id}` - Learning loop
- `WS /ws` - WebSocket eventos

### Bridge (Agent Runtime)

```powershell
cd agent-runtime
bun bridge.js          # Inicia bridge en localhost:4097
```

### Frontend (PWA)

```powershell
cd frontend-pwa
npm run dev            # http://localhost:5173
```

## Roadmap

| Fase | Estado |
|------|--------|
| 1. Inicializacion del Workspace | Completed |
| 2. Arquitectura core (12 modelos, AgentRuntime, politicas, eventos, auditoria, memoria) | Completed |
| 3. Integracion OpenCode CLI via bridge HTTP | Completed |
| 4. PWA offline-first + WebSockets + Visor de Diffs/PRs | Pending |
| 5. Seguridad (Tailscale, WebAuthn) + CI/CD (n8n + Easypanel) | Pending |
| 6. Integracion DopaWeb (templates, BYOK payments, agentes por tenant) | Pending |
| 7. Empaquetado final (PyInstaller + Windows Service) | Pending |

## Pitch

Dopa Code es un constructor agentico que vive en tu PC y se controla desde tu movil. No es otro IDE -- es el taller de desarrollo nativo del ecosistema Dopa, donde los agentes personalizan ecommerce, integran pagos y mejoran el ERP sin plugins ni lock-in.
