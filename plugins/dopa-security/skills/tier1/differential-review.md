# differential-review
**Categoria**: security
**Tags**: security, audit, pr-review, trail-of-bits

## Steps
1. Analizar el diff del PR: `git diff origin/master...HEAD`
2. Identificar archivos modificados y su propósito
3. Contrastar contra patrones seguros existentes en el repo (grep por helpers canónicos)
4. Verificar: ¿el código nuevo usa los patrones seguros que el equipo ya adoptó?
5. Evaluar blast radius: ¿qué otros módulos/datos toca este cambio?
6. Revisar cobertura de tests del código cambiado
7. Generar reporte con hallazgos por severidad (crítico/alto/medio/bajo)

## Best Practices
- Triage por RIESGO, no por tamaño (Heartbleed = 2 líneas)
- Todo fix de seguridad ship con test que falla si se revierte
- Contrastar diff contra patrones atómicos ya probados en el repo
- Buscar regresiones: "código nuevo que NO usa el patrón seguro existente"
- Verificar que no se hayan perdido casos al sobrescribir archivos
