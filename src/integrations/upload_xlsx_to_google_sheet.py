#!/usr/bin/env python3
"""Sobe um XLSX para o Google Drive convertendo em Google Sheets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from breakeven_naming import breakeven_name_from_config

PROJECT = Path(__file__).resolve().parents[2]
CRED_PATH = PROJECT.parent / "assessor-pessoal" / "mcp" / "credentials" / "google_sheets_token.json"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload XLSX convertido para Google Sheets.")
    parser.add_argument("xlsx", type=Path)
    parser.add_argument("--name", help="Título no Drive; omita se usar --config")
    parser.add_argument(
        "--config",
        type=Path,
        help="Config JSON — deriva o nome padrão [Colli & CO] - [Cliente] - Breakeven … - AI Auto",
    )
    parser.add_argument("--share-anyone", action="store_true")
    args = parser.parse_args()

    if args.name:
        sheet_name = args.name
    elif args.config:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        sheet_name = breakeven_name_from_config(config)
    else:
        parser.error("Informe --name ou --config para definir o título da planilha.")

    drive = build("drive", "v3", credentials=load_credentials())
    media = MediaFileUpload(str(args.xlsx), mimetype=XLSX_MIME, resumable=False)
    created = drive.files().create(
        body={"name": sheet_name, "mimeType": GOOGLE_SHEET_MIME},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()

    if args.share_anyone:
        drive.permissions().create(
            fileId=created["id"],
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()

    print(json.dumps(created, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
