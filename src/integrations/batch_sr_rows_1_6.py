#!/usr/bin/env python3
"""Detecta perfil GP e gera breakeven para SR linhas 1-6."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
INTEGRATIONS = Path(__file__).resolve().parent
sys.path.insert(0, str(INTEGRATIONS))

from build_growthpack_inside_sales_config import GP_PROFILES, read_funnel_months, read_investment_months, resolve_growthpack_sheet_name
from growthpack_sheets_reader import open_growthpack_worksheet
from strategy_review_fields import apply_sr_fields_to_manifest

GENERATE = (
    PROJECT
    / "vendor"
    / "autobreakeven"
    / "breakeven-projetos"
    / "scripts"
    / "generate_breakeven.py"
)
UPLOAD = INTEGRATIONS / "upload_xlsx_to_google_sheet.py"
BUILD = INTEGRATIONS / "build_growthpack_inside_sales_config.py"
REF = "2026-06-22"

BATCH = [
    {
        "sr_row": 1,
        "folder": "projects/20-construtora-e-incorporadora-vilela-campos-ltda",
        "gp_id": "18ppHnsXmPjVvNYZopPDDqvxBiSajPy6SlBzvTUAjO2U",
    },
    {
        "sr_row": 2,
        "folder": "projects/21-maidpad-assessoria-byline-maidpad",
        "gp_id": "1UQ4tS029w_DJDPGAbvEtjficQiX0Z8gtJ8Z6y9D-SOc",
    },
    {
        "sr_row": 3,
        "folder": "projects/22-instituto-panamericano-de-oftalmologia-ltda-instituto-panamericano-de-of",
        "gp_id": "1YbnWKqE_yu8x5r7i-Ceu6GMGuyVePB56h-JyDX_T9ak",
    },
    {
        "sr_row": 4,
        "folder": "projects/04-sigo-erp-duo3-solucoes-em-tecnologia-da-informacao-ltda-duo3-solucoes-em",
        "gp_id": "1FBLPH61TCcUui5azwMZS6QFVq_tRI5dtnMrHgFlg2aY",
        "profile": "sigo",
    },
    {
        "sr_row": 5,
        "folder": "projects/23-escritorio-vicentini-andrade-sociedade-de-advogados-s-s-18-213-376-0001",
        "gp_id": "1uzTSmnC-9yrNvp2td26fw_5zafMXP5QuAkPwh-spJ3U",
    },
    {
        "sr_row": 6,
        "folder": "projects/24-malbork-corretora-de-seguros-ltda",
        "gp_id": "1UypffQrX2-FgPgqrPA3rbOTvhrA4HlyBa2inoEYnIVQ",
    },
]


def patch_manifest(project_dir: Path, gp_id: str, *, sr_row: int) -> None:
    manifest_path = project_dir / "source" / "manifest-entry.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["growthpack_updated_link"] = (
        f"https://docs.google.com/spreadsheets/d/{gp_id}/edit"
    )
    apply_sr_fields_to_manifest(manifest, sr_row)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def detect_profile(project_dir: Path) -> tuple[str, int, int]:
    best: tuple[str, int, int] | None = None
    errors: list[str] = []
    for name, profile in GP_PROFILES.items():
        try:
            sheet_name = resolve_growthpack_sheet_name(project_dir, profile)
            ws, _ = open_growthpack_worksheet(project_dir, sheet_name, source="online")
            funnel = read_funnel_months(ws, profile)
            invest = read_investment_months(ws, profile)
            if funnel and invest:
                score = len(funnel) * 100 + len(invest)
                if best is None or score > best[1]:
                    best = (name, score, len(funnel))
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    if not best:
        raise RuntimeError("Nenhum perfil GP funcionou.\n" + "\n".join(errors[:8]))
    return best[0], best[1], best[2]


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=PROJECT)


def process_one(item: dict) -> dict:
    project_dir = PROJECT / item["folder"]
    print(f"\n{'=' * 60}\nSR {item['sr_row']} — {project_dir.name}\n{'=' * 60}")
    patch_manifest(project_dir, item["gp_id"], sr_row=item["sr_row"])
    if item.get("profile"):
        profile = item["profile"]
        _, score, months = detect_profile(project_dir)
        print(f"Perfil fixo: {profile} (detecção auto score={score}, meses={months})")
    else:
        profile, score, months = detect_profile(project_dir)
        print(f"Perfil detectado: {profile} (score={score}, meses funil={months})")

    run(
        [
            sys.executable,
            str(BUILD),
            "--project-folder",
            str(project_dir.relative_to(PROJECT)),
            "--profile",
            profile,
            "--reference-date",
            REF,
            "--gp-source",
            "online",
        ]
    )
    xlsx = project_dir / "spreadsheet" / "breakeven.xlsx"
    run(
        [
            sys.executable,
            str(GENERATE),
            "--config",
            str(project_dir / "config.json"),
            "--output",
            str(xlsx),
            "--reference-date",
            REF,
        ]
    )
    upload = subprocess.run(
        [
            sys.executable,
            str(UPLOAD),
            str(xlsx),
            "--config",
            str(project_dir / "config.json"),
            "--share-anyone",
        ],
        cwd=PROJECT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(upload.stdout.strip())
    url = payload.get("webViewLink") or upload.stdout.strip()
    print("Upload:", url)
    return {**item, "profile": profile, "funnel_months": months, "breakeven_url": url, "status": "ok"}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="", help="SR rows comma-separated, e.g. 3,4,5,6")
    args = parser.parse_args()
    selected = {int(x.strip()) for x in args.rows.split(",") if x.strip()} if args.rows else None

    results = []
    for item in BATCH:
        if selected and item["sr_row"] not in selected:
            continue
        try:
            results.append(process_one(item))
        except Exception as exc:
            print(f"ERRO SR {item['sr_row']}: {exc}")
            results.append({**item, "status": "error", "error": str(exc)})

    out = PROJECT / "_context" / "batch_sr_1_6_results.json"
    existing = []
    if out.exists():
        existing = json.loads(out.read_text(encoding="utf-8"))
    by_row = {r["sr_row"]: r for r in existing}
    for r in results:
        by_row[r["sr_row"]] = r
    merged = [by_row[k] for k in sorted(by_row)]
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nDone. Results:", out)


if __name__ == "__main__":
    main()
