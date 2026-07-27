---
name: backend-refactor
description: Refactorizar código backend de Dopa Web (Next.js + Payload CMS + PostgreSQL). Usar cuando se necesita reorganizar, optimizar o modernizar el backend sin romper funcionalidad.
---

# Refactorizar Backend

Guía para modificar el backend de Dopa Web manteniendo compatibilidad.

## Stack

- **Runtime**: Next.js 16 (Turbopack / Webpack)
- **CMS**: Payload CMS 3 + PostgreSQL + Drizzle
- **Cache**: Redis (cart, rate-limit)
- **Deploy**: Docker + EasyPanel (Contabo)

## Pipeline

```
branch → npm run build local → push → EasyPanel deploy
```

Reglas del pipeline:
1. `npm ci` (NO `npm install`) — builds determinísticos
2. Lockfile SIEMPRE commiteado
3. `npx tsc --noEmit` para ver TODOS los type errors
4. NUNCA push si el build falla

## Reproducir Docker local

```bash
docker run --rm -v "$PWD:/app" -v fresh2go_nm:/app/node_modules \
  -w /app node:22-slim bash -c "npm ci && npx tsc --noEmit"
```

## Errores comunes

### `Module not found: @payload-config`
- Asegurar que `tsconfig.json` tiene `paths: { "@payload-config": ["./src/payload.config.ts"] }`

### `Property 'X' does not exist on type 'Y'`
- Colecciones no registradas en tipos: usar `as any`
- `description` es Lexical object (no string)
- `images` es `StorefrontImage[]` (array, no string)

### `new Stripe()` rompe build
- SIEMPRE lazy init dentro del handler

### Lockfile drift
- Dockerfile usa `npm ci` (no `npm install`)
- Si `@aws-sdk/checksums` no existe, regenerar lockfile en Linux:
  ```bash
  docker run --rm -v "$PWD:/app" -w /app node:22-slim bash -c "rm -rf node_modules package-lock.json && npm install"
  ```

## Guardrails

- Colecciones Payload sin tipo → `as any` en queries
- No modificar `payload-types.ts` (se regenera)
- Migraciones en `src/migrations/`
- `tenantId` en TODA query
