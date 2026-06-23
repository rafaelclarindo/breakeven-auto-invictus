#!/usr/bin/env python3
"""Baixa uma planilha Google como XLSX."""
from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PROJECT = Path(__file__).resolve().parents[2]
CRED_PATH = PROJECT.parent / "assessor-pessoal" / "mcp" / "credentials" / "google_sheets_token.json"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def extract_file_id(link: str) -> str:
    for pattern in (r"/spreadsheets/d/([^/?#]+)", r"/file/d/([^/?#]+)", r"[?&]id=([^&#]+)"):
        match = re.search(pattern, link)
        if match:
            return match.group(1)
    raise ValueError(f"Link sem fileId reconhecido: {link}")


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


def public_export(file_id: str) -> bytes:
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        payload = response.read()
    if not payload.startswith(b"PK"):
        raise RuntimeError("Export público não retornou um XLSX válido.")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa Google Sheets como XLSX.")
    parser.add_argument("url")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    file_id = extract_file_id(args.url)
    drive = build("drive", "v3", credentials=load_credentials())
    try:
        payload = drive.files().export(fileId=file_id, mimeType=XLSX_MIME).execute()
    except HttpError:
        payload = public_export(file_id)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(args.output)


if __name__ == "__main__":
    main()
