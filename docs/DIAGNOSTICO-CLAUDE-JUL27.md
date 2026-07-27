# Diagnostico Dopa Code — Julio 27, 2026

## Claude, necesito tu ayuda con esto.

### Contexto

Acabo de mergear 5 PRs que creaste con el AgentLoop (slices 1-5). El nuevo core `agent_loop.py` (512 lineas) reemplaza `chat_commands.py` y `agent_runtime.py`. El flujo ahora es:

```
Chat (PWA) → WebSocket → AgentLoop.run() → OpenRouter (tool-calling)
                  │
                  ├── read_file, write_file, list_dir, run_command, git_diff
                  ├── run_opencode (delega a bridge :4097)
                  └── recall_memory (MemoryContext)
```

El AgentLoop usa tool-calling de OpenRouter. Cuando `require_approval=True`, crea un checkpoint (Job+Diff en DB) para que el humano apruebe.

### Lo que SI funciona

- El AgentLoop responde conversacionalmente ("Hola" → "¡Hola! Soy Inti...")
- Las herramientas funcionan (list_dir, write_file, read_file)
- El bridge OpenCode esta corriendo en :4097
- La autenticacion basica (token `intl-sun-2026`) protege las rutas
- Ngrok tunnel funciona para acceso movil
- 10/11 tests del AgentLoop pasan (1 falla por `sleep` de Unix en Windows)

### Bugs criticos que necesitan tu atencion

**Bug 1: AgentLoop sin memoria (CRITICO)**
Cada mensaje del Chat crea un NUEVO AgentLoop. No hay historial de conversacion. Inti responde a "¿en qué carpeta está?" como si fuera la primera vez que habla con el usuario.

- Archivo: `backend-inti/main.py` lineas 115-120
- Causa: `loop = AgentLoop(...)` se crea fresco cada mensaje
- El `history` param de `run()` nunca se usa

**Bug 2: Auth middleware bloquea las API calls del frontend (CRITICO)**
La PWA no puede cargar jobs porque el auth middleware (`main.py` lineas 88-97) devuelve 401. El frontend no envia el token en los headers/cookies de sus fetch calls.

- `GET /api/v1/jobs/` → 401 Unauthorized
- `GET /api/v1/sessions/` → 401 Unauthorized
- Todos los endpoints protegidos fallan desde el frontend

**Bug 3: Login flash en refresh (MEDIUM)**
Al refrescar la pagina, aparece la pantalla de login por un segundo antes de redirigir al Chat. El `LoginGate` verifica el token almacenado y hace una llamada async - durante ese momento muestra el login.

**Bug 4: Chat no envia require_approval correctamente (MEDIUM)**
El Chat.tsx detecta verbos de accion y pone `require_approval=true`, pero el AgentLoop con `require_approval=True` llama a `_create_checkpoint()` que requiere `git add -A` y `git diff --cached` con cambios reales. Si el LLM no uso herramientas, no hay diff y `_create_checkpoint` retorna None (sin checkpoint). El sistema cae a chat_response normal sin approve/reject.

### Lo que necesito que hagas

1. **Arreglar el auth middleware** para que las API calls del frontend funcionen (el token `intl-sun-2026` esta en cookie o header)

2. **Agregar historial de conversacion** al AgentLoop. Que `main.py` pase el historial de mensajes cuando llame a `loop.run()`.

3. **Arreglar el login flash** - que no muestre la pantalla de login durante la verificacion del token.

4. **Hacer que require_approval funcione** incluso cuando no hay cambios en git - que al menos cree el Job y muestre el resultado.

### Archivos clave

```
backend-inti/main.py              — auth middleware + WebSocket handler
backend-inti/inti/agent_loop.py   — AgentLoop core
frontend-pwa/src/pages/Chat.tsx   — Chat UI + WebSocket
frontend-pwa/src/components/Layout.tsx — LoginGate + Layout
frontend-pwa/src/services/sync.ts — API calls (jobs, diffs, sync)
```

### Commits recientes

```
c7ad6ca feat: Chat envia require_approval=true para comandos de tarea
16b816c merge: AgentLoop slices 1-5
e919dd1 feat(agent): checkpoint humano approve=commit/reject=discard
b77b524 feat(agent): guardrails gate + recall_memory tool
9361724 feat(agent): run_opencode como tool del loop
cbfe8b4 fix(config): extra=ignore
c967fc8 feat(agent): AgentLoop núcleo con tool-calling
```
