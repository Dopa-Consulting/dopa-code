# git-cleanup
**Categoria**: operations
**Tags**: git, cleanup, branches, worktrees, trail-of-bits

## Steps
1. Listar branches locales: `git branch`
2. Identificar branches mergeados: `git branch --merged master`
3. Identificar branches squash-mergeados (comparar diff con master)
4. Categorizar: merged / squash-merged / superseded / active
5. Eliminar branches mergeados y squash-mergeados
6. Limpiar worktrees huérfanos: `git worktree list`
7. Sugerir branches activas que pueden estar stale (>30 días sin commit)

## Best Practices
- NUNCA eliminar branches sin confirmar que están mergeados
- Verificar con `git log master..branch` antes de eliminar
- Mantener máximo 5-10 branches activas
- Nombrar branches con prefijo: feature/, fix/, chore/
- Eliminar branches remotas después del merge (PR merge button lo hace)
