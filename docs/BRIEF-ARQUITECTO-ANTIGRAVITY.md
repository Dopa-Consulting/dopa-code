# Dopa Code — Resumen para el Agente Arquitecto (Antigravity)

## Contexto

Este documento resume todo lo implementado en Dopa Code, un entorno de desarrollo agentico Local-First. Está diseñado para que el Agente Arquitecto que usamos en Antigravity pueda entender el proyecto completo, dar su opinion, y sugerir mejoras de integracion con DopaCRM.

---

## 1. Que es Dopa Code

Dopa Code es un orquestador de agentes de IA que vive en la PC del desarrollador y se controla desde una PWA movil. Inti (el agente andino) orquesta la escritura, revision y despliegue de codigo via OpenCode CLI, usando modelos LLM configurables (BYOK: OpenRouter, APIs directas, Gemini Interactions, Antigravity nativo).

**Repo**: https://github.com/Dopa-Consulting/dopa-code
**Stack**: Python 3.14 + FastAPI + SQLAlchemy 2.0 + SQLite | React 19 + Vite 8 + Tailwind 4 + TypeScript | Node.js/Bun bridge

---

## 2. Estado actual — 22 commits, MVP completo

### 2.1 Backend (Inti Daemon) — 14 tablas, 40+ endpoints

**Modelos SQLAlchemy**: jobs, job_steps, diffs, approvals, audit_log, events, ci_runs, devices, experience_lessons, skill_definitions, skill_executions, project_knowledge, tenants, payment_integrations

**Modulos de servicio (11)**:
| Modulo | Funcion |
|--------|---------|
| `orchestrator.py` | Multi-sesion: 5 roles (architect, builder, reviewer, deployer, custom) en paralelo |
| `agent_runtime.py` | Inti ↔ OpenCode bridge + multi-provider routing + discovery mode |
| `policies.py` | 3 perfiles LLM + 5 project types + 4 niveles autonomia + allowlist comandos |
| `memory.py` | PostMortem automático, SkillRefiner, MemoryContext (replica de Hermes) |
| `guardrails.py` | 8 reglas de proteccion ERP (block/warn/info) + 2 perfiles (dopaweb_theme/payment) |
| `deploy.py` | PreDeployAudit (6 checks) + Easypanel deploy + CI webhooks + auto-merge |
| `openrouter_client.py` | Cliente OpenRouter + 6 proveedores directos + 24 modelos |
| `gemini_interactions.py` | Gemini Interactions API (GA 2026) con streaming SSE + Deep Research + Antigravity nativo |
| `webauthn.py` | Passkeys biometricos (MVP con ruta a py_webauthn para produccion) |
| `voice.py` | Voice command parser (5 comandos) |
| `langgraph_fsm.py` | Prototipo StateGraph con 9 nodos y QA paralelo |

### 2.2 Frontend (PWA) — 6 paginas, offline-first

| Pagina | Funcion |
|--------|---------|
| **Chat** | Chat enriquecido con Markdown, streaming SSE, quick replies, botones Approve/Reject/Merge |
| **Dashboard** | Stats en vivo via WebSocket, sesiones activas, event log |
| **Jobs** | Lista con badges de estado por color, filtros |
| **DiffViewer** | Sintaxis coloreada git diff, CI status, botones Merge/Deploy, input token Easypanel |
| **Models** | Selector multi-proveedor (6 tabs), 24 modelos, test chat, creditos, modelos gratis |
| **PRViewer** | Placeholder para integracion GitHub + WebAuthn |

### 2.3 Skills (22) — libreria nativa

**Origenes**: obra/superpowers (261k ★), mattpocock/skills (187k ★), emilkowalski/skills (20k ★), anthropics/skills (164k ★), Hainrixz/the-architect (371 ★), Hainrixz/all-deploy (47 ★), Hainrixz/cyber-neo (214 ★)

| Categoria | Skills |
|-----------|--------|
| **General (10)** | brainstorming, tdd, debugging, planning, code-review, git-worktrees, subagent-dev, safe-deploy, the-architect, cyber-neo-security |
| **Design (4)** | frontend-design, animations, branding, canvas-design |
| **DopaWeb (6)** | product-page, branding, sections, checkout-ui, payment-byok, backend-refactor |
| **Meta (2)** | writing-skills, using-skills |

### 2.4 Bridge + Empaquetado

- `bridge.js`: Servidor HTTP :4097 ↔ OpenCode CLI via subprocess + git diff
- `dopa-bridge.exe`: Bun standalone compile (98 MB)
- `dopa-code-daemon.exe`: PyInstaller one-file (22 MB)
- `install.ps1`: Instalador Windows con servicio nssm
- `quickstart.ps1`: Setup + inicio en un comando

### 2.5 Seguridad (auditado)

- WebAuthn: MVP documentado con ruta a py_webauthn
- SQLite: PRAGMA foreign_keys=ON + WAL mode
- FK cascades: cascade="all, delete-orphan" en 6 relationships
- Service Worker: /api/* y /ws excluidos del cache
- PreDeployAudit: 6 checks que bloquean deploy si fallan

---

## 3. Conexion con el ecosistema Dopa

```
Dopa Code (constructor agentico)
    │
    ├── Personaliza DopaWeb (templates ecommerce)
    │     → Architect diseña, Builder ejecuta, Reviewer audita
    │     → Guardrails protegen facturacion SUNAT + checkout
    │
    ├── Integra BYOK payments (Stripe, MercadoPago, etc.)
    │     → Agente genera checkout + webhooks + mapping ERP
    │     → QA en sandbox del PSP antes de produccion
    │
    ├── Refactoriza DopaCRM (backend Express + Sequelize)
    │     → Skills: backend-refactor, tdd, systematic-debugging
    │     → Guardrails: facturacion SUNAT intocable
    │
    ├── Mejora DopaCRM Frontend (Vite + React + MUI)
    │     → Skills: frontend-design, animations, branding
    │
    └── Despliega todo via Easypanel (deploy.py)
          → PreDeployAudit + CI webhooks + auto-merge
```

## 4. Multi-provider LLM

| Forma | Proveedores | Modelos | Costo |
|-------|-------------|---------|-------|
| OpenRouter | Todos | 24 modelos (4 gratis) | +5% margen |
| APIs directas | OpenAI, Anthropic, DeepSeek, Google, Groq | nativos | 0% margen |
| Gemini Interactions | Google | 8 modelos + Deep Research + Antigravity Agent | Google pricing |
| Bridge (OpenCode CLI) | opencode run | el que tengas configurado | depende |

## 5. Pipeline agentico completo

```
Humano (PWA/Chat): "Refactorizar checkout DopaWeb"
    │
    ▼
Discovery Mode (the_architect skill)
    → Preguntas inteligentes → Deep Research → Blueprint 16 secciones
    │
    ▼
Planner (Architect LLM: Opus 4.8 / Sonnet 5 / Deep Research)
    → Lee guardrails + ERP context + memoria de skills
    │
    ▼
Executor (Builder LLM: DeepSeek V4 + OpenCode CLI)
    → Rama aislada (git worktree) → aplica cambios → git diff
    │
    ▼
QA (Reviewer: Antigravity Agent nativo / Gemini)
    → Cyber Neo: 11 dominios OWASP → analisis paralelo
    → Guardrails: bloquea cambios en archivos protegidos
    │
    ▼
CI (GitHub Actions → n8n → Inti webhook)
    │
    ▼
Aprobacion Humana (PWA: WebAuthn FaceID)
    → [Approve] [Reject] [Merge] [Deploy]
    │
    ▼
Deploy (Easypanel: PreDeployAudit → preview → health check → prod)
    │
    ▼
PostMortem (Memory: lecciones aprendidas → refina skills)
```

---

## 6. Recomendaciones para seguir mejorando

### 6a. Corto plazo (este sprint)

1. **Probar con un job real de DopaCRM**: usar Dopa Code para hacer un cambio pequeño en DopaCRM y ver el pipeline completo funcionando
2. **Configurar Deep Research para el Architect**: probar `/gemini/deep-research` con una pregunta real de arquitectura
3. **Integrar n8n con webhooks reales**: que un PR en GitHub realmente dispare el pipeline de Inti
4. **Poblar la memoria con experiencia real**: ejecutar 5-10 jobs contra DopaCRM/DopaWeb y dejar que PostMortem refine las skills

### 6b. Mediano plazo

1. **WebAuthn produccion**: instalar py_webauthn y hacer verificacion criptografica real
2. **Agent marketplace**: skills contribuidas por la comunidad
3. **Multi-workspace**: que Inti maneje multiples proyectos simultaneamente (DopaCRM + DopaWeb + Landing)
4. **Voice commands reales**: integrar ElevenLabs Speech Engine para comandos por voz

### 6c. Largo plazo

1. **LangGraph migration**: feature flag para QA paralelo real
2. **Dopa Academy integration**: skills + blueprints + lecciones como contenido de Academy
3. **Self-healing**: si CI falla, Inti analiza el error y propone fix automaticamente
4. **Agent swarm**: multiples builders trabajando en paralelo sobre distintos modulos

---

## 7. Preguntas para el Agente Arquitecto (Antigravity)

1. **Integracion**: Como ves la integracion Dopa Code ↔ DopaCRM? Que falta para que sea fluida?

2. **Delegacion**: Actualmente delegamos tareas manualmente desde Antigravity. Como podriamos hacer que Inti reciba tareas directamente del Agente Arquitecto y las ejecute sin intervencion humana?

3. **Skills**: De las 22 skills implementadas, cuales crees que son mas utiles para el desarrollo de DopaCRM? Faltan skills especificas del dominio ERP?

4. **Guardrails**: Las reglas de proteccion actuales cubren facturacion SUNAT, checkout, y webhooks. Que otros archivos/modulos de DopaCRM deberian estar protegidos?

5. **Memoria**: El sistema de memoria (PostMortem + SkillRefiner) aprende de cada job. Como podriamos alimentarlo con el historial de decisiones que ya tomamos en DopaCRM?

6. **Pipeline**: Preferis que el Agente Arquitecto siga haciendo merge manual (con CI verde) o activamos auto-merge en staging con `auto_merge_staging`?

7. **Prioridad**: De las recomendaciones en la seccion 6, cual priorizarias primero?
