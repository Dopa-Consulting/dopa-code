# Dopa Code — Resumen de Implementacion (Julio 2026)

## Para: Agente Perplexity que ayudo a darle forma al proyecto

---

## 1. Lo que se construyo (10 commits, 12 sprints)

### Stack final

| Capa | Tecnologia | Archivos |
|------|-----------|----------|
| Backend | Python 3.14 + FastAPI + SQLAlchemy 2.0 + SQLite | 28 .py |
| Frontend | React 19 + Vite 8 + Tailwind 4 + Dexie + TypeScript | 12 .ts/.tsx |
| Bridge | Node.js/Bun + OpenCode CLI + git submodule | 3 .js |
| Infra | PyInstaller + Bun compile + PowerShell | 2 spec/ps1 |

### Backend (backend-inti/inti/)

**14 modelos SQLAlchemy:**
```
jobs, job_steps, diffs, approvals, audit_log, events, ci_runs, devices,
experience_lessons, skill_definitions, skill_executions, project_knowledge,
tenants, payment_integrations
```

**32 endpoints REST:**
- `/health` — estado del daemon
- `/api/v1/jobs/*` (10) — CRUD, approve/reject, deploy, merge, ci-status, ci-webhook, deploy-token
- `/api/v1/devices/*` (3) — registro, pairing, QR
- `/api/v1/audit/*` (1) — trazabilidad forense
- `/api/v1/events/*` (1) — streaming de eventos
- `/api/v1/memory/*` (7) — lessons, skills, knowledge, postmortem, refine, context
- `/api/v1/tenants/*` (4) — multi-tenant
- `/api/v1/templates/*` (2) — catalogo + personalizacion
- `/api/v1/payments/*` (3) — BYOK payment integrations
- `/api/v1/openrouter/*` (10) — modelos, chat, config, proveedores directos

**11 modulos de servicio:**
```
agent_runtime.py     — Inti ↔ OpenCode bridge
policies.py          — 3 perfiles de modelo + 6 project types + 4 niveles autonomia
events.py            — 10 tipos de eventos WebSocket
audit.py             — auditoria forense
memory.py            — PostMortem, SkillRefiner, MemoryContext (replica de Hermes)
deploy.py            — Easypanel deploy, CI webhooks, auto-merge
guardrails.py        — 8 reglas de proteccion ERP (block/warn/info)
skills_seeder.py     — 6 skills predefinidas para DopaWeb
template_service.py  — bridge de repos de templates
payment_service.py   — BYOK payment integration con contexto ERP
erp_context.py       — schemas + reglas de negocio desde DopaCRM
openrouter_client.py — cliente directo OpenRouter + MultiProviderClient
tenant_resolver.py   — resolucion multi-tenant (workspace path, ERP endpoint)
```

### Frontend (frontend-pwa/)

**6 paginas:**
- `Dashboard` — stats en vivo via WebSocket, event log, sync manual
- `Jobs` — lista con badges de estado, perfil, rama visible
- `DiffViewer` — sintaxis coloreada (git diff), approve/reject offline-aware, CI status, Merge/Deploy
- `PRViewer` — placeholder GitHub + WebAuthn
- `Models` — selector multi-proveedor, chat test, creditos, modelos gratis

**4 hooks/servicios:**
- `useWebSocket` — conexion WS con reconexion automatica + subscribe/unsubscribe
- `useDeploy` — polling CI cada 10s, deploy, merge, saveToken
- `sync.ts` — IndexedDB ↔ backend + pendingActions queue
- `db.ts` — Dexie schema (jobs, diffs, pendingActions)

### Bridge (agent-runtime/)

- `bridge.js` — servidor HTTP :4097 que invoca `opencode run` via subprocess + `git diff`
- `dopa-bridge.exe` — compilado standalone con `bun build --compile` (98 MB)
- OpenCode v1.18.4 como git submodule en `agent-runtime/opencode/`

### Empaquetado

- `dopa-code-daemon.exe` — PyInstaller one-file (22 MB)
- `dopa-bridge.exe` — Bun standalone (98 MB)
- `install.ps1` — instalador PowerShell que verifica deps, copia binarios, crea .env, registra servicio Windows via nssm

---

## 2. Diferenciadores clave vs Cursor / competencia

| Aspecto | Cursor | Dopa Code |
|---------|--------|-----------|
| Dónde corre | SaaS / app electron | **Tu PC** (local-first) |
| UI | Desktop IDE | **PWA móvil** (ChatOps) |
| Modelos | Propios | **BYOK**: OpenRouter + APIs directas |
| Memoria | Sesion | **Persistente**: PostMortem + skills auto-mejorables |
| Seguridad | Cloud | **Local**: guardrails, allowlist, workspace jail |
| ERP/Ecommerce | No | **Nativo**: DopaCRM + DopaWeb |
| Monetizacion | $20/mes suscripcion | Open-core: community gratis, pro/enterprise pago |
| Precio LLM | Fijo | **Vos elegis**: gratis (Gemma), barato (DeepSeek), premium (Opus) |

---

## 3. Propuestas de mejora para el agente Perplexity

Estas son areas donde nos gustaria tu analisis para la proxima iteracion:

### 3a. Seguridad y WebAuthn

El diseño original planteaba Tailscale VPN + MagicDNS + WebAuthn + QR handshake para la PWA. Implementamos la estructura (devices, pairing, JWT) pero falta:
- Integracion real de WebAuthn (biometria para aprobaciones criticas)
- Tailscale ACLs configuradas
- QR handshake con token de un solo uso
- Encriptacion de credenciales BYOK en reposo

¿Que patrones de WebAuthn recomendarias para una PWA local-first? ¿Conviene Passkeys sobre U2F?

### 3b. n8n + CI/CD orquestacion

El plan original mencionaba n8n en VPS como orquestador externo. Implementamos el deploy via Easypanel y los webhooks de CI, pero falta:
- Integracion real con n8n (workflows predefinidos)
- GitHub Actions auto-configurados por Inti
- Health checks + auto-shutdown via enchufe inteligente
- Rollback automatizado si el deploy falla

¿Como estructurarias los workflows de n8n para un flujo completo: PR abierto → CI → n8n notifica → Inti auto-mergea → deploy Easypanel → health check → rollback si falla?

### 3c. Voice + Multimodal (ElevenLabs / Gemini)

El ecosistema Dopa ya usa ElevenLabs y Gemini para voice agents. Dopa Code hoy es solo texto/chat. ¿Como integrarias:
- Voice commands desde el movil ("Inti, ejecuta el job 42")
- Resumen de diffs por voz ("El ejecutor cambio 3 archivos, ¿apruebo?")
- Screenshots/previews de componentes generados por el agente

### 3d. Escalabilidad multi-agente

Hoy el pipeline es secuencial: Planner → Executor → QA → Human. En tu analisis original mencionaste LangGraph y AutoGen para multi-agente. Con 12 sprints de experiencia construyendo esto, ¿rees tu recomendacion sigue siendo FSM propio? ¿O en este punto conviene migrar a LangGraph?

### 3e. Estrategia de pricing

Planteamos open-core con 4 niveles. ¿Que metricas deberiamos trackear desde ahora para justificar el pricing? ¿Crees que el modelo BYOK (el usuario paga sus tokens directamente) es sostenible como negocio, o deberiamos considerar ser nosotros el merchant of record?

---

## 4. Metricas del proyecto

| Metrica | Valor |
|---------|-------|
| Commits | 11 |
| Archivos fuente (~sin node_modules) | ~55 |
| Tablas DB | 14 |
| Endpoints REST | 32 |
| WebSocket channels | 1 (+ eventos tipados) |
| Modelos LLM precargados | 12 (4 gratis) |
| Proveedores directos | 5 (OpenAI, Anthropic, DeepSeek, Google, Groq) |
| Perfiles de tarea | 6 (con guardrails y skills) |
| Skills predefinidas | 6 |
| Reglas de guardrail | 8 |
| Niveles de autonomia | 4 |
| TypeScript + Python errores | 0 |
