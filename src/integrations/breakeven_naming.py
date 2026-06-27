"""Convenção de nomes de entrega — Breakeven Auto (Colli & CO)."""
from __future__ import annotations

BRAND = "Colli & CO"
PRODUCT_TAG = "AI Auto"


def is_inside_sales_model(project_model: str) -> bool:
    return "inside sales" in (project_model or "").lower()


def is_marketplace_model(project_model: str) -> bool:
    return "marketplace" in (project_model or "").lower()


def breakeven_model_label(
    project_model: str = "",
    *,
    is_inside_sales: bool | None = None,
) -> str:
    if is_marketplace_model(project_model):
        return "Marketplace"
    if is_inside_sales is None:
        is_inside_sales = is_inside_sales_model(project_model)
    return "Inside Sales" if is_inside_sales else "E-commerce"


def breakeven_deliverable_title(
    client: str,
    project_model: str = "",
    *,
    is_inside_sales: bool | None = None,
) -> str:
    """Título canônico — Google Sheets e nome base do arquivo local."""
    model = breakeven_model_label(project_model, is_inside_sales=is_inside_sales)
    return f"[{BRAND}] - [{client}] - Breakeven {model} - {PRODUCT_TAG}"


def breakeven_local_filename(
    client: str,
    project_model: str = "",
    *,
    is_inside_sales: bool | None = None,
    suffix: str = ".xlsx",
) -> str:
    return breakeven_deliverable_title(client, project_model, is_inside_sales=is_inside_sales) + suffix


def breakeven_name_from_config(config: dict) -> str:
    return breakeven_deliverable_title(config["client"], config.get("project_model", ""))


def breakeven_filename_from_config(config: dict) -> str:
    return breakeven_local_filename(config["client"], config.get("project_model", ""))
