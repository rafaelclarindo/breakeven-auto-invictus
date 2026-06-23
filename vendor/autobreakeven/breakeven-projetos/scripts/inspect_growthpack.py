#!/usr/bin/env python3

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def column_index(reference):
    letters = re.match(r"[A-Z]+", reference).group()
    value = 0
    for char in letters:
        value = value * 26 + ord(char) - 64
    return value


def main():
    parser = argparse.ArgumentParser(
        description="Inspeciona um Growth Pack XLSX sem alterar o arquivo."
    )
    parser.add_argument("xlsx", type=Path)
    parser.add_argument("--rows", type=int, default=40)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with zipfile.ZipFile(args.xlsx) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall(f"{{{MAIN}}}si"):
                shared.append(
                    "".join(
                        node.text or ""
                        for node in item.iter(f"{{{MAIN}}}t")
                    )
                )

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(
            archive.read("xl/_rels/workbook.xml.rels")
        )
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in relationships.findall(f"{{{PKG_REL}}}Relationship")
        }

        result = {"file": str(args.xlsx), "sheets": []}
        sheets = workbook.find(f"{{{MAIN}}}sheets")
        for sheet in sheets:
            name = sheet.attrib["name"]
            rel_id = sheet.attrib[f"{{{REL}}}id"]
            target = rel_map[rel_id].lstrip("/")
            if not target.startswith("xl/"):
                target = f"xl/{target}"
            root = ET.fromstring(archive.read(target))
            rows = []
            for row in root.findall(f".//{{{MAIN}}}row"):
                row_number = int(row.attrib["r"])
                if row_number > args.rows:
                    break
                values = {}
                for cell in row.findall(f"{{{MAIN}}}c"):
                    ref = cell.attrib["r"]
                    value_node = cell.find(f"{{{MAIN}}}v")
                    formula_node = cell.find(f"{{{MAIN}}}f")
                    value = None if value_node is None else value_node.text
                    if cell.attrib.get("t") == "s" and value is not None:
                        value = shared[int(value)]
                    elif cell.attrib.get("t") == "inlineStr":
                        value = "".join(
                            node.text or ""
                            for node in cell.iter(f"{{{MAIN}}}t")
                        )
                    values[str(column_index(ref))] = {
                        "cell": ref,
                        "value": value,
                        "formula": None
                        if formula_node is None
                        else formula_node.text,
                    }
                if values:
                    rows.append({"row": row_number, "cells": values})
            result["sheets"].append(
                {"name": name, "target": target, "rows": rows}
            )

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(payload)


if __name__ == "__main__":
    main()
