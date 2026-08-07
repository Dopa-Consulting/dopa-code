---
name: dopa-arquitectura
description: Decisiones de arquitectura cerradas que no se reabren sin aprobacion. Cargar antes de disenar o modificar features en cualquier repo Dopa.
---

# Arquitectura Dopa — Decisiones Cerradas

## Reabrir solo con aprobacion de Jose

1. **Multi-tenant disenado-no-activado.** tenantId en TODA query. El dia que se active, es solo remover el flag.
2. **Dopa = fuente de verdad.** Stock, fidelizacion, cliente. Integracion solo por API + webhooks.
3. **Cero hardcodes fiscales.** El pais, moneda, impuestos vienen de config, no del codigo.
4. **Resiliencia.** Ninguna pagina depende de Dopa arriba. Timeout ~800ms, degrada con datos locales.
5. **Pricing en PEN.** Precios en soles peruanos para el mercado LATAM.

## Dopa Sites — multi-tenant

- `getRootDomain()` en `lib/tenant/config.ts` es la fuente unica de verdad.
- Middleware extrae subdominio: `midominio.dopasites.com` → `x-tenant-id: midominio`.
- `ROOT_DOMAIN=''` en dev local desactiva multi-tenant.
- Cada tenant tiene su propio tenantId. Datos aislados.

## DopaCRM — backend

- Express + Sequelize-typescript. Node 24. Postgres.
- Migraciones: raw SQL via `queryInterface.sequelize.query()`.
- Auth: JWT (usuarios) + API Keys (MCP/API externa). Middleware `apiKeyAuth`.
- RBAC: `requirePermission('permiso')`. No roles hardcodeados.
- `enforceTenantScope` en todos los modelos multi-tenant.
- Vault: `TenantCredential` con cifrado AES-256 para secretos.

## DopaCRM — frontend

- React v19 + Vite 7 + MUI v7 + Zustand.
- `axios.ts` como unico cliente HTTP.
- `SectionHeader`, `ConfirmDialog` — componentes reutilizables en `components/ui/`.
- Routes lazy-loaded via `React.lazy()` en `App.tsx`.
- Settings navegacion en `SettingsHubPage.tsx`.

## MCP Server (#879)

- Endpoint `POST /api/mcp-server`. JSON-RPC 2.0.
- Auth: API Key en header `Authorization: Bearer dk_live_xxx`.
- 13 tools en allowlist (sin finanzas, sin Google compliance).
- Rate limit: 20 req/min por IP.
- Scopes enforzados por tool (-32002 si falta el scope).
