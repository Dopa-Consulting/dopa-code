# safe-deploy
**Categoria**: methodology
**Tags**: methodology, deploy, safety, ci-cd

## Steps
1. Verificar que el working tree esta limpio (git status)
2. Ejecutar tests localmente
3. Crear PR con descripcion clara
4. Esperar CI verde
5. Merge y verificar deploy

## Best Practices
- Nunca deployar a produccion un viernes
- Siempre tener rollback plan
- Verificar .env y secretos antes de deployar
- Usar feature flags para cambios grandes
