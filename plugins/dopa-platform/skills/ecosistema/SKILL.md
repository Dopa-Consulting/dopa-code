---
name: dopa-ecosistema
description: Mapa completo del ecosistema Dopa: repos, tecnologia, dominios. Cargar al inicio de cualquier tarea Dopa para entender el contexto.
---

# Ecosistema Dopa

## Repositorios

| Repo | Carpeta local | Stack | Proposito |
|---|---|---|---|
| `dopa-platform` | `~/dopacrm/` | Node 24 + Express + Sequelize + Postgres | ERP + CRM agentivo |
| `dopa-sites` | `~/dopa-sites/` | Payload CMS 3 + Next.js 16 + Postgres 16 | Storefronts multi-tenant |
| `dopa-code` | `~/dopa-code/` | Python/FastAPI + React/Vite + SQLite | Entorno de desarrollo agentivo (Inti) |

## Dominios

```
Dopa Platform
├── DopaCRM (ERP + CRM agentivo)       → ~/dopacrm/
├── Dopa Sites (builder multi-tenant)   → ~/dopa-sites/
│   └── Fresh2go (tenant demo: ecommerce saludable)
└── Dopa Code / Inti (agentes + tools) → ~/dopa-code/
```

## Fundador

Jose Castaneda. Backend/infra. Rol: decisiones de producto, aprueba merges.
