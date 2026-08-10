# semgrep
**Categoria**: security
**Tags**: security, static-analysis, semgrep, ci, trail-of-bits

## Steps
1. Configurar Semgrep con reglas extendidas (security + custom Dopa)
2. Ejecutar escaneo sobre el diff del PR con subagentes paralelos
3. Procesar resultados: filtrar por severidad y confianza
4. Crear issues automáticos para hallazgos de alta confianza
5. Integrar en CI: ejecutar en cada PR antes del merge
6. Mantener catálogo de reglas Dopa actualizado

## Best Practices
- Dos modos: "run all" (cobertura total) y "important only" (alta confianza)
- Usar Semgrep Pro para cross-file taint analysis
- Crear reglas específicas para patrones de Dopa
- No ignorar hallazgos por "baja severidad" — revisar manualmente
- Integrar con sarif-parsing para reportes consolidados
