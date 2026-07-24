# n8n Workflows para Dopa Code

Workflows de automatizacion que corren en n8n (VPS) para orquestar CI/CD entre GitHub, Inti y Easypanel.

## Workflow 1: CI → Auto-merge → Deploy

```
[GitHub Webhook] CI completado
    │
    ▼
[IF] status == "success"
    │ YES
    ▼
[HTTP] POST /api/v1/ci-webhook → Inti
    │ body: { job_id, status: "passed", provider: "github_actions", run_id }
    │
    ▼
[IF] Inti responde { auto_merge: true }
    │ YES
    ▼
[GitHub API] Merge PR
    │
    ▼
[HTTP] POST /api/v1/deploy → Inti → Easypanel
    │
    ▼
[WAIT] 30s
    │
    ▼
[HTTP] GET https://dopa-code.local/health
    │
    ├── 200 → [Slack/Email] "Deployed OK"
    └── !200 → [Easypanel API] Rollback → [Slack] "Deploy failed, rolled back"
```

## Workflow 2: PR Abierto → Notificar PWA

```
[GitHub Webhook] PR opened
    │
    ▼
[HTTP] POST /api/v1/ci-webhook → Inti
    │ body: { job_id, status: "running", provider: "github_actions" }
    │
    ▼
[WebSocket] Inti emite CiStatusUpdated → PWA muestra "CI: Running"
```

## Workflow 3: Health Check → Auto-shutdown

```
[Cron] Cada 5 min
    │
    ▼
[HTTP] GET https://dopa-code.local/health
    │
    ├── 200 → [NOOP]
    └── !200 (x3 consecutivos)
         │
         ▼
    [HTTP] POST /api/v1/shutdown → Inti
         │
         ▼
    [WAIT] 90s
         │
         ▼
    [HTTP] POST https://smart-plug-api/off
         │
         ▼
    [Slack] "PC apagada por inactividad"
```

## Variables de entorno en n8n

```json
{
  "INTI_URL": "https://dopa-code.local:8000",
  "GITHUB_TOKEN": "ghp_...",
  "EASYPANEL_TOKEN": "eyJ...",
  "SMART_PLUG_API": "https://smart-plug.local",
  "SLACK_WEBHOOK": "https://hooks.slack.com/..."
}
```

## Importar en n8n

1. n8n → Settings → Import Workflow
2. Pegar el JSON del workflow correspondiente
3. Configurar credenciales (GitHub, HTTP Request nodes)
4. Activar el workflow
