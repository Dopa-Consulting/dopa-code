# supply-chain-risk-auditor
**Categoria**: security
**Tags**: security, supply-chain, dependencies, npm, pip, trail-of-bits

## Steps
1. Listar todas las dependencias (npm: package.json, pip: requirements.txt)
2. Auditar cada paquete: ¿mantenido? ¿vulnerabilidades conocidas? ¿typosquatting?
3. Evaluar riesgo: paquetes con pocos maintainers, forks abandonados, nombres sospechosos
4. Revisar transitive dependencies (npm ls --depth=5, pip freeze)
5. Verificar integridad: checksums en lockfiles vs registros
6. Generar reporte con recomendaciones de reemplazo

## Best Practices
- Ejecutar semanalmente (automatizado en CI)
- Pin a SHA para actions de terceros (no a tag movible)
- Congelar dependencias con lockfiles (package-lock.json, requirements.txt con ==)
- Alertar sobre paquetes sin actividad en 6+ meses
- Verificar que no haya dependencias con nombres que imitan paquetes populares
