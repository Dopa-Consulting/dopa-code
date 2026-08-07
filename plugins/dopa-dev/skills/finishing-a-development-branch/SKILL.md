---
name: finishing-a-development-branch
description: Usar cuando la implementacion esta completa, los tests pasan, y es hora de preparar el PR. Cubre git workflow, higiene de commits, y creacion de PR.
---

# Finishing a Development Branch

## Antes del PR

1. **Rebasear sobre origin/main FRESCO** — NUNCA usar main local obsoleto.
   ```bash
   git fetch origin
   git rebase origin/main
   ```
2. **Squashear commits WIP** — No dejar "wip", "fix", "test" sueltos.
   Dejar 1-3 commits significativos con prefijos convencionales.
3. **Correr verificacion** (ver skill verification-before-completion).
4. **Revisar diff** — `git diff origin/main...HEAD --stat` debe mostrar SOLO tus archivos.

## Convenciones de commits

- `feat(scope): que` — Nuevo feature
- `fix(scope): que` — Bug fix
- `test(scope): que` — Solo tests
- `chore(scope): que` — Build/tooling
- `docs(scope): que` — Documentacion

Commits en espanol, concisos, que + por que.

## PR

```bash
gh pr create --base main --title "feat: ..." --body "..."
```
- Draft PR (NO mergear sin revision).
- Body: que cambio, como verificarlo, decisiones fuera del brief.
- Link al brief en el body.

## Push

Verificar que `git push` muestra `-> nombre-branch` en el output. Si no aparece esa linea, el push no llego a origin.
