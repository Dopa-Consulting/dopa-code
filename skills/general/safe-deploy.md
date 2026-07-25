# safe_deploy

Deploy a produccion con auditoria de seguridad obligatoria. Adaptado de Hainrixz/all-deploy.

**Origen**: [Hainrixz/all-deploy](https://github.com/Hainrixz/all-deploy) (MIT)
**Tags**: general, deploy, security, audit, universal

## 8 reglas duras

1. **Nunca omitir el audit.** Es la unica puerta entre tu codigo y produccion
2. **Nunca deploy a prod sin preview verde** confirmada con HTTP status real
3. **Nunca exponer secretos** en logs, diffs, ni commits
4. **Nunca auto-instalar ni auto-autenticar CLIs.** El usuario ejecuta `vercel login`, no el agente
5. **Nunca esconder comandos en scripts.** Todo comando es legible y copiable
6. **Nunca modificar codigo sin mostrar el diff primero**
7. **Nunca deploy desde working tree sucio** (salvo permiso explicito)
8. **"Espera" siempre gana.** Cualquier duda antes de prod aborta limpiamente

## Steps

### Fase 0: Prerrequisitos
1. Confirmar que estas en un repo git con remote configurado
2. Verificar que el proyecto tiene start command detectable
3. Si es monorepo, preguntar que paquete desplegar

### Fase 1: Audit (CRITICO - bloquea el deploy)
1. **Secretos**: verificar que no haya .env commiteado ni API keys en archivos trackeados
2. **Lockfile**: verificar que existe package-lock.json, yarn.lock, pnpm-lock.yaml, o bun.lockb
3. **.env.example**: verificar que existe y documenta todas las variables que usa el proyecto
4. **Working tree**: verificar `git status --porcelain` esta limpio
5. **Vulnerabilidades**: correr `npm audit --production` o `pip-audit`
6. **.gitignore**: verificar que existe y cubre node_modules, .env, dist, build

Si algun check critico falla → **el deploy NO continua**. Se muestra el fix como diff y se aprueba antes de seguir.

### Fase 2: Target
1. Detectar el target optimo segun el proyecto:
   - Next.js, Vite, Astro → Vercel
   - FastAPI, Flask, Express → Railway o Docker+VPS
   - Static HTML → Vercel o cloudflared tunnel
2. Si el target detectado no esta disponible, preguntar alternativa
3. Verificar que el CLI del target esta instalado y autenticado

### Fase 3: Preview
1. Entregar variables de entorno al target
2. Desplegar a preview/staging (NUNCA --prod en este paso)
3. Obtener URL de preview

### Fase 4: Health check
1. `curl` a la URL de preview
2. Solo 2xx o 3xx permiten continuar
3. Cualquier otra respuesta → detener y mostrar comando de logs

### Fase 5: Produccion
1. Mostrar resumen de cambios
2. Solicitar confirmacion explicita (o ventana de 5s en modo auto)
3. Promover a produccion

### Fase 6: Handover
1. Verificar que prod responde correctamente
2. Confirmar que las env vars llegaron
3. Entregar comandos de rollback y logs

## Best Practices

### Pre-deploy checklist (para el agente)

Antes de ejecutar cualquier deploy:
```bash
# 1. Secrets check (usa el script de audit)
python scripts/audit.py

# 2. Working tree must be clean
git status --porcelain  # must be empty

# 3. Dependencies audit
npm audit --production --audit-level=high
# o: pip-audit

# 4. Env vars documented
python scripts/env_extract.py  # check .env.example coverage

# 5. Lockfile present
ls package-lock.json yarn.lock pnpm-lock.yaml bun.lockb 2>/dev/null
```

### Rollback commands por target

| Target | Comando |
|--------|---------|
| Vercel | `vercel rollback` |
| Railway | Re-deploy del commit anterior |
| Docker+VPS | `docker tag previous:latest && docker compose up -d` |
| Easypanel | Rollback via API o UI |
| cloudflared | `pkill cloudflared` |

### Reglas adicionales para Dopa Code

- Si el proyecto es DopaWeb, verificar guardrails antes del deploy
- Si el deploy es BYOK payment, verificar credenciales en sandbox primero
- El auto-merge solo ocurre si CI paso + audit paso + preview verde
