# fix-and-verify
**Categoria**: methodology
**Tags**: methodology, debugging, testing, verification

## Steps
1. Reproducir el bug con un test que falle
2. Identificar la causa raiz (no el sintoma)
3. Aplicar el fix minimo necesario
4. Verificar que el test ahora pasa
5. Verificar que no hay regresiones (correr suite completa)
6. Documentar el fix y la causa raiz

## Best Practices
- Un fix = un commit
- Siempre agregar test que cubra el bug
- No hacer refactors junto con el fix
- Si el fix es temporal, marcarlo con TODO y crear issue
