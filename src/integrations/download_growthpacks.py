#!/usr/bin/env python3
"""Baixa Growth Packs da fila Breakeven Auto para as pastas por projeto.

Opcional — o pipeline padrão lê o GP online via ``growthpack_sheets_reader`` (Sheets API).
Use este script apenas para cache offline em ``source/growthpack.xlsx``.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

PROJECT = Path(__file__).resolve().parents[2]
PORTFOLIO_DIR = PROJECT / "projects"
CRED_PATH = PROJECT.parent / "assessor-pessoal" / "mcp" / "credentials" / "google_sheets_token.json"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def latest_index() -> Path:
    index = PORTFOLIO_DIR / "index.json"
    if not index.exists():
        raise FileNotFoundError(
            "Index não encontrado. Rode prepare_strategy_review_projects.py primeiro."
        )
    return index


def load_credentials() -> Credentials:
    info = json.loads(CRED_PATH.read_text(encoding="utf-8"))
    creds = Credentials(
        token=info.get("token"),
        refresh_token=info.get("refresh_token"),
        token_uri=info.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=info.get("client_id"),
        client_secret=info.get("client_secret"),
        scopes=list(info.get("scopes") or []),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def extract_file_id(link: str | None) -> str | None:
    if not link:
        return None
    patterns = [
        r"/spreadsheets/d/([^/?#]+)",
        r"/file/d/([^/?#]+)",
        r"[?&]id=([^&#]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            return match.group(1)
    return None


def download_file(drive, file_id: str) -> bytes:
    try:
        return drive.files().export(fileId=file_id, mimeType=XLSX_MIME).execute()
    except HttpError as export_error:
        if export_error.resp.status not in {400, 403}:
            raise
        request = drive.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()


def download_public_export(file_id: str) -> bytes:
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - Google export URL
        payload = response.read()
    if not payload.startswith(b"PK"):
        raise RuntimeError("Export público não retornou um XLSX válido.")
    return payload


def load_manifest_entry(project_folder: Path) -> dict[str, Any]:
    path = project_folder / "source" / "manifest-entry.json"
    return json.loads(path.read_text(encoding="utf-8"))


def select_projects(index: dict[str, Any], statuses: set[str], orders: set[int] | None, limit: int | None):
    selected = []
    for project in index.get("projects", []):
        if statuses and project.get("status") not in statuses:
            continue
        if orders and int(project["order"]) not in orders:
            continue
        selected.append(project)
        if limit and len(selected) >= limit:
            break
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa Growth Packs para source/growthpack.xlsx.")
    parser.add_argument("--status", default="ready", help="Statuses separados por vírgula.")
    parser.add_argument("--orders", default=None, help="Ordens separadas por vírgula.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    statuses = {item.strip() for item in args.status.split(",") if item.strip()}
    orders = None
    if args.orders:
        orders = {int(item.strip()) for item in args.orders.split(",") if item.strip()}

    index = json.loads(latest_index().read_text(encoding="utf-8"))
    selected = select_projects(index, statuses, orders, args.limit)
    drive = build("drive", "v3", credentials=load_credentials())

    results = []
    for item in selected:
        project_folder = PROJECT / item["folder"]
        manifest_entry = load_manifest_entry(project_folder)
        output = project_folder / "source" / "growthpack.xlsx"
        link = manifest_entry.get("growthpack_updated_link")
        file_id = extract_file_id(link)
        result = {
            "order": item["order"],
            "name": item["name"],
            "folder": item["folder"],
            "output": str(output.relative_to(PROJECT)),
            "status": "pending",
            "message": "",
        }

        if output.exists() and not args.force:
            result["status"] = "skipped"
            result["message"] = "Arquivo já existe."
        elif not file_id:
            result["status"] = "failed"
            result["message"] = "Link sem fileId reconhecido."
        else:
            try:
                output.parent.mkdir(parents=True, exist_ok=True)
                try:
                    payload = download_file(drive, file_id)
                except HttpError:
                    payload = download_public_export(file_id)
                output.write_bytes(payload)
                result["status"] = "downloaded"
                result["message"] = "Growth Pack baixado."
            except Exception as exc:  # noqa: BLE001 - keep per-project batch running
                result["status"] = "failed"
                result["message"] = str(exc)
        results.append(result)
        print(f"{result['order']:02d} {result['status']}: {result['name']} - {result['message']}")

    summary = {
        "generated_at": date.today().isoformat(),
        "selected": len(results),
        "downloaded": sum(1 for r in results if r["status"] == "downloaded"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }
    out = PROJECT / "assets" / f"growthpack_downloads_{date.today().isoformat()}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"summary: {out}")


if __name__ == "__main__":
    main()
