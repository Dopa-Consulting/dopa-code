# Auditoria Dopa Code — Julio 2026

## Resumen Ejecutivo

Dopa Code tiene **infraestructura solida** (23 modulos backend, 14 modelos DB, 22 skills, 24 LLMs) pero la **experiencia de usuario es un chatbot basico**. El 70% del codigo construido no esta conectado al flujo principal del Chat. La brecha con Hermes Agent es significativa en la capa de experiencia (loop de agente, memoria activa, contexto persistente).

---

## 1. Que funciona

| Componente | Estado | Evidencia |
|-----------|--------|-----------|
| Daemon FastAPI | OK | Responde health, docs, 35+ endpoints |
| OpenRouter | OK | DeepSeek V4 responde en Chat |
| Gemini Interactions | OK | 2.5 Flash responde en Chat + streaming |
| Bridge OpenCode | OK | CLI mode en :4097, hook co-author instalado |
| Creacion de Jobs | OK | 5 jobs creados visibles en tab Jobs |
| Creacion de archivos | OK | `crea un archivo test.md` funciona |
| Lectura de archivos | OK | `lee el archivo main.py` funciona |
| Creacion de carpetas | OK | `crea una carpeta docs` funciona |
| Git diff/status | OK | `git diff`, `git status` funcionan |
| Creacion de sesiones | OK | `crea sesion builder/architect` funciona |
| PWA mobile | OK | Accesible via ngrok desde celular |
| Skills (DB) | OK | 22 skills cargadas en tabla |
| Modelos LLM | OK | 24 en catalogo, 6 proveedores |

## 2. Que NO funciona

| Problema | Severidad | Detalle |
|----------|-----------|---------|
| **Workspace invisible** | CRITICO | El usuario no sabe donde trabaja Inti. No hay configuracion de workspace, no se muestra en la UI, no se puede cambiar. |
| **Chat no usa el pipeline FSM** | CRITICO | Los jobs se crean pero el pipeline no se ejecuta automaticamente. Planner, Executor, QA, PostMortem estan construidos pero no conectados. |
| **Skills no se usan** | CRITICO | 22 skills precargadas que jamas se consultan durante un job. No hay skill lookup en el flujo del Chat. |
| **Memoria no activa** | CRITICO | PostMortem, SkillRefiner, MemoryContext existen pero no se invocan desde el Chat. Cada job termina sin registrar lecciones. |
| **Guardrails no aplicados** | HIGH | Las reglas de proteccion ERP existen pero no se ejecutan en el pipeline del Chat. |
| **Agentes no orquestan** | HIGH | Orchestrator crea sesiones pero no asigna jobs ni ejecuta tareas reales. |
| **Chat sin historial** | HIGH | sessionStorage persiste pero se pierde entre dispositivos. No hay historial de sesiones como en OpenCode/Hermes. |
| **No aprendizaje** | HIGH | 0 lecciones registradas en experience_lessons porque PostMortem nunca se llama. |
| **WebAuthn no integrado** | MEDIUM | Passkeys existen pero no se usan en approve/merge/deploy del Chat. |
| **Deploy no conectado** | MEDIUM | deploy.py + PreDeployAudit existen pero no se disparan desde comandos del Chat. |
| **ERP context no usado** | MEDIUM | erp_context.py existe pero el Chat no inyecta schemas de Dopa en los prompts. |
| **Agent-to-agent muerto** | MEDIUM | agent_comm.py tiene 6 tipos de mensajes pero ninguna sesion los usa. |
| **Multi-provider no aplicado** | LOW | OpenRouter funciona, Gemini funciona, pero el routing automatico (Gemini → fallback OpenRouter) es fragil. |

## 3. Brecha con Hermes Agent

| Capacidad | Hermes Agent | Dopa Code | Gap |
|-----------|-------------|-----------|-----|
| **Loop de agente** | Bucle ReAct: observar→pensar→actuar→observar | Chat→comando directo. Sin loop. | TOTAL |
| **Memoria persistente** | MEMORY.md, USER.md, skills auto-mejorables | Tablas existentes pero inactivas | TOTAL |
| **Contexto entre sesiones** | Recuerda conversaciones, preferencias, patrones | sessionStorage se pierde al cerrar | TOTAL |
| **Skills activas** | Skills consultadas antes de cada accion | 22 skills en DB, nunca consultadas | TOTAL |
| **Multi-herramienta** | Integra OpenCode, web search, file system | Solo filesystem basico + git | PARCIAL |
| **Auto-mejora** | Nudgea, compacta y refina skills automaticamente | SkillRefiner existe pero no se ejecuta | TOTAL |
| **Delegacion** | Orquesta multiples agentes especializados | Orchestrator con 5 roles pero sin jobs reales | TOTAL |
| **UI** | Telegram (chat natural) | PWA con Chat (comandos) | PARCIAL |
| **Workspace awareness** | Sabe donde esta trabajando | Hardcodeado, no configurable | TOTAL |

## 4. Diagnostico raiz

El problema no es falta de codigo. Es **falta de integracion**.

```
LO QUE TENEMOS:          LO QUE USAMOS:
═══════════════          ══════════════
orchestrator.py  ─┐
agent_runtime.py ─┤
memory.py        ─┤
skills_seeder.py ─┤     chat_commands.py  ← solo esto
policies.py      ─┤         │
guardrails.py    ─┤         ▼
deploy.py        ─┤     DB directa + file I/O
events.py        ─┤     (+ LLM para conversacion)
audit.py         ─┤
agent_comm.py    ─┘
```

El 70% del backend esta construido pero **ningun modulo se conecta al flujo principal del Chat**. El Chat es un thin wrapper que hace file I/O directo y consultas SQL simples, ignorando completamente la FSM, los skills, la memoria y los guardrails.

## 5. Plan de accion (orden de prioridad)

### Fase 1: Workspace + Chat funcional (1-2 dias)

1. **Workspace configurable**: Variable `DOPA_WORKSPACE` o config desde PWA. Mostrar en la UI.
2. **Chat usa el pipeline real**: Cada comando `crea X` o `hace Y`:
   - Crea Job → Planner (skills + memory context) → Executor (bridge/OpenCode) → QA → PostMortem → respuesta al Chat
3. **Skills activas**: Antes de cada job, `MemoryContext.get_context_for_job()` busca skills por tags y las inyecta en el prompt del Planner.

### Fase 2: Memoria + Aprendizaje (2-3 dias)

4. **PostMortem automatico**: Al completar cada job, ejecutar `PostMortem.run(job_id)` → guardar lecciones en experience_lessons.
5. **SkillRefiner periodico**: Cada N jobs, refinar skills basado en success_rate.
6. **Historial de sesiones**: Persistir mensajes en DB (no solo sessionStorage). Mostrar historial en PWA.

### Fase 3: Agentes reales (3-5 dias)

7. **Loop de agente**: Implementar ReAct loop: observar workspace → pensar (LLM + skills) → actuar (bridge/OpenCode) → observar resultado.
8. **Multi-agente**: Orchestrator asigna jobs a sesiones. Builder ejecuta, Reviewer audita, Architect planea.
9. **Delegacion entre agentes**: Architect → Builder (delegate_task), Builder → Reviewer (request_review).

---

## 6. Recomendacion final

Dopa Code no esta listo para reemplazar a Hermes. Pero la infraestructura construida es solida y completa. El gap es 100% integracion, no features nuevas.

**Accion inmediata**: Cablear el Chat al pipeline FSM existente. Conectar skills, memoria y guardrails al flujo principal. Definir el workspace.

Sin esto, Dopa Code seguira siendo "un prompt y nada mas".
