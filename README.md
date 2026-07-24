# Dopa Code

Entorno de desarrollo agentico **Local-First**. Inti, el agente andino, orquesta la escritura, revision y despliegue de codigo desde tu PC, controlado desde tu movil via PWA.

## Arquitectura

```
dopa-code
├── backend-inti/     # Daemon FastAPI (Python) - FSM Inti, API REST + WebSocket
├── frontend-pwa/     # PWA movil (React/Vite + Tailwind + Dexie) - ChatOps
├── agent-runtime/    # Entorno aislado Node.js para el CLI de OpenCode
└── docs/             # Documentacion de arquitectura y FSM
```

```
[ PWA Movil ] <--Tailscale VPN--> [ PC Windows: Inti Daemon + OpenCode CLI ]
                                        |
                                   [ n8n VPS ] (CI/CD, Webhooks)
                                   [ OpenRouter ] (LLMs BYOK)
```

## Requisitos

- **Python** 3.11+
- **Node.js** 20+
- **Git**

## Desarrollo Local

### Backend (Inti Daemon)

```powershell
cd backend-inti
.\venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints:
- `GET /health` - Health check
- `GET /api/v1/health/` - Estado de Inti
- `GET /api/v1/jobs/` - Lista de jobs
- `POST /api/v1/devices/pair` - Vinculacion QR

### Frontend (PWA)

```powershell
cd frontend-pwa
npm run dev
```

Abre `http://localhost:5173` en el navegador.

### Agent Runtime

```powershell
cd agent-runtime
# Fase 3: Instalacion del CLI de OpenCode
```

## Roadmap

| Fase | Estado |
|------|--------|
| 1. Inicializacion del Workspace | Completado |
| 2. Daemon FastAPI (Inti FSM) + SQLite | Pendiente |
| 3. Integracion OpenCode + extraccion de diffs | Pendiente |
| 4. PWA offline-first + WebSockets + Visor de Diffs | Pendiente |
| 5. Seguridad (Tailscale, WebAuthn) + CI/CD (n8n) | Pendiente |
| 6. Empaquetado final (PyInstaller) | Pendiente |

## Pitch

Dopa Code es un orquestador de agentes de IA que vive en tu PC y se controla desde tu movil, pensado para flujos reales de desarrollo y DevOps.

Todo corre en tu infraestructura: tu PC, tu repositorio, tus pipelines. Tu eliges los modelos (via OpenRouter o claves propias), tu defines las politicas de seguridad, y Dopa Code se convierte en tu control tower personal.
