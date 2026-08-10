# insecure-defaults
**Categoria**: security
**Tags**: security, auth, defaults, fail-open, trail-of-bits

## Steps
1. Auditar sistema de auth: ¿SKIP_AUTH se activa con default inseguro?
2. Revisar RBAC/permisos: ¿permisos que defaultean a true?
3. Detectar fail-open: "si no hay key, permitir", try/catch que hace next()
4. Verificar toggles de prod: ¿gateados por NODE_ENV/env flag, no por dato del tenant?
5. Revisar modos de seguridad: ¿el default ante valor desconocido es restrictivo?
6. Buscar bypasses: ¿Symbol vs string? ¿doble encoding de flags?

## Best Practices
- Default ante lo desconocido = fail-CLOSED
- Toggles de producción NUNCA dependen de datos del tenant
- Mocks/bypasses solo en desarrollo (NODE_ENV gate)
- Una sola codificación para flags (no string Y symbol)
- Validar VALOR, no solo presencia de campos de seguridad
