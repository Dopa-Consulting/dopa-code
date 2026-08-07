---
name: agent-handoff
description: Preparar documentos de contexto para transferir trabajo entre agentes o continuar entre sesiones. Usar al final de sesiones complejas (5+ tool calls) o al pasar trabajo a otro agente.
---

# Agent Handoff

## Cuando crear un handoff

- Despues de una sesion compleja (5+ tool calls)
- Antes de pasar trabajo a otro agente
- Al final de una sesion de desarrollo
- Cuando la ventana de contexto esta por compactarse

## Formato del handoff

```
BRIEF: [nombre del feature]
REPO: [URL de GitHub]
BRANCH: [nombre de branch]

ESTADO:
- Que esta implementado
- Que esta pendiente
- Que esta bloqueado

DECISIONES CLAVE:
- Decision 1 + justificacion
- Decision 2 + justificacion

ARCHIVOS MODIFICADOS:
- ruta/al/archivo.ts — que cambio

VERIFICACION:
- tsc: 0 errores
- vitest: N/N pasando
- build: verde

PROXIMOS PASOS:
- Que debe hacer el siguiente agente
```

## Entrega

Guardar en `~/Downloads/private/BRIEF_*.md` o `HANDOFF_*.md`.
Incluir salidas REALES de comandos, no descripciones.
Link a PRs, commits, y skills relevantes.
