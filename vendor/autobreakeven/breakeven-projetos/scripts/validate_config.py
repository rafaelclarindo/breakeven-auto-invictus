#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


REQUIRED_SCENARIO_FIELDS = [
    "media",
    "revenue",
    "ticket",
    "session_view",
    "view_cart_share",
    "add_view_cart",
    "viewcart_checkout",
    "checkout_shipping",
    "shipping_payment",
    "payment_order",
    "order_sale",
]


def main():
    parser = argparse.ArgumentParser(description="Valida o JSON do breakeven.")
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))

    required = [
        "client",
        "current_period",
        "lt_period",
        "margin",
        "monthly_fee",
        "monthly_media",
        "source_months",
        "benchmark_months",
        "current_funnel",
        "minimum_scenario",
        "scenarios",
    ]
    errors = [f"Campo ausente: {key}" for key in required if key not in config]

    if not errors:
        if config["margin"] <= 0 or config["margin"] > 1:
            errors.append("margin deve estar entre 0 e 1.")
        if len(config["source_months"]) != len(config["benchmark_months"]):
            if len(config["source_months"]) < len(config["benchmark_months"]):
                errors.append(
                    "source_months não pode ser menor que benchmark_months."
                )
        for row in config["source_months"]:
            if len(row) != 7:
                errors.append(f"source_months inválido: {row}")
        for row in config["benchmark_months"]:
            if len(row) != 9:
                errors.append(f"benchmark_months inválido: {row}")
        for name in ("Pessimista", "Realista", "Otimista"):
            scenario = config["scenarios"].get(name)
            if scenario is None:
                errors.append(f"Cenário ausente: {name}")
                continue
            for field in REQUIRED_SCENARIO_FIELDS:
                values = scenario.get(field)
                if not isinstance(values, list) or len(values) != 7:
                    errors.append(f"{name}.{field} deve conter 7 valores.")
        for name in config.get("scenario_sheet_order") or []:
            if name in ("Pessimista", "Realista", "Otimista"):
                continue
            scenario = config["scenarios"].get(name)
            if scenario is None:
                errors.append(f"Cenário em scenario_sheet_order ausente: {name}")
                continue
            for field in REQUIRED_SCENARIO_FIELDS:
                values = scenario.get(field)
                if not isinstance(values, list) or len(values) != 7:
                    errors.append(f"{name}.{field} deve conter 7 valores.")

    if errors:
        for error in errors:
            print(f"ERRO: {error}")
        raise SystemExit(1)
    print("OK")


if __name__ == "__main__":
    main()
