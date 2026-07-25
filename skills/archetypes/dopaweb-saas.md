# DopaWeb / SaaS Blueprint

Arquetipo por defecto para proyectos en el ecosistema Dopa.

## Stack por defecto

| Capa | Tecnologia | Version |
|------|-----------|---------|
| Frontend | Next.js + React + Tailwind | Latest |
| Backend | Express + Sequelize + PostgreSQL | Node 24 |
| Auth | JWT + WebAuthn (via Dopa) | - |
| Pagos | MercadoPago nativo + BYOK | API v2 |
| Hosting | Easypanel (via Dopa Code) | - |
| CI/CD | GitHub Actions + n8n | - |

## Estructura de directorios

```
project/
├── frontend/           # Next.js app
│   ├── src/
│   │   ├── components/ # Componentes reutilizables
│   │   ├── pages/      # Rutas
│   │   ├── hooks/      # useAuth, useCart, useCheckout
│   │   ├── integrations/
│   │   │   └── erp/    # Cliente ERP (NO MODIFICAR)
│   │   └── styles/     # Tailwind + tokens
│   └── public/
├── backend/            # Express API
│   ├── src/
│   │   ├── models/     # Sequelize models
│   │   ├── routes/     # API endpoints
│   │   └── services/   # Logica de negocio
│   └── migrations/
└── docs/               # Documentacion
```

## Build Order

1. Setup del proyecto (frontend + backend)
2. Modelo de datos + migraciones
3. Auth (registro, login, roles)
4. API core (CRUD basico)
5. Frontend basico (layout + navegacion)
6. Integracion ERP (facturacion, productos)
7. Checkout + pagos
8. Dashboard admin
9. Tests + CI/CD
10. Deploy staging → prod

## Guardrails activos

- `src/integrations/erp/`: NO MODIFICAR
- `src/hooks/useCheckout.ts`: NO MODIFICAR
- `src/lib/facturacion/`: NO MODIFICAR
- Facturacion SUNAT: intocable sin doble aprobacion
