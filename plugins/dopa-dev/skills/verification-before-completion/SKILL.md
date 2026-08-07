---
name: verification-before-completion
description: Usar antes de reportar cualquier trabajo como completo. Paso de verificacion obligatorio: correr tsc, build, y tests reales antes de decir "listo".
---

# Verification Before Completion

## LA REGLA

**Nunca reportes "listo" sin correr el comando de verificacion real.**

Tres veces los agentes reportaron "verde/build paso/tests OK" sin ejecutarlos. Este skill existe para prevenirlo.

## Checklist de verificacion por proyecto

### DopaCRM (backend)
```bash
npx tsc --noEmit          # TypeScript — el CI corre esto
npx vitest run            # Tests — TODOS, no solo tu archivo
```

### DopaCRM (frontend)
```bash
npx tsc --noEmit
npm run build             # Vite build — atrapa errores que tsc no ve
```

### Dopa Web (dopa-sites)
```bash
npm run build             # Next.js build — atrapa errores de runtime/DB
```

### Dopa Code (Inti)
```bash
cd backend-inti && venv/Scripts/python -c "from inti.database import Base; print(len(Base.metadata.tables))"
cd frontend-pwa && npx tsc --noEmit
```

## Red flags que significan VERIFICA DE NUEVO

- "Deberia funcionar" — No. Correlo.
- "Ya lo probe local" — Correlo con el comando del CI.
- "Es solo un cambio chico" — Cambios chicos causaron 3 de los incidentes.
- "vitest paso, debe estar bien" — vitest ≠ tsc. El CI corre ambos.

## Formato de reporte

No digas "los tests pasan". Mostra la salida REAL:

```
$ npx vitest run
Test Files  5 passed (5)
Tests  23 passed (23)
```
