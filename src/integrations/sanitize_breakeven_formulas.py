#!/usr/bin/env python3
"""Protege fórmulas de breakeven contra erros de divisão ao abrir no Google Sheets."""
from __future__ import annotations

import argparse
from pathlib import Path

import openpyxl

ERROR_GUARDED = ("=IFERROR(", "=IFNA(")


def should_guard(formula: str) -> bool:
    upper = formula.upper()
    return (
        formula.startswith("=")
        and "/" in formula
        and not upper.startswith(ERROR_GUARDED)
        and "#DIV/0!" not in upper
    )


def guard(formula: str) -> str:
    return f"=IFERROR({formula[1:]},0)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Adiciona IFERROR em fórmulas com divisão.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    wb = openpyxl.load_workbook(args.input)
    patched = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                value = cell.value
                if isinstance(value, str) and should_guard(value):
                    cell.value = guard(value)
                    patched += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(args.output)
    print(f"patched_formulas: {patched}")
    print(args.output)


if __name__ == "__main__":
    main()
