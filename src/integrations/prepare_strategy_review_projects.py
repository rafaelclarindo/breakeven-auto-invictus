#!/usr/bin/env python3
"""Prepara a carteira Strategy Review para execução da skill Jefferson."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT / "assets"
PORTFOLIO_DIR = PROJECT / "projects"


def slugify(value: str, fallback: str, *, max_length: int = 72) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    text = text or fallback
    return text[:max_length].rstrip("-") or fallback


def latest_manifest() -> Path:
    manifests = sorted(
        ASSETS_DIR.glob("strategy_review_manifest_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not manifests:
        raise FileNotFoundError(
            "Nenhum manifest encontrado. Rode build_strategy_review_manifest.py primeiro."
        )
    return manifests[0]


def present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def positive_number(value: Any) -> bool:
    try:
        return value is not None and float(value) > 0
    except (TypeError, ValueError):
        return False


def classify_project(project: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if not present(project.get("growthpack_updated_link")):
        reasons.append("Sem GrowthPack Atualizado no Flow.")
    if not positive_number(project.get("fee")):
        reasons.append("Fee ausente ou zerado no Flow.")
    if project.get("media_planned") is None:
        reasons.append("Mídia prevista ausente no Flow.")
    if not positive_number(project.get("margin_pct")):
        reasons.append("Margem de contribuição ausente ou zerada no Flow.")
    if not present(project.get("document_id")):
        reasons.append("Projeto não pareado com documentId do Cockpit.")

    if not present(project.get("growthpack_updated_link")):
        return "blocked", reasons
    if reasons:
        return "needs-review", reasons
    return "ready", ["Insumos Flow mínimos disponíveis."]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_project_status(path: Path, project: dict[str, Any], status: str, reasons: list[str]) -> None:
    lines = [
        f"# Status — {project['name']}",
        "",
        f"**Atualizado:** {date.today().isoformat()}",
        f"**Status:** `{status}`",
        f"**Ordem Strategy Review:** {project['order']}",
        "",
        "## Prontidão",
        "",
    ]
    lines.extend(f"- {reason}" for reason in reasons)
    lines.extend(
        [
            "",
            "## Insumos Flow",
            "",
            f"- Document ID: `{project.get('document_id') or 'pendente'}`",
            f"- Coordenador: `{project.get('coordinator') or 'pendente'}`",
            f"- Fee: `{project.get('fee') if project.get('fee') is not None else 'pendente'}`",
            f"- Mídia prevista: `{project.get('media_planned') if project.get('media_planned') is not None else 'pendente'}`",
            f"- Margem: `{project.get('margin_pct') if project.get('margin_pct') is not None else 'pendente'}`",
            f"- GrowthPack Atualizado: {project.get('growthpack_updated_link') or '`pendente`'}",
            "",
            "## Próximo passo",
            "",
        ]
    )
    if status == "ready":
        lines.append("- Baixar Growth Pack `.xlsx`, inspecionar e montar `config.json` da skill.")
    elif status == "needs-review":
        lines.append("- Conferir pendências acima antes de aprovar geração final.")
    else:
        lines.append("- Completar dados bloqueantes no Flow/Cockpit antes de executar a skill.")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def prepare_project(project: dict[str, Any]) -> dict[str, Any]:
    order = int(project["order"])
    slug = project.get("slug") or slugify(project["name"], f"projeto-{order:02d}")
    folder_name = f"{order:02d}-{slugify(slug, f'projeto-{order:02d}')}"
    project_dir = PORTFOLIO_DIR / folder_name

    for child in ("source", "inspection", "report", "spreadsheet"):
        (project_dir / child).mkdir(parents=True, exist_ok=True)

    status, reasons = classify_project(project)
    project_payload = {
        **project,
        "portfolio_folder": str(project_dir.relative_to(PROJECT)),
        "readiness_status": status,
        "readiness_reasons": reasons,
    }
    write_json(project_dir / "source" / "manifest-entry.json", project_payload)
    write_project_status(project_dir / "status.md", project_payload, status, reasons)

    return {
        "order": order,
        "name": project["name"],
        "slug": folder_name,
        "status": status,
        "reasons": reasons,
        "folder": str(project_dir.relative_to(PROJECT)),
        "has_growthpack_link": present(project.get("growthpack_updated_link")),
        "document_id": project.get("document_id"),
        "coordinator": project.get("coordinator"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cria pastas por projeto e readiness da carteira Strategy Review."
    )
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()

    manifest_path = args.manifest or latest_manifest()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    projects = manifest.get("projects", [])

    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    prepared = [prepare_project(project) for project in projects]

    summary = {
        "source_manifest": str(manifest_path.relative_to(PROJECT)),
        "generated_at": date.today().isoformat(),
        "project_count": len(prepared),
        "ready": sum(1 for p in prepared if p["status"] == "ready"),
        "needs_review": sum(1 for p in prepared if p["status"] == "needs-review"),
        "blocked": sum(1 for p in prepared if p["status"] == "blocked"),
        "projects": prepared,
    }

    today = date.today().isoformat()
    write_json(ASSETS_DIR / f"strategy_review_readiness_{today}.json", summary)
    write_json(PORTFOLIO_DIR / "index.json", summary)

    index_lines = [
        "# Índice — Breakeven Auto",
        "",
        f"**Atualizado:** {today}",
        f"**Manifest:** `{summary['source_manifest']}`",
        "",
        "## Resumo",
        "",
        f"- Projetos: {summary['project_count']}",
        f"- Prontos: {summary['ready']}",
        f"- Precisam de revisão: {summary['needs_review']}",
        f"- Bloqueados: {summary['blocked']}",
        "",
        "## Projetos",
        "",
        "| Ordem | Projeto | Status | Pasta | Motivo principal |",
        "|---:|---|---|---|---|",
    ]
    for project in prepared:
        reason = project["reasons"][0] if project["reasons"] else "-"
        index_lines.append(
            f"| {project['order']} | {project['name']} | `{project['status']}` | "
            f"`{project['folder']}` | {reason} |"
        )
    index_lines.append("")
    (PORTFOLIO_DIR / "index.md").write_text("\n".join(index_lines), encoding="utf-8")

    print(
        "projetos: {project_count} | ready: {ready} | needs-review: "
        "{needs_review} | blocked: {blocked}".format(**summary)
    )
    print(f"index: {PORTFOLIO_DIR / 'index.md'}")


if __name__ == "__main__":
    main()
