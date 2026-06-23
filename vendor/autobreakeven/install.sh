#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$ROOT/breakeven-projetos"
MODE="${1:-}"

case "$MODE" in
  codex)
    TARGET="${CODEX_HOME:-$HOME/.codex}/skills"
    ;;
  claude)
    TARGET="$HOME/.claude/skills"
    ;;
  cursor)
    TARGET="$PWD/.cursor/skills"
    ;;
  custom)
    TARGET="${2:-}"
    if [[ -z "$TARGET" ]]; then
      echo "Uso: ./install.sh custom /caminho/para/skills" >&2
      exit 2
    fi
    ;;
  *)
    echo "Uso: ./install.sh codex|claude|cursor|custom [caminho]" >&2
    exit 2
    ;;
esac

mkdir -p "$TARGET"
rm -rf "$TARGET/breakeven-projetos"
cp -R "$SOURCE" "$TARGET/breakeven-projetos"

echo "Skill instalada em: $TARGET/breakeven-projetos"
