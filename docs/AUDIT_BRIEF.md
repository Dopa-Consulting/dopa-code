# Brief de Auditoria: Dopa Code

## Proposito
Auditoria tecnica completa del repositorio Dopa Code. Revisar calidad de codigo, seguridad, patrones, y deuda tecnica. Output accionable para priorizar mejoras.

## Contexto del proyecto

Dopa Code es un entorno de desarrollo agentico Local-First. Inti (orquestador Python/FastAPI) maneja agentes que escriben, revisan y despliegan codigo via OpenCode CLI, controlados desde una PWA movil (React + Tailwind + Dexie).

**Repo**: https://github.com/Dopa-Solutions/dopa-code
**Stack**: Python 3.14 + FastAPI + SQLAlchemy 2.0 + SQLite | React 19 + Vite 8 + Tailwind 4 + TypeScript | Node.js/Bun bridge

## Estructura clave

```
backend-inti/inti/
├── models/          # 14 modelos SQLAlchemy (job, diff, approval, audit_log, tenant...)
├── api/             # 13 modulos de endpoints REST + WebSocket
├── orchestrator.py  # Gestion multi-sesion (5 roles, agentes paralelos)
├── agent_runtime.py # Inti <-> OpenCode bridge (subprocess + httpx)
├── policies.py      # Perfiles de modelo, 5 project types, 4 niveles autonomia
├── memory.py        # PostMortem, SkillRefiner, MemoryContext
├── guardrails.py    # Reglas de proteccion ERP (8 reglas)
├── deploy.py        # Easypanel deploy, CI webhooks, auto-merge
├── openrouter_client.py # OpenRouter + APIs directas (6 providers, 24 modelos)
├── webauthn.py      # Passkeys biometricos
├── voice.py         # Voice command parser
└── langgraph_fsm.py # Prototipo StateGraph (no instalado)
```

## Areas a auditar (priorizadas)

### 1. Seguridad (CRITICO)

- **API keys en repositorio**: verificar que no haya keys hardcodeadas
- **WebAuthn**: el endpoint `/register/complete` guarda `public_key` como el `challenge` (posible bug linea ~35 de api/webauthn.py)
- **Guardrails**: las reglas se aplican en `agent_runtime._validate_guardrails()` pero solo en QA -- deberian aplicarse tambien pre-ejecucion
- **Workspace jail**: `agent_runtime.py` tiene paths pero no valida que el workspace este dentro de una jaula permitida
- **CORS**: `allow_origins=["*"]` en produccion es inseguro

### 2. Integridad de datos (ALTO)

- **Transacciones**: `audit.py:log_action()` atrapa excepciones y loggea warning -- deberia fallar hard si no puede auditar
- **Foreign keys**: SQLite no las fuerza por defecto. Verificar que `PRAGMA foreign_keys=ON`
- **Cascading deletes**: no hay `ondelete` en los modelos. Borrar un job deja huerfanos

### 3. Performance (MEDIO)

- **`memory.py:MemoryContext.get_context_for_job()`** hace 3 queries secuenciales. Podrian ser concurrentes
- **`deploy.py:DeployService.trigger_deploy()`** hace multiples `async with async_session()` -- deberia ser una sesion
- **WebSocket**: no tiene heartbeat/ping. Conexiones pueden quedar zombie

### 4. Patrones y consistencia (MEDIO)

- **Circular imports**: `database.py` no importa modelos, `main.py` si. Verificar que se mantenga ese patron
- **Async vs sync**: `audit.py:log_action` es async pero `agent_runtime._audit` la llama sin await. Verificar
- **Typing**: modelos usan `Mapped[str | None]` en algunos lados y `Optional[str]` en otros
- **Error handling**: httpx calls en `agent_runtime.py` atrapan excepciones y devuelven dicts de error. Patron inconsistente con el resto

### 5. Frontend (MEDIO)

- **TypeScript strict**: verificar que `verbatimModuleSyntax` y `noUnusedLocals` esten activos
- **IndexedDB sync**: `sync.ts:flushPendingActions()` no maneja conflictos de version
- **Service Worker**: `sw.js` cachea todo -- deberia excluir `/api/*`
- **WebSocket reconnect**: exponencial backoff seria mejor que fixed 3s

### 6. Deuda tecnica (BAJO)

- **`openrouter_client.py`**: los metodos `_chat_openai_compat`, `_chat_anthropic`, `_chat_google` son codigo duplicado que podria unificarse
- **`guardrails.py`**: las reglas son estaticas. Deberian cargarse de config
- **`langgraph_fsm.py`**: file de 444 lineas que es un prototipo. Deberia moverse a `docs/` o `prototypes/`
- **Tests**: solo existe `test_smoke.py`. Sin tests unitarios para servicios core

## Formato de output esperado

Estructurar hallazgos por archivo, con severidad y accion sugerida:

```markdown
## [ARCHIVO] titulo breve

- **Severidad**: CRITICAL | HIGH | MEDIUM | LOW
- **Linea**: ~numero o rango
- **Hallazgo**: descripcion del problema
- **Impacto**: que podria fallar
- **Accion sugerida**: fix concreto (idealmente con snippet)
```

## Archivos a revisar (top 10 por prioridad)

1. `backend-inti/inti/agent_runtime.py` -- corazon del sistema
2. `backend-inti/inti/api/webauthn.py` -- seguridad biometrica
3. `backend-inti/inti/orchestrator.py` -- multi-agente
4. `backend-inti/inti/deploy.py` -- deploy + CI
5. `backend-inti/inti/guardrails.py` -- proteccion ERP
6. `backend-inti/inti/memory.py` -- memoria persistente
7. `backend-inti/inti/api/jobs.py` -- API principal
8. `frontend-pwa/src/services/sync.ts` -- offline-first
9. `frontend-pwa/src/hooks/useWebSocket.ts` -- tiempo real
10. `backend-inti/inti/database.py` -- SQLite config

## Notas adicionales

- El proyecto tiene **dummy mode** (`DOPA_CODE_DUMMY=1`). Verificar que todas las funciones lo respeten
- Los guardrails para DopaWeb deben proteger facturacion SUNAT (intocable)
- La PWA usa `localhost:8000` hardcodeado. Deberia ser configurable via env
- `quickstart.ps1` y `install.ps1` son scripts PowerShell -- verificar que manejen errores correctamente
