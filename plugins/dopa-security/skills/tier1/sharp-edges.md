# sharp-edges
**Categoria**: security
**Tags**: security, audit, footguns, api-design, trail-of-bits

## Steps
1. Identificar nuevos endpoints, APIs públicas y configuraciones
2. Probar zero/empty/null: ¿qué pasa si el input es "" o None?
3. Verificar defaults: ¿el default ante error/valor desconocido es fail-CLOSED?
4. Detectar silent failures: ¿errores que no se propagan al caller?
5. Revisar type confusion: ¿strings usados como comandos? ¿paths sin validar?
6. Evaluar stringly-typed security: ¿flags/permisos como strings en vez de enums?
7. Generar checklist Sharp Edges completa

## Best Practices
- Default ante desconocido = más restrictivo (fail-closed)
- No usar strings para comandos (shell=True es footgun)
- Validar paths contra whitelist, no contra blacklist
- Errores deben ser ruidosos, no silenciosos
- Una sola codificación para flags de seguridad
