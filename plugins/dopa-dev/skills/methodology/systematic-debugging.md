# systematic-debugging
**Categoria**: methodology
**Tags**: methodology, debugging, troubleshooting

## Steps
1. Definir el comportamiento esperado vs observado
2. Aislar el problema (binary search en commits/componentes)
3. Agregar logs estrategicos, no logs por todos lados
4. Identificar la condicion exacta que causa el fallo
5. Corregir y validar
6. Agregar guard clause para prevenir recurrencia

## Best Practices
- Leer los logs antes de agregar mas
- Usar git bisect para encontrar commits problematicos
- Reproducir en ambiente aislado primero
- No asumir — verificar cada hipotesis con datos
