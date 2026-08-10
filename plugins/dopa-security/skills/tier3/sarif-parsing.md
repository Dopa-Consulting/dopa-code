# sarif-parsing
**Categoria**: security
**Tags**: security, sarif, reporting, static-analysis, trail-of-bits

## Steps
1. Recibir archivos SARIF de CodeQL, Semgrep u otros scanners
2. Parsear y extraer hallazgos: file, line, severity, message, rule
3. Deducplicar hallazgos (mismo file:line:rule entre scanners)
4. Filtrar por severidad: solo críticos y altos para reporte ejecutivo
5. Agregar estadísticas: total, por severidad, por archivo, por regla
6. Generar reporte consolidado en Markdown
7. Integrar con CI para publicar resultados como PR comment

## Best Practices
- No duplicar hallazgos entre scanners
- Incluir contexto: snippet de código alrededor del hallazgo
- Priorizar hallazgos con data flow evidence
- Marcar falsos positivos como "suppressed" con razón
- Vincular hallazgos a CWE cuando sea posible
