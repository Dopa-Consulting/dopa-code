---
name: using-superpowers
description: Punto de entrada para trabajo efectivo con agentes. Establece como encontrar y usar skills, herramientas y memoria. Cargar al inicio de cada sesion.
---

# Using Superpowers — Trabajo Efectivo con Agentes

## Antes de CUALQUIER tarea

1. **Escanea skills disponibles** — `skills_list()` para ver que hay.
2. **Carga skills relevantes** — `skill_view(name)` para lo que coincida con tu tarea.
3. **Revisa la memoria** — Datos persistentes sobre el usuario, entorno, convenciones.
4. **Busca sesiones pasadas** — `session_search(query)` si el topico puede tener historia.

## Al implementar

1. **Lee antes de escribir** — Checkea patrones existentes (ApiVaultPage antes de ApiKeysPage).
2. **Verifica despues de escribir** — tsc + build + tests. Nunca reportes sin correrlos.
3. **Commitea atomicamente** — Un commit por preocupacion. Sin cambios mezclados.
4. **Pushea con verificacion** — Confirma que `git push` muestre `-> branch_name`.

## Al estar trabado

- Errores de herramientas → intenta alternativa antes de preguntar al usuario.
- Informacion faltante → busca en el codigo, docs, o historial de sesiones.
- Bloqueado por dependencia externa → dilo claro con que se necesita.

## Patrones de herramientas

- **Leer archivos:** `read_file` no `cat/head/tail`
- **Buscar codigo:** `search_files` no `grep/find`
- **Editar archivos:** `patch` no `sed/awk`
- **Shell:** `terminal` para builds, git, npm, procesos
- **Web:** `web_search` + `web_extract` para investigacion
