---
name: dopa-errores-comunes
description: Catalogo de bugs y errores recurrentes en Dopa, con su causa raiz y solucion. Cargar al debuggear o antes de reportar "listo" para no repetirlos.
---

# Errores Comunes en Dopa

## 1. Reportar "verde" sin correr verificacion

**Causa:** El agente asume que vitest verde = todo OK. El CI corre tsc + vitest.
**Solucion:** Siempre `npx tsc --noEmit` + `npm run build` ANTES de reportar.
**Incidentes:** 4 falsos positivos en una sesion (getVoiceMinutesLimit, TENANT_BYPASS_FLAG, AiTool.description, push fantasma).

## 2. `tenantId.field` en lugar de `tenantId`

**Causa:** Payload CMS cambia el API entre versiones. `tenantId.field` era valido en v2.
**Solucion:** Usar `tenantId` directamente. Verificar en el código real, no en docs viejas.

## 3. `force-dynamic` faltante en paginas con DB

**Causa:** Next.js prerenderiza estatico por defecto. Si la pagina consulta DB → ECONNREFUSED en build.
**Solucion:** `export const dynamic = 'force-dynamic'` en layout.tsx de paginas multi-tenant.

## 4. Migraciones no idempotentes

**Causa:** `CREATE TABLE` sin `IF NOT EXISTS`. El entrypoint de Docker reintenta y falla 5 veces.
**Solucion:** Siempre `CREATE TABLE IF NOT EXISTS`. Para enums PG16: `DO $$ BEGIN CREATE TYPE ... EXCEPTION WHEN duplicate_object THEN NULL; END $$`.

## 5. Ramas desde main local obsoleto

**Causa:** `git checkout -b feat/X main` usa el main local, que se desfasa tras squash-merge.
**Solucion:** `git fetch origin && git checkout -b feat/X origin/main`.

## 6. Push fantasma (exit 0 pero no llego a origin)

**Causa:** `git push` retorna exit 0 pero el output no muestra `-> branch_name`.
**Solucion:** Verificar el output completo. Si no aparece la flecha, el push no llego.

## 7. `emailAdapter` fantasma en Payload

**Causa:** `(payload as any).emailAdapter.send()` — el adapter es undefined en versiones recientes.
**Solucion:** Usar `payload.sendEmail()` directo (API oficial de Payload CMS 3).

## 8. `String(tenantId)` type error

**Causa:** `getTenant()` devuelve `string | number`. Payload espera `string`.
**Solucion:** `String(tenantId)` en queries de Payload. No asumir que es string.

## 9. Migraciones con `serial` vs `uuid`

**Causa:** Algunos modelos usan UUIDs. Las migraciones de Payload esperan `serial`.
**Solucion:** IDs siempre `serial` en migraciones de Payload (dopa-sites). `uuid` en Sequelize (dopa-platform).

## 10. `migrate:create` roto con tsx

**Causa:** `node:crypto` no disponible bajo tsx en ciertas versiones.
**Solucion:** Escribir migraciones manualmente siguiendo el patron de las existentes.
