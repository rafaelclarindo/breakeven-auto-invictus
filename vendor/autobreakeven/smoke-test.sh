#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$ROOT/breakeven-projetos"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 "$SKILL/scripts/validate_config.py" \
  "$SKILL/assets/config-exemplo-dalpack.json"

python3 "$SKILL/scripts/generate_report.py" \
  --config "$SKILL/assets/config-exemplo-dalpack.json" \
  --output "$TMP/analise.md"

python3 "$SKILL/scripts/generate_breakeven.py" \
  --config "$SKILL/assets/config-exemplo-dalpack.json" \
  --output "$TMP/breakeven.xlsx"

python3 - "$TMP/breakeven.xlsx" <<'PY'
import sys
import zipfile

path = sys.argv[1]
errors = ["#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A"]
with zipfile.ZipFile(path) as archive:
    archive.testzip()
    xml = "".join(
        archive.read(name).decode("utf-8", "ignore")
        for name in archive.namelist()
        if name.endswith(".xml")
    )
found = {error: xml.count(error) for error in errors}
if any(found.values()):
    raise SystemExit(f"Erros de fórmula encontrados: {found}")
print(f"OK: planilha válida, erros={found}")
PY

test -s "$TMP/analise.md"
test -s "$TMP/breakeven.xlsx"
echo "OK: smoke test concluído"
