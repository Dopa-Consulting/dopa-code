# AGENTS.md - Dopa Code

Instrucciones para agentes IA y desarrolladores que trabajan en este proyecto.

## Que es Dopa Code

Entorno de desarrollo agentico Local-First. Inti (orquestador Python/FastAPI) maneja agentes que escriben, revisan y despliegan codigo via OpenCode CLI, controlados desde una PWA movil.

## Estructura

```
dopa-code/
├── backend-inti/          # Daemon Python (FastAPI + SQLite)
│   ├── main.py            # Entry point, lifespan, static files
│   ├── inti/
│   │   ├── orchestrator.py  # Multi-sesion: 5 roles, agentes paralelos
│   │   ├── agent_runtime.py # Inti ↔ OpenCode bridge + ERP context
│   │   ├── policies.py      # Perfiles, autonomia, guardrails
│   │   ├── memory.py        # PostMortem, SkillRefiner, MemoryContext
│   │   ├── deploy.py        # Easypanel deploy, CI webhooks, auto-merge
│   │   ├── guardrails.py    # Reglas de proteccion ERP
│   │   ├── openrouter_client.py # OpenRouter + APIs directas + MultiProvider
│   │   ├── webauthn.py      # Passkeys (FaceID/huella)
│   │   ├── voice.py         # Voice command parser
│   │   ├── skills_seeder.py # 6 skills predefinidas DopaWeb
│   │   ├── models/          # 14 modelos SQLAlchemy
│   │   └── api/             # 13 modulos de endpoints REST
├── frontend-pwa/          # PWA React/Vite + Tailwind + Dexie
│   └── src/
│       ├── hooks/          # useWebSocket, useDeploy, useWebAuthn
│       ├── services/       # sync.ts (IndexedDB ↔ backend)
│       ├── pages/          # Dashboard, Jobs, DiffViewer, Models, PRViewer
│       └── db.ts           # Dexie schema
├── agent-runtime/         # Bridge Node.js + OpenCode submodule
│   ├── bridge.js           # HTTP server :4097 → opencode run + git diff
│   └── opencode/           # Git submodule
├── docs/                  # Arquitectura, resumen, n8n workflows
├── .env.example           # Template de variables de entorno
├── quickstart.ps1         # Setup + inicio en un comando
├── install.ps1            # Instalador produccion (Windows Service)
└── AGENTS.md              # Este archivo
```

## Convenciones

- **Nombres**: snake_case en Python, camelCase en TypeScript, kebab-case en URLs
- **Prefijo env vars**: `DOPA_` (DOPA_DATABASE_URL, DOPA_CODE_DUMMY...)
- **Prefijo DB**: `dopa_code.db` (SQLite local)
- **Puertos**: Inti=8000, Bridge=4097, PWA dev=5173
- **Imports**: `from inti.X import Y` (relativo al paquete inti/)
- **Modelos**: heredan de `inti.database.Base`, se importan en `main.py` para creacion de tablas
- **APIs**: un archivo por dominio en `inti/api/`, se registran en `inti/router.py`
- **No circular imports**: `database.py` solo define Base. `main.py` importa modelos.

## Comandos clave

```powershell
# Backend
cd backend-inti
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Bridge
cd agent-runtime
bun bridge.js

# Frontend
cd frontend-pwa
npm install
npm run dev

# Todo junto
.\quickstart.ps1
```

## Reglas para agentes IA

1. **Nunca tocar `database.py`** salvo para agregar imports de modelos nuevos (sin tocar Base/engine)
2. **Modelos nuevos**: crear en `inti/models/`, agregar a `__init__.py`, importar en `main.py`
3. **APIs nuevas**: crear en `inti/api/`, registrar en `inti/router.py`
4. **Servicios nuevos**: crear en `inti/`, importar donde se necesite (evitar circular imports)
5. **No hardcodear secretos**: usar `settings.X` de `inti.config`
6. **Dummy mode**: `if settings.dopa_code_dummy: return dummy_result` antes de logica real
7. **Auditoria**: toda accion relevante → `from inti.audit import log_action`
8. **Eventos WebSocket**: `from inti.events import create_event`
9. **Diffs coloreados en PWA**: respetar los colores verde/rojo/cian/ambar definidos
10. **TypeScript 0 errores**: `cd frontend-pwa && npx tsc --noEmit`

## Modelos LLM configurados (24)

Usar IDs del catalogo en `inti/openrouter_client.py:OPENROUTER_MODELS`.
Proveedores directos: `inti/openrouter_client.py:PROVIDER_ENDPOINTS`.

## Estados de Job

`planned → executing → qa_pending → qa_failed → awaiting_approval → approved → deploying → deployed`
Cancelado: `cancelled` desde cualquier estado.

## Testing

```powershell
cd backend-inti
.\venv\Scripts\python.exe -c "from inti.database import Base; print(len(Base.metadata.tables))"
# Expected: 14

cd frontend-pwa
npx tsc --noEmit
# Expected: no output (0 errors)
```
