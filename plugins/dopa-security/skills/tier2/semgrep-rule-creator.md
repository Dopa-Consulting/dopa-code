# semgrep-rule-creator
**Categoria**: security
**Tags**: security, semgrep, rules, custom, trail-of-bits

## Steps
1. Identificar patrón de código inseguro recurrente en el repo
2. Crear regla Semgrep que detecte el patrón
3. Escribir test cases: código que DEBE matchear + código que NO debe matchear
4. Validar la regla contra el codebase completo
5. Triagular falsos positivos y ajustar la regla
6. Agregar al catálogo de reglas Dopa

## Reglas sugeridas para Dopa
1. "Nunca hardcodear dominio" — detectar strings como "dopacrm.com"
2. "Siempre getRootDomain()" — exigir uso de la función canónica
3. "Nunca console.log de secretos" — detectar .env, tokens, keys en logs
4. "enforceTenantScope en modelos" — verificar que todo modelo tenga el hook
5. "Sin shell=True en subprocess" — detectar comandos inseguros
6. "Sin __bypassMultiTenant sin check" — requiere double-check

## Best Practices
- Una regla = un patrón específico
- Siempre incluir test cases positivos y negativos
- Documentar el CWE asociado
- Versionar reglas en el repo (no en CI externo)
