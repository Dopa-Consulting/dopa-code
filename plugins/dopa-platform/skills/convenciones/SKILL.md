---
name: dopa-convenciones
description: Convenciones de codigo, nomenclatura y reglas criticas que aplican en TODOS los repos Dopa. Violarlas bloquea el merge.
---

# Convenciones Dopa

## Nombres

- **Backend (Node/Express):** camelCase para variables, PascalCase para modelos Sequelize.
- **Frontend (React):** PascalCase para componentes, camelCase para hooks y utilidades.
- **Python (Inti):** snake_case para todo. `from inti.X import Y`.
- **Commits:** espanol, prefijo convencional (`feat`, `fix`, `test`, `chore`, `docs`).

## Reglas criticas

1. **NUNCA hardcodear dominios.** Usar `getRootDomain()` en dopa-sites, `ROOT_DOMAIN` env var.
2. **NUNCA pushear secretos.** `.env` esta gitignored. Usar variables de entorno.
3. **NUNCA reportar "listo" sin build.** `npm run build` o `npx tsc --noEmit` obligatorio.
4. **NUNCA usar main local.** Siempre `git fetch origin && git rebase origin/main`.
5. **Dopa-code es repo PUBLICO.** No pushear perfiles, IPs, credenciales ni datos sensibles.

## Espanol

- Neutro LATAM (tu, no vos). "Crea", "Factura", "Empieza" — nunca "Crea", "Factura", "Empeza".
- Commits, mensajes de error, y UI visible en espanol.
- Codigo (variables, funciones) en ingles.

## Migraciones

- **dopa-platform:** Sequelize-CLI, raw SQL idempotente (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`).
- **dopa-sites:** Manuales, orden alfabetico, IDs `serial` (nunca uuid), `IF NOT EXISTS` + `DO $$` blocks para enums PG16.

## Multi-tenant

- `tenantId` en TODA query. Sin excepciones.
- El middleware resuelve tenant por hostname (`x-tenant-id` header).
- Sin datos compartidos entre tenants.
