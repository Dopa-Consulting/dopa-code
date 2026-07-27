# Dopa Code — Brief de Auditoria y Refactorizacion

## Para otro agente IA: Lo que se construyo vs lo que funciona

---

## 1. El proyecto en numeros

| Metrica | Construido | Funciona | Gap |
|---------|-----------|----------|-----|
| Modulos backend | 25 .py | ~5 se usan | 80% inactivo |
| Modelos SQLAlchemy | 14 tablas | 4 se usan | 70% inactivo |
| Endpoints REST | 35+ | ~10 responden correctamente | 70% buggy |
| Skills | 22 en DB | 0 se consultan | 100% inactivo |
| Modelos LLM | 24 en catalogo | 2 configurados | OK |
| Paginas PWA | 6 | 2 funcionales (Chat, Jobs) | 60% |
| Tests | 0 | 0 | Nada |

## 2. Lo que SI funciona

- `GET /health` — health check OK
- `POST /api/v1/sessions/` — crear sesiones (tras fix de Body params)
- `GET /api/v1/sessions/` — listar sesiones
- OpenRouter chat (DeepSeek V4) — responde en el Chat
- Gemini 2.5 Flash — responde en el Chat (sin system_instruction que causa 400)
- Comandos basicos de archivos: `crea un archivo`, `lee archivo`, `crea carpeta`, `git diff`, `git status`
- Creacion de Jobs en DB al decir `Crea X` con verbo
- Aprobacion de Jobs con pipeline FSM simulado (dummy mode)
- Autenticacion basica via token (DOPA_ACCESS_TOKEN)
- ngrok tunnel para acceso movil
- Bridge OpenCode corriendo en :4097

## 3. Lo que NO funciona

### Critico
- **Approve/reject**: El endpoint aprobo jobs pero el pipeline FSM (plan_change, apply_change, generate_diff, qa_review) no produce resultados visibles. Los diffs nunca llegan a la DB o el DiffViewer no los muestra.
- **Chat sin retroalimentacion**: El usuario no sabe si algo paso. No hay streaming de progreso real de OpenCode. Los comandos devuelven texto plano sin indicar si fallaron.
- **Workspace invisible**: Hardcodeado a `backend-inti/`. No configurable desde UI. El usuario nunca sabe donde esta trabajando.
- **No hay loop de agente**: No hay ciclo observar→pensar→actuar como Hermes. Solo comandos unicos y directos.
- **Skills inactivas**: 22 skills en DB que jamas se consultan. MemoryContext, SkillRefiner, PostMortem nunca se invocan desde el flujo del Chat.

### Alto
- **API params bug sistemico**: Muchos endpoints POST aceptan query params en vez de Body. Corregido en sessions y jobs pero quedan openrouter, webauthn, deploy, merge, etc.
- **DiffViewer muestra datos falsos**: "CI: unknown" en todos los jobs. Los diffs nunca se guardan en la tabla `diffs` al aprobar.
- **Approve no muestra resultado**: Tras clickear Approve, el Chat no muestra que paso. El Job cambia de estado en DB pero la UI no lo refleja.
- **No hay persistencia real de sesiones**: sessionStorage se pierde al cambiar de pestana/dispositivo.
- **WebAuthn fantasma**: Codigo existe pero nunca se activo. No hay login biometrico.
- **Guardrails nunca aplicados**: Las reglas de proteccion ERP existen pero nunca bloquean nada.

### Medio
- **OpenCode streaming cableado pero no probado**: bridge.js tiene /run-stream. main.py lo llama. Pero el dummy mode evita que OpenCode real se ejecute.
- **Deploy service existe pero nunca se dispara desde Chat**
- **Agent-to-agent comm muerto**: agent_comm.py tiene 6 tipos de mensajes. 0 sesiones los usan.
- **Gemini falla con system_instruction**: La Interactions API no acepta `system_instruction`. Se hizo workaround con prompt inline.
- **Multi-provider routing falla**: Gemini→OpenRouter fallback es fragil. El codigo esta duplicado en varios lugares.

## 4. Diagnostico raiz

El problema NO es falta de features. Es **falta de integracion**. Construimos:

```
Infraestructura (70% del codigo):
  orchestrator.py, agent_runtime.py, memory.py, skills_seeder.py,
  policies.py, guardrails.py, deploy.py, events.py, audit.py,
  agent_comm.py, openrouter_client.py, gemini_interactions.py,
  webauthn.py, voice.py, langgraph_fsm.py, erp_context.py,
  payment_service.py, template_service.py, tenant_resolver.py
```

```
Lo que realmente se usa (30%):
  chat_commands.py → DB directa + file I/O
  main.py → WebSocket handler
  openrouter_client.py → chat LLM fallback
  gemini_interactions.py → chat LLM principal
```

**El Chat es un thin wrapper que ignora el 70% del codigo construido.**

No hay un solo lugar donde el flujo completo funcione:

```
Usuario: "Crea una landing page"
  → chat_commands.py: crea Job en DB
  → main.py: envia chat_response al WebSocket
  → FIN. Nada mas.
```

Cuando el usuario clickea Approve:
```
  → POST /api/v1/jobs/{id}/approve
  → agent_runtime.plan_change() (dummy: retorna dict simulado)
  → agent_runtime.apply_change() (dummy: no modifica archivos)
  → agent_runtime.generate_diff() (dummy: texto simulado)
  → agent_runtime.run_qa_review() (dummy: passed=True)
  → PostMortem.run() (dummy: leccion dummy)
  → Diff guardado en DB
  → PERO: el DiffViewer no refresca, el Chat no muestra resultado
```

## 5. Plan de refactorizacion

### Principio rector: EXPERIENCE-FIRST, no architecture-first

Cada feature debe ser **visible y funcional en el Chat** antes de escribirse en el backend. El backend existe para servir al Chat, no al reves.

### Fase 1: Hacer que el pipeline basico funcione (1 dia)

1. **Arreglar el approve pipeline para que produzca resultados VISIBLES**:
   - El approve endpoint YA ejecuta plan_change→apply_change→generate_diff→qa_review→PostMortem
   - **Falta**: guardar el diff en la tabla `diffs` con datos reales (no dummy)
   - **Falta**: actualizar el Chat via WebSocket cuando el job cambia de estado
   - **Falta**: el DiffViewer debe cargar los datos reales de la tabla diffs

2. **Conectar el Chat al estado real de los jobs**:
   - Cuando un job se aprueba, enviar `JobStateChanged` via WebSocket
   - El Chat debe mostrar "Job #X aprobado. Diff: [ver]" con link al DiffViewer
   - El Chat debe refrescar automaticamente cuando el estado cambia

### Fase 2: Workspace + contexto (1 dia)

3. **Hacer el workspace configurable y visible**:
   - Variable DOPA_WORKSPACE en .env
   - Mostrar workspace en el mensaje de bienvenida del Chat
   - Permitir cambiarlo desde el tab Sesiones

4. **Activar skills y memoria en el flujo real**:
   - Antes de cada plan_change, consultar `MemoryContext.get_context_for_job()`
   - Inyectar skills relevantes por tags en el prompt del Architect
   - Despues de cada job, ejecutar PostMortem y guardar lecciones

### Fase 3: Agente real con OpenCode (2-3 dias)

5. **Activar el bridge para ejecucion real**:
   - `DOPA_CODE_DUMMY=0` para usar OpenCode real
   - El bridge /run-stream streamea stdout de OpenCode al Chat
   - El Chat muestra "OpenCode ejecutando..." con output en vivo

6. **Loop de agente basico**:
   - Crear un `AgentLoop` que orqueste: task → plan → execute → review → respond
   - El Chat envia el comando, el AgentLoop lo procesa, streamea el progreso

### Fase 4: UI funcional (1 dia)

7. **Arreglar el DiffViewer**:
   - Cargar diffs reales desde la API
   - Mostrar sintaxis coloreada
   - Conectar approve/reject a los endpoints reales

8. **Arreglar el Chat**:
   - Scroll automatico al fondo
   - Botones que no dupliquen acciones
   - Indicadores de progreso (spinner durante ejecucion)
   - Mensajes de error claros

## 6. Que eliminar o posponer

Estas features estan construidas pero no deben activarse hasta que el pipeline basico funcione:

- WebAuthn (posponer — sin pipeline funcional no hay nada que aprobar biometricamente)
- Agent-to-agent communication (posponer — sin agentes reales, no hay comunicacion)
- Deploy service (posponer — sin codigo generado, no hay que desplegar)
- LangGraph FSM (posponer — el FSM simple debe funcionar primero)
- Voice commands (posponer — sin Chat funcional, la voz no aporta)
- ERP context / Payment BYOK (posponer — sin DopaWeb funcionando, no aplica)
- Multi-tenant (posponer — single tenant primero)

## 7. Estructura de archivos a modificar (orden de prioridad)

```
1. backend-inti/inti/api/jobs.py        ← approve pipeline guarda diffs reales
2. backend-inti/inti/api/health.py      ← health endpoint OK
3. backend-inti/inti/chat_commands.py   ← simplificar, conectar a agent_runtime
4. backend-inti/main.py                 ← WebSocket handler limpio y funcional
5. agent-runtime/bridge.js              ← streaming OpenCode output
6. frontend-pwa/src/pages/Chat.tsx      ← chat funcional con scroll y botones
7. frontend-pwa/src/pages/DiffViewer.tsx ← mostrar diffs reales
8. frontend-pwa/src/services/sync.ts    ← sync jobs/diffs de la API
9. backend-inti/inti/agent_runtime.py   ← dummy mode → bridge mode real
10. backend-inti/inti/memory.py         ← conectar PostMortem al pipeline
```

## 8. Metricas de exito

Un refactor es exitoso cuando:

1. Escribo "Crea una landing page" en el Chat → veo el job creado
2. Click Approve → veo progreso (planning... executing... reviewing...)
3. El DiffViewer muestra el diff real del job
4. Puedo ver los jobs en la pestana Jobs con su estado real
5. El Chat recuerda la conversacion al cambiar de pestana
6. Se donde esta el workspace y puedo cambiarlo
7. Los comandos basicos de archivos funcionan (crear, leer, listar)
8. Puedo chatear con el LLM (preguntas, no comandos)
