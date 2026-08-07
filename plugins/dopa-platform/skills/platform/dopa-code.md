# dopa-code
**Categoria**: platform
**Tags**: dopa, code, agent, inti, tools

## Steps
1. Identificar si el cambio es en el backend (Python/FastAPI) o frontend (React/Vite)
2. Seguir las convenciones: snake_case en Python, camelCase en TypeScript, kebab-case en URLs
3. Usar las tools del agente: read_file, write_file, list_dir, run_command
4. Verificar con tsc --noEmit (frontend) y verificar imports (backend)
5. Si es cambio multi-archivo, delegar a run_opencode

## Best Practices
- No tocar database.py salvo para imports de modelos nuevos
- APIs nuevas: crear en inti/api/, registrar en inti/router.py
- No hardcodear secretos: usar settings.X de inti.config
- Respetar DOPA_ prefix en env vars
- Tool calling: usar formato XML dentro de <tool_calls>
