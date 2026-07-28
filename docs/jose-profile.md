# Perfil de José Castañeda — Fundador de Dopa

## Identidad
- Fundador de Dopa (ecosistema: Dopa Consulting + Dopa SaaS)
- Español neutro LATAM (tú, NUNCA vos)
- Exige UI visible — "si no se ve en pantalla no está entregado"
- Ejecución autónoma sin pausas
- Prefiere Telegram para comunicación rápida, CLI para debug pesado

## Stack técnico personal
- **PC:** i7-4790K + RTX 3060
- **OS:** Windows con WSL (Ubuntu 26.04)
- **Home WSL:** /home/pc-pepe
- **Windows files:** /mnt/c/Users/User/

## Proyectos activos

### Dopa ERP/CRM (dopacrm)
- Backend: Node.js 24 + Express + Sequelize + PostgreSQL
- Frontend: React + MUI
- Deploy: Contabo VPS (62.146.231.22) + EasyPanel + Docker Swarm
- Funcionalidades: facturación SUNAT, POS, inventario, inbox omnicanal, AI agents, BYOK

### Dopa Commerce / Fresh2Go (dopa-commerce, antes fresh2go)
- Stack: Payload CMS 3 + Next.js 16 + PostgreSQL + Redis
- Deploy: EasyPanel en `staging.fresh2go.pe`
- Dominio futuro: `*.dopaweb.com`
- Pipeline: branch → `npm run build` local → push → EasyPanel deploy
- Docker: `npm ci` + lockfile → builds determinísticos
- Multi-tenant: `getTenant()` por hostname, CSS vars dinámicas
- Stripe: 6 price IDs creados (Starter/Pro/Business × mensual/anual)
- Apunta a Cloudflare → EasyPanel

### Dopa Code (dopa-code)
- Entorno de desarrollo agéntico Local-First
- Inti: orquestador Python/FastAPI + AgentLoop con tool-calling
- OpenCode: agente de código vía bridge Bun en :4097
- Frontend: PWA React/Vite + Tailwind + Dexie
- 17 skills con contenido (Anthropic + Obra Superpowers)
- Puerto: backend 8000, bridge 4097, PWA 5173

### Fresh2Go (primer tenant de Dopa Commerce)
- Ecommerce de productos saludables
- Paleta: verde #4A7C59, crema #F7F3E9, naranja #E88D3C

## Preferencias de diseño
- Clean Solid dark (#0B0E11 bg, #E2E8F0 text)
- Gradiente corporativo 90°: #00E9D9 → #6900FF
- Botones: texto blanco sobre gradiente, NUNCA texto oscuro
- Sin glassmorphism, sin emojis en UI, sin sombras de color
- Tipografía: Geist (sans) + Geist Mono
- Sin colores hardcodeados — usar CSS vars
- SED PROHIBIDO en TSX (reescribir archivos, no sed)

## Modelos y herramientas
- **Claude (arquitecto/auditor):** planifica, audita, mergea
- **DeepSeek Pro (yo, Hermes):** ejecución, revisión, implementación
- **DeepSeek Flash:** ejecución rápida, bajo costo
- **Gemini Flash:** QA diario 4x
- Stripe MCP para crear productos
- EasyPanel: 62.146.231.22:3000
- OpenRouter para acceso multi-modelo
- FAL.ai para generación de imágenes (Nano Banana Pro)

## Credenciales y secretos (ubicaciones)
- Stripe keys: ~/.hermes/stripe-key
- APIPERU token: ~/.hermes/apiperu-key
- Deploy token: ~/.hermes/deploy-token
- NUNCA exponer secretos en logs, commits ni respuestas

## Pipeline y reglas
- Branch naming: feat/* para features, fix/* para bugs
- Commits en español, prefijo convencional
- PRs en draft hasta revisión
- `npm run build` local ANTES de push — NUNCA push sin build
- `npx tsc --noEmit` para ver todos los type errors
- Dockerfile con `npm ci` (no `npm install`)
- Lockfile siempre commiteado
- Layout server + StoreBody client (dynamic ssr:false)

## WSL limitaciones
- Sin pip, sin venv, sin pytest (no puedo correr tests Python)
- Docker build lento pero funcional
- Python 3.14.4, Node 24

## Preferencias personales
- Keto diet + gimnasio (88kg)
- QA diario automatizado a las 22:00
- Modelo de costos mínimo para agentes
- Objetivo: emprendedor #500, no solo Fresh2Go
