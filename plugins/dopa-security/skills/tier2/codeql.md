# codeql
**Categoria**: security
**Tags**: security, static-analysis, codeql, data-flow, trail-of-bits

## Steps
1. Configurar CodeQL database para el proyecto (Python + TypeScript)
2. Ejecutar security-and-quality query suite
3. Ejecutar security-experimental suite para patrones avanzados
4. Revisar resultados de data flow y taint tracking
5. Priorizar hallazgos: críticos primero, luego altos
6. Generar SARIF output para procesamiento posterior
7. Triagular falsos positivos con trailmark-finding-triage

## Best Practices
- Correr ambas suites: security-and-quality + security-experimental
- Usar data extension models para APIs propias (ORM, wrappers)
- No ignorar hallazgos "informational" — a veces esconden bugs reales
- SARIF output para integración con sarif-parsing skill
- Re-correr después de cada cambio significativo de código
