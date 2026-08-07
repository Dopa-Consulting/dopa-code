---
name: dispatching-parallel-agents
description: Usar cuando hay 2+ tareas independientes que pueden trabajarse simultaneamente. Paraleliza trabajo via delegate_task para flujos independientes.
---

# Dispatching Parallel Agents

## Cuando paralelizar

Las tareas son independientes si:
- Tocan archivos/repos diferentes
- Ninguna depende del output de la otra
- Se pueden verificar independientemente

## Como

```python
# Python (Inti)
tasks = [
    {"goal": "Agregar calculo de descuento al modelo Sale", "context": "..."},
    {"goal": "Agregar generacion de PDF de factura", "context": "..."},
]
delegate_task(tasks=tasks)  # Ambas corren en paralelo
```

## Anti-patrones

- ❌ Dos agentes editando el mismo archivo
- ❌ Agente B necesita el output del Agente A
- ❌ Ambos agentes necesitan la misma migracion de DB (race condition)

## Buenas practicas

- Cada agente en su propio git worktree o branch separada
- El contexto debe ser AUTO-CONTENIDO (los agentes no tienen memoria de tu conversacion)
- Verifica el output de cada agente independientemente antes de mergear
