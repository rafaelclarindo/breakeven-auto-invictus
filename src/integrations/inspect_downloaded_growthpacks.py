#!/usr/bin/env python3
"""Executa inspect_growthpack.py para Growth Packs já baixados."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
PORTFOLIO_DIR = PROJECT / "projects"
INSPECTOR = (
    PROJECT
    / "vendor"
    / "autobreakeven"
    / "breakeven-projetos"
    / "scripts"
    / "inspect_growthpack.py"
)


def load_index() -> dict[str, Any]:
    path = PORTFOLIO_DIR / "index.json"
    if not path.exists():
        raise FileNotFoundError(
            "Index não encontrado. Rode prepare_strategy_review_projects.py primeiro."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def selected_projects(index: dict[str, Any], orders: set[int] | None, limit: int | None):
    selected = []
    for project in index.get("projects", []):
        if orders and int(project["order"]) not in orders:
            continue
        selected.append(project)
        if limit and len(selected) >= limit:
            break
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspeciona Growth Packs baixados.")
    parser.add_argument("--orders", default=None, help="Ordens separadas por vírgula.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--rows", type=int, default=80)
    args = parser.parse_args()

    orders = None
    if args.orders:
        orders = {int(item.strip()) for item in args.orders.split(",") if item.strip()}

    results = []
    for project in selected_projects(load_index(), orders, args.limit):
        project_dir = PROJECT / project["folder"]
        growthpack = project_dir / "source" / "growthpack.xlsx"
        output = project_dir / "inspection" / "inspection.json"
        result = {
            "order": project["order"],
            "name": project["name"],
            "folder": project["folder"],
            "input": str(growthpack.relative_to(PROJECT)),
            "output": str(output.relative_to(PROJECT)),
            "status": "pending",
            "message": "",
        }
        if not growthpack.exists():
            result["status"] = "skipped"
            result["message"] = "Growth Pack não baixado."
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(INSPECTOR),
                    str(growthpack),
                    "--rows",
                    str(args.rows),
                    "--output",
                    str(output),
                ],
                cwd=str(INSPECTOR.parent.parent),
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode == 0:
                result["status"] = "inspected"
                result["message"] = "Inspeção gerada."
            else:
                result["status"] = "failed"
                result["message"] = (completed.stderr or completed.stdout).strip()
        results.append(result)
        print(f"{result['order']:02d} {result['status']}: {result['name']} - {result['message']}")

    summary = {
        "generated_at": date.today().isoformat(),
        "selected": len(results),
        "inspected": sum(1 for r in results if r["status"] == "inspected"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }
    out = PROJECT / "assets" / f"growthpack_inspections_{date.today().isoformat()}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"summary: {out}")


if __name__ == "__main__":
    main()
