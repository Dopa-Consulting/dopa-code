#!/usr/bin/env bash
# setup-inti-git.sh - Configura git para que Inti aparezca como co-author
# Ejecutar una vez por workspace para activar los hooks de Inti

HOOKS_DIR="$(git rev-parse --git-dir)/hooks"
SCRIPT_DIR="$(dirname "$0")/git-hooks"

echo "[Inti] Configurando git hooks..."

# Instalar prepare-commit-msg hook (agrega Co-authored-by: Inti)
cp "$SCRIPT_DIR/prepare-commit-msg" "$HOOKS_DIR/prepare-commit-msg"
chmod +x "$HOOKS_DIR/prepare-commit-msg"

# Instalar commit-msg hook (prefijo [Inti] en branches de agente)
cp "$SCRIPT_DIR/commit-msg" "$HOOKS_DIR/commit-msg"
chmod +x "$HOOKS_DIR/commit-msg"

# Instalar post-commit hook
cp "$SCRIPT_DIR/post-commit" "$HOOKS_DIR/post-commit"
chmod +x "$HOOKS_DIR/post-commit"

# Configurar alias de git para commits de Inti
git config alias.inti '!git commit -m "[Inti] $1" --trailer "Co-authored-by: Inti <inti@dopa.solutions>"'

echo "[Inti] Hooks instalados. Cada commit en branches intl/* llevara co-autoria de Inti."
echo "[Inti] Usa 'git inti \"mensaje\"' para commits directos con co-autoria."
echo ""
echo "Para que Inti tenga foto de perfil en GitHub:"
echo "  1. Crea cuenta en GitHub: inti@dopa.solutions"
echo "  2. Sube public/inti-logo.svg como avatar"
echo "  3. Los commits de Inti mostraran el logo del sol andino"
