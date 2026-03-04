#!/usr/bin/env bash
# Run once after cloning to activate git hooks.
# Usage: bash scripts/install_hooks.sh

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_SRC="$REPO_ROOT/.githooks"
HOOKS_DST="$REPO_ROOT/.git/hooks"

echo "[hooks] Installing git hooks..."

for hook in pre-commit pre-push; do
  src="$HOOKS_SRC/$hook"
  dst="$HOOKS_DST/$hook"

  if [ ! -f "$src" ]; then
    echo "  [SKIP] $hook (source not found)"
    continue
  fi

  cp "$src" "$dst"
  chmod +x "$dst"
  echo "  [ OK ] $hook -> .git/hooks/$hook"
done

# Point git to .githooks directory (git 2.9+, works for current user)
git config core.hooksPath .githooks
echo ""
echo "[hooks] Done. Hooks will run on: commit, push."
echo "        Requires: python3 + python-frontmatter"
echo "        Install:  pip3 install python-frontmatter"
