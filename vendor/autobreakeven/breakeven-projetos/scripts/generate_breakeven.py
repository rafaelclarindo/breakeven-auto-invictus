#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from statistics import median

import xlsxwriter

_INTEGRATIONS_DIR = Path(__file__).resolve().parents[4] / "src" / "integrations"
if str(_INTEGRATIONS_DIR) not in sys.path:
    sys.path.insert(0, str(_INTEGRATIONS_DIR))

from breakeven_naming import breakeven_filename_from_config
from breakeven_personalization import (
    build_resumo_title,
    build_strategic_reading,
    scenario_actual_column_label,
)
from breakeven_projection import (
    breakeven_month_from_rows,
    compute_financial_projections,
    projection_month_headers,
)


def div_formula(expr: str, default: str = "0") -> str:
    """Wrap a division expression with IFERROR for Google Sheets stability."""
    return f"=IFERROR({expr},{default})"


MAX_PROJECTION_MONTHS = 36
RATE_KEYS = {
    "session_view",
    "view_add",
    "add_view_cart",
    "viewcart_checkout",
    "checkout_shipping",
    "shipping_payment",
    "payment_order",
    "order_sale",
    "view_cart_share",
    "add_cart_purchase",
    "lead_lead_quali",
    "lead_quali_mql",
    "mql_sql",
    "sql_sale",
}


def extend_numeric_series(values: list[float], length: int, *, key: str = "") -> list[float]:
    result = list(values)
    while len(result) < length:
        if len(result) >= 2 and result[-2]:
            delta = result[-1] - result[-2]
            ratio = result[-1] / result[-2]
        else:
            delta = 0.0
            ratio = 1.1
        if key == "revenue":
            next_val = result[-1] * ratio
        elif key == "ticket":
            next_val = result[-1] * 1.01
        elif key == "media":
            next_val = result[-1]
        elif key in RATE_KEYS:
            next_val = min(1.0, max(0.0001, result[-1] + delta))
        else:
            next_val = result[-1] + delta
        result.append(next_val)
    return result[:length]


def extend_scenario_config(config: dict, length: int) -> None:
    for key in (
        "media",
        "revenue",
        "ticket",
        "session_view",
        "view_add",
        "view_cart_share",
        "add_view_cart",
        "viewcart_checkout",
        "checkout_shipping",
        "shipping_payment",
        "payment_order",
        "order_sale",
    ):
        if key in config:
            config[key] = extend_numeric_series(config[key], length, key=key)


def months_until_breakeven(
    revenues: list[float],
    *,
    margin: float,
    monthly_fee: float,
    monthly_media: float,
    current_result: float,
    max_months: int = MAX_PROJECTION_MONTHS,
) -> int:
    if current_result >= -0.01:
        return 1
    extended = extend_numeric_series(revenues, max_months, key="revenue")
    cumulative = current_result
    for month in range(1, max_months + 1):
        cumulative += extended[month - 1] * margin - (monthly_fee + monthly_media)
        if cumulative >= -0.01:
            return month
    return max_months


def breakeven_month_label(projections: list[dict], projection_months: int) -> str:
    for idx, proj in enumerate(projections, 1):
        if proj["cumulative_result"] >= -0.01:
            return f"Mês {idx}"
    return f"Não breakeva em {projection_months} meses"


def full_funnel_rate_expr(prem_col: str) -> str:
    return f"'Premissas'!{prem_col}15*'Premissas'!{prem_col}16*'Premissas'!{prem_col}17"


def inside_sales_lead_to_sale_expr(prem_col: str, has_lead_quali: bool) -> str:
    if has_lead_quali:
        return (
            f"'Premissas'!{prem_col}17*'Premissas'!{prem_col}18*"
            f"'Premissas'!{prem_col}19*'Premissas'!{prem_col}20"
        )
    return f"'Premissas'!{prem_col}17"


def ecommerce_session_to_sale_expr(prem_col: str) -> str:
    return (
        f"'Premissas'!{prem_col}15*'Premissas'!{prem_col}16*'Premissas'!{prem_col}17*"
        f"'Premissas'!{prem_col}18*'Premissas'!{prem_col}19*'Premissas'!{prem_col}20"
    )


def unified_final_conversion_expr(
    prem_col: str, *, is_inside_sales: bool, has_lead_quali: bool, is_ecommerce: bool
) -> str:
    if is_ecommerce:
        return ecommerce_session_to_sale_expr(prem_col)
    return inside_sales_lead_to_sale_expr(prem_col, has_lead_quali)


def inside_sales_full_funnel_rate_expr(prem_col: str, has_lead_quali: bool) -> str:
    if has_lead_quali:
        return (
            f"'Premissas'!{prem_col}15*'Premissas'!{prem_col}16*'Premissas'!{prem_col}17*"
            f"'Premissas'!{prem_col}18*'Premissas'!{prem_col}19*'Premissas'!{prem_col}20"
        )
    return full_funnel_rate_expr(prem_col)


# Excel row numbers (1-based) — aba Breakeven unificada (inside sales + lead quali).
BEU = {
    "header": 2,
    "cost_total": 3,
    "fee": 4,
    "media": 5,
    "impressions": 6,
    "rate_imp_click": 7,
    "clicks": 8,
    "rate_click_lead": 9,
    "leads": 10,
    "rate_lead_quali": 11,
    "lead_quali": 12,
    "rate_quali_mql": 13,
    "mqls": 14,
    "rate_mql_sql": 15,
    "sqls": 16,
    "rate_sql_sale": 17,
    "sales": 18,
    "rate_lead_sale": 19,
    "cps": 20,
    "cost_sql": 21,
    "cpv": 22,
    "ticket": 23,
    "margin": 24,
    "revenue": 25,
    "revenue_acc": 26,
    "roas": 27,
    "mc_month": 28,
    "mc_acc": 29,
    "cost_month": 30,
    "cost_acc": 31,
    "result_month": 32,
    "result_acc": 33,
    "roi_month": 34,
    "roi_project": 35,
    "future_revenue": 36,
    "status": 37,
}


def beu_row_labels() -> dict[int, str]:
    return {
        BEU["cost_total"]: "Custos Fixos V4 + Mídia",
        BEU["fee"]: "Fee Mensal",
        BEU["media"]: "Verba de mídia",
        BEU["impressions"]: "Impressões por mês",
        BEU["rate_imp_click"]: "Taxa Impressões → Cliques",
        BEU["clicks"]: "Cliques",
        BEU["rate_click_lead"]: "Taxa Cliques → Leads",
        BEU["leads"]: "Leads",
        BEU["rate_lead_quali"]: "Taxa Leads → Lead quali",
        BEU["lead_quali"]: "Lead quali",
        BEU["rate_quali_mql"]: "Taxa Lead quali → MQLs",
        BEU["mqls"]: "MQLs",
        BEU["rate_mql_sql"]: "Taxa MQLs → SQLs",
        BEU["sqls"]: "SQLs por mês",
        BEU["rate_sql_sale"]: "Taxa SQLs → Vendas",
        BEU["sales"]: "Vendas por mês",
        BEU["rate_lead_sale"]: "Taxa Leads → Vendas",
        BEU["cps"]: "Custo por impressão",
        BEU["cost_sql"]: "Custo por SQL",
        BEU["cpv"]: "Custo por venda",
        BEU["ticket"]: "Ticket médio",
        BEU["margin"]: "Margem Contribuição (MC)",
        BEU["revenue"]: "Valor de Venda no mês",
        BEU["revenue_acc"]: "Valor Acumulado",
        BEU["roas"]: "ROAS no mês",
        BEU["mc_month"]: "Resultado MC/mês",
        BEU["mc_acc"]: "Resultado MC Acumulado",
        BEU["cost_month"]: "Custo V4 + mídia/mês",
        BEU["cost_acc"]: "Custo V4 + mídia acumulado",
        BEU["result_month"]: "Resultado líquido Mês",
        BEU["result_acc"]: "Resultado líquido Acumulado",
        BEU["roi_month"]: "ROI no mês",
        BEU["roi_project"]: "ROI Projeto",
        BEU["future_revenue"]: "Receita futura necessária",
        BEU["status"]: "Status do breakeven",
    }


def beu_write_index(excel_row: int) -> int:
    return excel_row - 1


def build_minimum_funnel_cache(
    projections: list[dict],
    minimum_full_rates: dict[str, list[float]],
    has_lead_quali: bool,
    is_inside_sales: bool,
) -> list[dict]:
    cached = []
    for idx, proj in enumerate(projections):
        sales = proj["sales"]
        if is_inside_sales:
            funnel_volumes = build_inside_sales_funnel_volumes(
                sales,
                {
                    "shipping_payment": minimum_full_rates["shipping_payment"][idx],
                    "checkout_shipping": minimum_full_rates["checkout_shipping"][idx],
                    "viewcart_checkout": minimum_full_rates["viewcart_checkout"][idx],
                    "add_view_cart": minimum_full_rates["add_view_cart"][idx],
                    "view_add": minimum_full_rates["view_add"][idx],
                    "session_view": minimum_full_rates["session_view"][idx],
                },
                has_lead_quali=has_lead_quali,
            )
            cached.append(funnel_volumes)
        else:
            orders = sales / minimum_full_rates["order_sale"][idx]
            payment = orders / minimum_full_rates["payment_order"][idx]
            shipping = payment / minimum_full_rates["shipping_payment"][idx]
            checkout = shipping / minimum_full_rates["checkout_shipping"][idx]
            view_cart = checkout / minimum_full_rates["viewcart_checkout"][idx]
            add_cart = view_cart / minimum_full_rates["add_view_cart"][idx]
            view_item = add_cart / minimum_full_rates["view_add"][idx]
            sessions = view_item / minimum_full_rates["session_view"][idx]
            cached.append(
                {
                    "sessions": sessions,
                    "view_item": view_item,
                    "add_cart": add_cart,
                    "view_cart": view_cart,
                    "begin_checkout": checkout,
                    "checkout": checkout,
                    "shipping": shipping,
                    "payment": payment,
                    "orders": orders,
                    "sales": sales,
                }
            )
    return cached


def build_projection_rate_series(
    minimum: dict,
    key: str,
    current_value: float,
    projection_months: int,
    max_rate: float,
    boost: float = 1.05,
) -> list[float]:
    raw = minimum.get(key)
    if isinstance(raw, list):
        base = list(raw)
        if base:
            base[0] = current_value
    else:
        target = min(
            max_rate,
            max(current_value, current_value * boost, float(raw or current_value)),
        )
        base_len = max(2, len(minimum.get("session_view", [0, 0])))
        base = [
            current_value + (target - current_value) * i / (base_len - 1)
            for i in range(base_len)
        ]
    return extend_numeric_series(base, projection_months, key=key)


def is_inside_sales_model(project_model: str) -> bool:
    return "inside sales" in (project_model or "").lower()


def has_lead_quali_funnel(config_data: dict) -> bool:
    return bool(config_data.get("funnel_has_lead_quali"))


def projection_rules(config_data: dict) -> dict:
    defaults = {
        "max_conversion_rate": 0.95,
        "min_cost_per_impression": 0.01,
        "media_lever_after_monthly_breakeven": False,
    }
    merged = defaults.copy()
    merged.update(config_data.get("projection_rules") or {})
    return merged


def cap_conversion_rate(value: float, max_rate: float = 0.95) -> float:
    return min(max_rate, value)


INSIDE_SALES_INTEGRATED_SKIP_ROWS = frozenset({46, 47, 49, 50, 51, 52})
INSIDE_SALES_INTEGRATED_SKIP_ROWS_LEAD_QUALI = frozenset({49, 50, 51, 52})
INSIDE_SALES_SCENARIO_SKIP_ROWS = frozenset({26, 27, 28, 29, 30, 31})
INSIDE_SALES_SCENARIO_SKIP_ROWS_LEAD_QUALI = frozenset({28, 29, 30, 31})
INSIDE_SALES_INTEGRATED_RATE_ROWS = frozenset({38, 40, 42, 44, 48})
INSIDE_SALES_INTEGRATED_RATE_ROWS_LEAD_QUALI = frozenset({38, 40, 42, 44, 46, 48})
INSIDE_SALES_SCENARIO_RATE_ROWS = frozenset({17, 19, 21, 23, 25})
INSIDE_SALES_SCENARIO_RATE_ROWS_LEAD_QUALI = frozenset({17, 19, 21, 23, 25, 27})


def integrated_funnel_row_labels(
    is_inside_sales: bool,
    final_funnel_rate_label: str,
    lead_quali: bool = False,
) -> dict[int, str]:
    if not is_inside_sales:
        return {
            37: "Sessões",
            38: "Taxa Sessão → View item",
            39: "View item",
            40: "Taxa View item → Add to cart",
            41: "Add to cart",
            42: "Taxa Add to cart → View cart",
            43: "View cart",
            44: "Taxa View cart → Begin checkout",
            45: "Begin checkout",
            46: "Taxa Begin checkout → Add shipping info",
            47: "Add shipping info",
            48: "Taxa Add shipping info → Add payment info",
            49: "Add payment info",
            50: "Taxa Add payment info → Pedido",
            51: "Pedidos",
            52: "Taxa Pedido → Venda",
            53: "Vendas",
            54: final_funnel_rate_label,
            55: "Custo por sessão",
            56: "Custo por pedido",
            57: "Custo por venda",
        }
    if lead_quali:
        return {
            37: "Impressões",
            38: "Taxa Impressões → Cliques",
            39: "Cliques",
            40: "Taxa Cliques → Leads",
            41: "Leads",
            42: "Taxa Leads → Lead quali",
            43: "Lead quali",
            44: "Taxa Lead quali → MQLs",
            45: "MQLs",
            46: "Taxa MQLs → SQLs",
            47: "SQLs",
            48: "Taxa SQLs → Vendas",
            53: "Vendas",
            54: final_funnel_rate_label,
            55: "Custo por impressão",
            56: "Custo por SQL",
            57: "Custo por venda",
        }
    return {
        37: "Impressões",
        38: "Taxa Impressões → Cliques",
        39: "Cliques",
        40: "Taxa Cliques → Leads",
        41: "Leads",
        42: "Taxa Leads → MQLs",
        43: "MQLs",
        44: "Taxa MQLs → SQLs",
        45: "SQLs",
        48: "Taxa SQLs → Vendas",
        53: "Vendas",
        54: final_funnel_rate_label,
        55: "Custo por impressão",
        56: "Custo por SQL",
        57: "Custo por venda",
    }


def scenario_funnel_row_labels(
    is_inside_sales: bool,
    final_funnel_rate_label: str,
    lead_quali: bool = False,
) -> dict[int, str]:
    if not is_inside_sales:
        return {
            16: "Sessões",
            17: "Taxa Sessão → View item",
            18: "View item",
            19: "Taxa View item → Add to cart",
            20: "Add to cart",
            21: "Taxa Add to cart → View cart",
            22: "View cart",
            23: "Taxa View cart → Begin checkout",
            24: "Begin checkout",
            25: "Taxa Begin checkout → Add shipping info",
            26: "Add shipping info",
            27: "Taxa Add shipping info → Add payment info",
            28: "Add payment info",
            29: "Taxa Add payment info → Pedido",
            30: "Pedidos",
            31: "Taxa Pedido → Venda",
            32: "Vendas",
            33: final_funnel_rate_label,
            34: "Custo por sessão",
            35: "Custo por pedido",
            36: "Custo por venda",
            37: "Receita recalculada",
            38: "Diferença vs. faturamento alvo",
        }
    if lead_quali:
        return {
            16: "Impressões",
            17: "Taxa Impressões → Cliques",
            18: "Cliques",
            19: "Taxa Cliques → Leads",
            20: "Leads",
            21: "Taxa Leads → Lead quali",
            22: "Lead quali",
            23: "Taxa Lead quali → MQLs",
            24: "MQLs",
            25: "Taxa MQLs → SQLs",
            26: "SQLs",
            27: "Taxa SQLs → Vendas",
            32: "Vendas",
            33: final_funnel_rate_label,
            34: "Custo por impressão",
            35: "Custo por SQL",
            36: "Custo por venda",
            37: "Receita recalculada",
            38: "Diferença vs. faturamento alvo",
        }
    return {
        16: "Impressões",
        17: "Taxa Impressões → Cliques",
        18: "Cliques",
        19: "Taxa Cliques → Leads",
        20: "Leads",
        21: "Taxa Leads → MQLs",
        22: "MQLs",
        23: "Taxa MQLs → SQLs",
        24: "SQLs",
        25: "Taxa SQLs → Vendas",
        32: "Vendas",
        33: final_funnel_rate_label,
        34: "Custo por impressão",
        35: "Custo por SQL",
        36: "Custo por venda",
        37: "Receita recalculada",
        38: "Diferença vs. faturamento alvo",
    }


def breakeven_financial_row_labels(is_inside_sales: bool, funnel_conversion_label: str) -> dict[int, str]:
    labels = {
        2: "Custos Fixos V4 + Mídia",
        3: "Fee Mensal",
        4: "Verba de mídia",
        5: "Sessões por mês",
        6: "Custo por Sessão",
        7: "Taxa de Conversão Sessão → Pedidos",
        8: "Pedidos por mês",
        9: "Custo por Pedido",
        10: "Taxa de Conversão Pedidos → Venda",
        11: "Vendas por mês",
        12: "Custo por Venda",
        13: funnel_conversion_label,
        15: "Ticket médio",
        16: "Margem Contribuição (MC)",
        18: "Valor de Venda no mês",
        19: "Valor Acumulado",
        20: "ROAS no mês",
        21: "Resultado MC/mês",
        22: "Resultado MC Acumulado",
        24: "Custo V4 + mídia/mês",
        25: "Custo V4 + mídia acumulado",
        27: "Resultado líquido Mês",
        28: "Resultado líquido Acumulado",
        29: "ROI no mês",
        30: "ROI Projeto",
        32: "Receita futura necessária",
        33: "Status do breakeven",
    }
    if is_inside_sales:
        labels.update(
            {
                5: "Impressões por mês",
                6: "Custo por impressão",
                7: "Taxa Impressões → SQLs",
                8: "SQLs por mês",
                9: "Custo por SQL",
                10: "Taxa SQLs → Vendas",
            }
        )
    return labels


def build_inside_sales_funnel_volumes(
    sales: float,
    rates: dict[str, float],
    has_lead_quali: bool = False,
) -> dict[str, float]:
    sqls = sales / rates["shipping_payment"]
    if has_lead_quali:
        mqls = sqls / rates["checkout_shipping"]
        lead_quali = mqls / rates["viewcart_checkout"]
        leads = lead_quali / rates["add_view_cart"]
    else:
        mqls = sqls / rates["viewcart_checkout"]
        leads = mqls / rates["add_view_cart"]
        lead_quali = mqls
    view_item = leads / rates["view_add"]
    sessions = view_item / rates["session_view"]
    return {
        "sessions": sessions,
        "view_item": view_item,
        "add_cart": leads,
        "view_cart": lead_quali,
        "begin_checkout": mqls,
        "checkout": sqls,
        "shipping": sqls,
        "payment": sales,
        "orders": sqls,
        "sales": sales,
    }


def inside_sales_funnel_rates(
    config: dict,
    idx: int,
    has_lead_quali: bool,
) -> dict[str, float]:
    rates = {
        "shipping_payment": config["shipping_payment"][idx],
        "viewcart_checkout": config["viewcart_checkout"][idx],
        "add_view_cart": config["add_view_cart"][idx],
        "view_add": config["view_add"][idx],
        "session_view": config["session_view"][idx],
    }
    if has_lead_quali:
        rates["checkout_shipping"] = config["checkout_shipping"][idx]
    return rates


def inside_sales_scenario_rate_values(config: dict, idx: int, has_lead_quali: bool) -> dict[int, float]:
    if has_lead_quali:
        return {
            17: config["session_view"][idx],
            19: config["view_add"][idx],
            21: config["add_view_cart"][idx],
            23: config["viewcart_checkout"][idx],
            25: config["checkout_shipping"][idx],
            27: config["shipping_payment"][idx],
        }
    return {
        17: config["session_view"][idx],
        19: config["view_add"][idx],
        21: config["add_view_cart"][idx],
        23: config["viewcart_checkout"][idx],
        25: config["shipping_payment"][idx],
    }


def inside_sales_scenario_volume_formulas(
    col_name: str,
    final_rate_volume_row: int,
    has_lead_quali: bool,
) -> dict[int, str]:
    if has_lead_quali:
        return {
            32: f"={col_name}6/{col_name}7",
            26: f"={col_name}32/{col_name}27",
            24: f"={col_name}26/{col_name}25",
            22: f"={col_name}24/{col_name}23",
            20: f"={col_name}22/{col_name}21",
            18: f"={col_name}20/{col_name}19",
            16: f"={col_name}18/{col_name}17",
            33: f"={col_name}32/{col_name}{final_rate_volume_row}",
            34: f"={col_name}4/{col_name}16",
            35: f"={col_name}4/{col_name}26",
            36: f"={col_name}4/{col_name}32",
            37: f"={col_name}32*{col_name}7",
            38: f"=ROUND({col_name}37-{col_name}6,2)",
        }
    return {
        32: f"={col_name}6/{col_name}7",
        24: f"={col_name}32/{col_name}25",
        22: f"={col_name}24/{col_name}23",
        20: f"={col_name}22/{col_name}21",
        18: f"={col_name}20/{col_name}19",
        16: f"={col_name}18/{col_name}17",
        33: f"={col_name}32/{col_name}{final_rate_volume_row}",
        34: f"={col_name}4/{col_name}16",
        35: f"={col_name}4/{col_name}24",
        36: f"={col_name}4/{col_name}32",
        37: f"={col_name}32*{col_name}7",
        38: f"=ROUND({col_name}37-{col_name}6,2)",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Gera a planilha completa de breakeven a partir de um JSON validado."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--reference-date",
        type=str,
        default=None,
        help="Data de geração ISO (YYYY-MM-DD). Define o 1º mês dos cenários (regra dia 15/16).",
    )
    args = parser.parse_args()

    reference_date = (
        datetime.strptime(args.reference_date, "%Y-%m-%d").date()
        if args.reference_date
        else date.today()
    )

    config_data = json.loads(args.config.read_text(encoding="utf-8"))
    is_inside_sales = is_inside_sales_model(config_data.get("project_model", ""))
    has_lead_quali = has_lead_quali_funnel(config_data) and is_inside_sales
    rules = projection_rules(config_data)
    max_conversion_rate = rules["max_conversion_rate"]
    min_cost_per_impression = rules["min_cost_per_impression"]
    media_lever_after_breakeven = rules["media_lever_after_monthly_breakeven"]
    client = config_data["client"]
    output = args.output or args.config.with_name(breakeven_filename_from_config(config_data))
    output.parent.mkdir(parents=True, exist_ok=True)

    # Ordem: mês, fee, mídia, sessões, pedidos, vendas e faturamento.
    source_months = [tuple(row) for row in config_data["source_months"]]

    # Ordem: mês, sessões, view item, add cart, view cart, checkout,
    # shipping, payment e purchase.
    benchmark_months = [tuple(row) for row in config_data["benchmark_months"]]

    benchmark_rates = []
    for month, sessions, view_item, add_cart, view_cart, checkout, shipping, payment, purchase in benchmark_months:
        benchmark_rates.append(
            (
                month,
                cap_conversion_rate(view_item / sessions, max_conversion_rate) if sessions else 0,
                cap_conversion_rate(add_cart / view_item, max_conversion_rate) if view_item else 0,
                cap_conversion_rate(view_cart / add_cart, max_conversion_rate) if add_cart else 0,
                cap_conversion_rate(checkout / view_cart, max_conversion_rate) if view_cart else 0,
                cap_conversion_rate(shipping / checkout, max_conversion_rate) if checkout else 0,
                cap_conversion_rate(payment / shipping, max_conversion_rate) if shipping else 0,
                cap_conversion_rate(purchase / payment, max_conversion_rate) if payment else 0,
                cap_conversion_rate(purchase / sessions, max_conversion_rate) if sessions else 0,
            )
        )

    benchmark_medians = [
        median(row[col] for row in benchmark_rates) for col in range(1, 9)
    ]
    (
        bench_session_view,
        bench_view_add,
        bench_add_viewcart,
        bench_viewcart_checkout,
        bench_checkout_shipping,
        bench_shipping_payment,
        bench_payment_purchase,
        bench_session_purchase,
    ) = benchmark_medians
    bench_lead_to_sale = median(
        min(1, purchase / add_cart) if add_cart else 0
        for _, _, _, add_cart, _, _, _, _, purchase in benchmark_months
    )
    final_conversion_bench = bench_lead_to_sale if is_inside_sales else bench_session_purchase

    current = config_data["current_funnel"]
    current_sessions = current["sessions"]
    current_pageviews = current.get("page_view", current_sessions)
    current_view_item = current["view_item"]
    current_add_cart = current["add_to_cart"]
    current_view_cart = current["view_cart"]
    current_checkout = current["begin_checkout"]
    current_shipping = current["add_shipping_info"]
    current_payment = current["add_payment_info"]
    current_purchase = current["purchase"]
    current_orders = current.get("orders", current_purchase)
    current_sales = current.get("sales", current_purchase)
    current_month_revenue = current["revenue"]
    current_month_media = current["media"]
    current_period = config_data["current_period"]
    bench_label = f"Mediana de {len(benchmark_months)} meses"

    if is_inside_sales:
        if has_lead_quali:
            current_funnel = [
                ("Impressões", current_sessions, None, None, "Base"),
                ("Cliques", current_view_item, current_view_item / current_sessions, bench_session_view, bench_label),
                ("Leads", current_add_cart, current_add_cart / current_view_item, bench_view_add, bench_label),
                (
                    "Lead quali",
                    current_view_cart,
                    min(max_conversion_rate, current_view_cart / current_add_cart),
                    bench_add_viewcart,
                    bench_label,
                ),
                (
                    "MQLs",
                    current_checkout,
                    current_checkout / current_view_cart if current_view_cart else 0,
                    bench_viewcart_checkout,
                    bench_label,
                ),
                (
                    "SQLs",
                    current_shipping,
                    current_shipping / current_checkout if current_checkout else 0,
                    bench_checkout_shipping,
                    bench_label,
                ),
                (
                    "Vendas",
                    current_sales,
                    current_sales / current_shipping if current_shipping else 0,
                    bench_shipping_payment,
                    bench_label,
                ),
            ]
        else:
            current_funnel = [
                ("Impressões", current_sessions, None, None, "Base"),
                ("Cliques", current_view_item, current_view_item / current_sessions, bench_session_view, bench_label),
                ("Leads", current_add_cart, current_add_cart / current_view_item, bench_view_add, bench_label),
                ("MQLs", current_view_cart, current_view_cart / current_add_cart, bench_add_viewcart, bench_label),
                ("SQLs", current_checkout, current_checkout / current_view_cart, bench_viewcart_checkout, bench_label),
                (
                    "Vendas",
                    current_sales,
                    current_sales / current_checkout if current_checkout else 0,
                    bench_shipping_payment,
                    bench_label,
                ),
            ]
    else:
        current_funnel = [
            ("Sessões", current_sessions, None, None, "Base"),
            ("Page view", current_pageviews, current_pageviews / current_sessions, None, "Múltiplas páginas por sessão"),
            ("View item", current_view_item, current_view_item / current_sessions, bench_session_view, bench_label),
            ("Add to cart", current_add_cart, current_add_cart / current_view_item, bench_view_add, bench_label),
            ("View cart", current_view_cart, current_view_cart / current_add_cart, bench_add_viewcart, "Validar sequência do tracking"),
            ("Begin checkout", current_checkout, current_checkout / current_view_cart, bench_viewcart_checkout, bench_label),
            ("Add shipping info", current_shipping, current_shipping / current_checkout, bench_checkout_shipping, "Validar sequência do tracking"),
            ("Add payment info", current_payment, current_payment / current_shipping, bench_shipping_payment, bench_label),
            ("Purchase", current_purchase, current_purchase / current_payment, bench_payment_purchase, bench_label),
        ]

    fee_total = sum(row[1] for row in source_months)
    media_total = sum(row[2] for row in source_months)
    sessions_total = sum(row[3] for row in source_months)
    orders_total = sum(row[4] for row in source_months)
    sales_total = sum(row[5] for row in source_months)
    revenue_total = sum(row[6] for row in source_months)

    months_with_fee = len(source_months)
    source_data_first_excel_row = 4
    source_data_last_excel_row = 3 + months_with_fee
    source_total_excel_row = source_data_last_excel_row + 1

    margin = config_data["margin"]
    monthly_fee = config_data["monthly_fee"]
    monthly_media = config_data["monthly_media"]
    current_cost = fee_total + media_total
    current_mc = revenue_total * margin
    current_result = current_mc - current_cost
    current_ticket = revenue_total / sales_total
    current_monthly_break_even = (monthly_fee + monthly_media) / margin

    minimum = config_data["minimum_scenario"]
    scenario_configs = config_data["scenarios"]
    base_minimum_revenue = list(minimum["revenue"])
    if not base_minimum_revenue:
        raise ValueError("minimum_scenario.revenue não pode ser vazio.")

    horizon_candidates = [
        months_until_breakeven(
            base_minimum_revenue,
            margin=margin,
            monthly_fee=monthly_fee,
            monthly_media=monthly_media,
            current_result=current_result,
        )
    ]
    for cfg in scenario_configs.values():
        horizon_candidates.append(
            months_until_breakeven(
                cfg["revenue"],
                margin=margin,
                monthly_fee=monthly_fee,
                monthly_media=monthly_media,
                current_result=current_result,
            )
        )
    projection_months = min(MAX_PROJECTION_MONTHS, max(horizon_candidates))
    future_cost = projection_months * (monthly_fee + monthly_media)
    future_revenue_required = (
        (abs(current_result) + future_cost) / margin
        if current_result < 0
        else future_cost / margin
    )

    projected_revenue = extend_numeric_series(base_minimum_revenue, projection_months, key="revenue")
    current_session_view = current_view_item / current_sessions if current_sessions else 0
    current_view_add_rate = current_add_cart / current_view_item if current_view_item else 0
    view_rates = build_projection_rate_series(
        minimum,
        "session_view",
        current_session_view,
        projection_months,
        max_conversion_rate,
        boost=1.05,
    )
    cart_rates = build_projection_rate_series(
        minimum,
        "view_add",
        current_view_add_rate,
        projection_months,
        max_conversion_rate,
        boost=1.05,
    )
    current_lead_to_sale = current_sales / current_add_cart if current_add_cart else 0
    lead_lead_quali_rates: list[float] = []
    lead_quali_mql_rates: list[float] = []
    mql_sql_rates: list[float] = []
    sql_sale_rates: list[float] = []
    if is_inside_sales and has_lead_quali:
        current_lead_lead_quali = current_view_cart / current_add_cart if current_add_cart else 0
        current_lead_quali_mql = current_checkout / current_view_cart if current_view_cart else 0
        current_mql_sql = current_shipping / current_checkout if current_checkout else 0
        current_sql_sale = current_sales / current_shipping if current_shipping else 0
        lead_lead_quali_rates = build_projection_rate_series(
            minimum,
            "lead_lead_quali",
            current_lead_lead_quali,
            projection_months,
            max_conversion_rate,
            boost=1.03,
        )
        lead_quali_mql_rates = build_projection_rate_series(
            minimum,
            "lead_quali_mql",
            current_lead_quali_mql,
            projection_months,
            max_conversion_rate,
            boost=1.08,
        )
        mql_sql_rates = build_projection_rate_series(
            minimum,
            "mql_sql",
            current_mql_sql,
            projection_months,
            max_conversion_rate,
            boost=1.05,
        )
        sql_sale_rates = build_projection_rate_series(
            minimum,
            "sql_sale",
            current_sql_sale,
            projection_months,
            max_conversion_rate,
            boost=1.08,
        )
        lead_to_sale_rates = [
            cap_conversion_rate(
                lead_lead_quali_rates[i]
                * lead_quali_mql_rates[i]
                * mql_sql_rates[i]
                * sql_sale_rates[i],
                max_conversion_rate,
            )
            for i in range(projection_months)
        ]
        cart_to_purchase = lead_to_sale_rates[0]
    elif is_inside_sales:
        cart_to_purchase_raw = minimum.get("add_cart_purchase", current_lead_to_sale)
        if isinstance(cart_to_purchase_raw, list):
            lead_to_sale_base = list(cart_to_purchase_raw)
            if lead_to_sale_base:
                lead_to_sale_base[0] = current_lead_to_sale
        else:
            lead_to_sale_target = min(
                max_conversion_rate,
                max(current_lead_to_sale, current_lead_to_sale * 1.05, float(cart_to_purchase_raw)),
            )
            base_len = max(2, len(minimum.get("session_view", [0, 0])))
            lead_to_sale_base = [
                current_lead_to_sale
                + (lead_to_sale_target - current_lead_to_sale) * i / (base_len - 1)
                for i in range(base_len)
            ]
        lead_to_sale_rates = extend_numeric_series(
            lead_to_sale_base, projection_months, key="add_cart_purchase"
        )
        cart_to_purchase = lead_to_sale_rates[0]
    else:
        cart_to_purchase_raw = minimum.get("add_cart_purchase", current_lead_to_sale)
        cart_to_purchase = (
            cart_to_purchase_raw
            if isinstance(cart_to_purchase_raw, (int, float))
            else cart_to_purchase_raw[-1]
        )
        lead_to_sale_rates = [cart_to_purchase] * projection_months
    approval_start = sales_total / orders_total
    base_approval = minimum.get("order_sale") or [
        approval_start
        + (minimum.get("approval_target", approval_start) - approval_start)
        * i
        / max(1, len(minimum.get("session_view", [0, 0])) - 1)
        for i in range(len(minimum.get("session_view", [0, 0])))
    ]
    approval_rates = extend_numeric_series(base_approval, projection_months, key="order_sale")

    be_proj_start_col = 4
    be_proj_last_col = be_proj_start_col + projection_months - 1
    be_proj_last_name = xlsxwriter.utility.xl_col_to_name(be_proj_last_col)
    scen_proj_start_col = 5
    scen_proj_last_col = scen_proj_start_col + projection_months - 1
    scen_proj_last_name = xlsxwriter.utility.xl_col_to_name(scen_proj_last_col)
    scen_sheet_last_col = scen_proj_last_col + 1
    scen_sheet_last_name = xlsxwriter.utility.xl_col_to_name(scen_sheet_last_col)
    prem_proj_start_col = 5
    prem_proj_last_col = prem_proj_start_col + projection_months - 1
    prem_proj_last_name = xlsxwriter.utility.xl_col_to_name(prem_proj_last_col)
    funnel_proj_start_col = 7
    funnel_proj_last_col = funnel_proj_start_col + projection_months - 1
    funnel_proj_last_name = xlsxwriter.utility.xl_col_to_name(funnel_proj_last_col)
    month_headers = projection_month_headers(projection_months, reference_date)
    scenario_month_headers = month_headers
    leads_total = sum(row[3] for row in benchmark_months)
    funnel_conversion_label = (
        "Taxa de Conversão Leads → Vendas"
        if is_inside_sales
        else "Taxa de Conversão do Funil"
    )
    final_funnel_rate_label = (
        "Taxa final Leads → Venda"
        if is_inside_sales
        else "Taxa final Sessão → Venda"
    )
    final_rate_volume_row = 20 if is_inside_sales else 16
    final_rate_integrated_row = 41 if is_inside_sales else 37

    projections = []
    minimum_financial = compute_financial_projections(
        revenue_series=projected_revenue,
        media_series=[monthly_media] * projection_months,
        ticket_series=None,
        monthly_fee=monthly_fee,
        base_monthly_media=monthly_media,
        margin=margin,
        current_result=current_result,
        projection_months=projection_months,
        media_lever_after_monthly_breakeven=media_lever_after_breakeven,
        current_ticket=current_ticket,
    )
    for idx in range(projection_months):
        fin = minimum_financial[idx]
        ticket = fin["ticket"]
        revenue = fin["revenue"]
        sales = fin["sales"]
        effective_monthly_media = fin["media"]
        monthly_cost = fin["monthly_cost"]
        monthly_mc = fin["monthly_mc"]
        monthly_result = fin["monthly_result"]
        cumulative_result = fin["cumulative_result"]
        view_rate = cap_conversion_rate(view_rates[idx], max_conversion_rate)
        cart_rate = cap_conversion_rate(cart_rates[idx], max_conversion_rate)
        if has_lead_quali:
            lead_lead_quali = lead_lead_quali_rates[idx]
            lead_quali_mql = lead_quali_mql_rates[idx]
            mql_sql = mql_sql_rates[idx]
            sql_sale = sql_sale_rates[idx]
            final_conversion = (
                view_rate * cart_rate * lead_lead_quali * lead_quali_mql * mql_sql * sql_sale
            )
            lead_rate = cap_conversion_rate(
                lead_lead_quali * lead_quali_mql * mql_sql * sql_sale,
                max_conversion_rate,
            )
        else:
            lead_rate = cap_conversion_rate(lead_to_sale_rates[idx], max_conversion_rate)
            final_conversion = view_rate * cart_rate * lead_rate
        sessions = sales / final_conversion if final_conversion else 0
        max_sessions = effective_monthly_media / min_cost_per_impression if min_cost_per_impression else sessions
        if sessions > max_sessions > 0:
            sessions = max_sessions
        orders = sales / approval_rates[idx]
        cps = effective_monthly_media / sessions if sessions else 0
        cpm = cps * 1000
        projections.append(
            {
                "revenue": revenue,
                "ticket": ticket,
                "sales": sales,
                "orders": orders,
                "sessions": sessions,
                "final_conversion": final_conversion,
                "approval": approval_rates[idx],
                "view_rate": view_rate,
                "cart_rate": cart_rate,
                "cart_to_purchase": cart_to_purchase,
                "monthly_cost": monthly_cost,
                "monthly_media": effective_monthly_media,
                "monthly_mc": monthly_mc,
                "monthly_result": monthly_result,
                "cumulative_result": cumulative_result,
                "cps": cps,
                "cpm": cpm,
                "cpp": effective_monthly_media / orders if orders else 0,
                "cpv": effective_monthly_media / sales if sales else 0,
                "roas": fin["roas"],
            }
        )
    minimum_breakeven_label = breakeven_month_label(projections, projection_months)
    already_historical_breakeven = current_result >= -0.01

    for config in scenario_configs.values():
        extend_scenario_config(config, projection_months)
        if "view_add" not in config:
            config["view_add"] = [
                config["view_cart_share"][idx]
                / (config["session_view"][idx] * config["add_view_cart"][idx])
                for idx in range(projection_months)
            ]

    scenario_financial_plans = {
        name: compute_financial_projections(
            revenue_series=config["revenue"],
            media_series=config["media"],
            ticket_series=config["ticket"],
            monthly_fee=monthly_fee,
            base_monthly_media=monthly_media,
            margin=margin,
            current_result=current_result,
            projection_months=projection_months,
            media_lever_after_monthly_breakeven=media_lever_after_breakeven,
            current_ticket=current_ticket,
        )
        for name, config in scenario_configs.items()
    }

    # Taxas completas do cenário mínimo alinhadas ao funil real (inside sales ou e-commerce).
    realista = scenario_configs["Realista"]
    if has_lead_quali:
        minimum_full_rates = {
            "session_view": view_rates,
            "view_add": cart_rates,
            "add_view_cart": lead_lead_quali_rates,
            "viewcart_checkout": lead_quali_mql_rates,
            "checkout_shipping": mql_sql_rates,
            "shipping_payment": sql_sale_rates,
            "payment_order": realista["payment_order"],
            "order_sale": approval_rates,
        }
    else:
        minimum_full_rates = {
            "session_view": view_rates,
            "view_add": cart_rates,
            "add_view_cart": realista["add_view_cart"],
            "viewcart_checkout": realista["viewcart_checkout"],
            "checkout_shipping": realista["checkout_shipping"],
            "shipping_payment": realista["shipping_payment"],
            "payment_order": realista["payment_order"],
            "order_sale": approval_rates,
        }

    workbook = xlsxwriter.Workbook(output)
    workbook.set_properties(
        {
            "title": f"Projeção Breakeven E-commerce — {client}",
            "subject": "Breakeven, cenário mínimo e funil completo",
            "author": "Colli & Co",
            "company": "V4 Company",
            "comments": "Modelo com fórmulas, premissas editáveis e bench pela mediana dos meses de LT.",
        }
    )
    workbook.set_calc_mode("auto")

    colors = {
        "navy": "#102A43",
        "navy2": "#243B53",
        "teal": "#00A896",
        "green": "#D9EAD3",
        "green_dark": "#38761D",
        "yellow": "#FFF2CC",
        "yellow_dark": "#BF9000",
        "red": "#F4CCCC",
        "red_dark": "#990000",
        "dark_red_2": "#CC0000",
        "blue": "#D9EAF7",
        "gray": "#F3F5F7",
        "gray2": "#D9E2EC",
        "white": "#FFFFFF",
        "text": "#1F2933",
    }

    title = workbook.add_format(
        {
            "font_name": "Arial",
            "bold": True,
            "font_size": 18,
            "font_color": colors["white"],
            "bg_color": colors["dark_red_2"],
            "align": "left",
            "valign": "vcenter",
        }
    )
    section = workbook.add_format(
        {
            "font_name": "Arial",
            "bold": True,
            "font_size": 12,
            "font_color": colors["white"],
            "bg_color": colors["dark_red_2"],
            "align": "left",
            "valign": "vcenter",
            "border": 1,
            "border_color": colors["dark_red_2"],
        }
    )
    header = workbook.add_format(
        {
            "font_name": "Arial",
            "bold": True,
            "font_color": colors["white"],
            "bg_color": colors["teal"],
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "border_color": colors["white"],
        }
    )
    label = workbook.add_format(
        {
            "font_name": "Arial",
            "bold": True,
            "font_color": colors["text"],
            "bg_color": colors["gray"],
            "border": 1,
            "border_color": colors["gray2"],
        }
    )
    input_text = workbook.add_format(
        {
            "font_name": "Arial",
            "bg_color": colors["yellow"],
            "font_color": colors["text"],
            "border": 1,
            "border_color": colors["yellow_dark"],
        }
    )
    input_currency = workbook.add_format(
        {
            "font_name": "Arial",
            "bg_color": colors["yellow"],
            "font_color": colors["text"],
            "border": 1,
            "border_color": colors["yellow_dark"],
            "num_format": 'R$ #,##0.00;[Red]-R$ #,##0.00',
        }
    )
    input_percent = workbook.add_format(
        {
            "font_name": "Arial",
            "bg_color": colors["yellow"],
            "font_color": colors["text"],
            "border": 1,
            "border_color": colors["yellow_dark"],
            "num_format": "0.00%",
        }
    )
    input_int = workbook.add_format(
        {
            "font_name": "Arial",
            "bg_color": colors["yellow"],
            "font_color": colors["text"],
            "border": 1,
            "border_color": colors["yellow_dark"],
            "num_format": "#,##0",
        }
    )
    formula_currency = workbook.add_format(
        {
            "font_name": "Arial",
            "bg_color": colors["green"],
            "font_color": colors["text"],
            "border": 1,
            "border_color": "#A9D18E",
            "num_format": 'R$ #,##0.00;[Red]-R$ #,##0.00',
        }
    )
    formula_percent = workbook.add_format(
        {
            "font_name": "Arial",
            "bg_color": colors["green"],
            "font_color": colors["text"],
            "border": 1,
            "border_color": "#A9D18E",
            "num_format": "0.00%",
        }
    )
    formula_number = workbook.add_format(
        {
            "font_name": "Arial",
            "bg_color": colors["green"],
            "font_color": colors["text"],
            "border": 1,
            "border_color": "#A9D18E",
            "num_format": "#,##0.00",
        }
    )
    formula_int = workbook.add_format(
        {
            "font_name": "Arial",
            "bg_color": colors["green"],
            "font_color": colors["text"],
            "border": 1,
            "border_color": "#A9D18E",
            "num_format": "#,##0",
        }
    )
    normal = workbook.add_format(
        {
            "font_name": "Arial",
            "font_color": colors["text"],
            "border": 1,
            "border_color": colors["gray2"],
        }
    )
    normal_currency = workbook.add_format(
        {
            "font_name": "Arial",
            "font_color": colors["text"],
            "border": 1,
            "border_color": colors["gray2"],
            "num_format": 'R$ #,##0.00;[Red]-R$ #,##0.00',
        }
    )
    normal_percent = workbook.add_format(
        {
            "font_name": "Arial",
            "font_color": colors["text"],
            "border": 1,
            "border_color": colors["gray2"],
            "num_format": "0.00%",
        }
    )
    normal_int = workbook.add_format(
        {
            "font_name": "Arial",
            "font_color": colors["text"],
            "border": 1,
            "border_color": colors["gray2"],
            "num_format": "#,##0",
        }
    )
    note = workbook.add_format(
        {
            "font_name": "Arial",
            "font_color": "#52616B",
            "font_size": 9,
            "italic": True,
            "text_wrap": True,
            "valign": "top",
        }
    )
    card_label = workbook.add_format(
        {
            "font_name": "Arial",
            "bold": True,
            "font_color": colors["navy2"],
            "bg_color": colors["blue"],
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "border_color": "#9CC2E5",
        }
    )
    card_value = workbook.add_format(
        {
            "font_name": "Arial",
            "bold": True,
            "font_size": 15,
            "font_color": colors["navy"],
            "bg_color": colors["white"],
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "border_color": "#9CC2E5",
            "num_format": 'R$ #,##0.00;[Red]-R$ #,##0.00',
        }
    )
    status_ok = workbook.add_format(
        {
            "font_name": "Arial",
            "bold": True,
            "font_color": colors["green_dark"],
            "bg_color": colors["green"],
            "align": "center",
            "border": 1,
            "border_color": "#A9D18E",
        }
    )
    status_bad = workbook.add_format(
        {
            "font_name": "Arial",
            "bold": True,
            "font_color": colors["red_dark"],
            "bg_color": colors["red"],
            "align": "center",
            "border": 1,
            "border_color": "#E6B8B7",
        }
    )
    status_ok_small = workbook.add_format(
        {
            "font_name": "Arial",
            "bold": True,
            "font_size": 9,
            "font_color": colors["green_dark"],
            "bg_color": colors["green"],
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
            "border": 1,
            "border_color": "#A9D18E",
        }
    )
    status_bad_small = workbook.add_format(
        {
            "font_name": "Arial",
            "bold": True,
            "font_size": 9,
            "font_color": colors["red_dark"],
            "bg_color": colors["red"],
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
            "border": 1,
            "border_color": "#E6B8B7",
        }
    )

    def write_scenario_sheet(name, config):
        """Cria uma aba de cenário com finanças e funil completo integrados."""
        ws = workbook.add_worksheet(name)
        ws.set_tab_color(config["tab_color"])
        ws.hide_gridlines(2)
        ws.freeze_panes(2, 5)
        ws.set_column("A:A", 38)
        ws.set_column("B:B", 24)
        ws.set_column("C:D", 19)
        ws.set_column("E:E", 3)
        ws.set_column(f"F:{scen_proj_last_name}", 15)
        ws.merge_range(f"A1:{scen_sheet_last_name}1", f"Breakeven {name} — {client}", title)
        headers = [
            "",
            scenario_actual_column_label(config_data),
            "Breakeven da\ncompetência",
            "Total projetado",
            "",
            *scenario_month_headers,
        ]
        ws.set_row(1, 32)
        for col, text in enumerate(headers):
            ws.write(1, col, text, header if col != 4 else normal)

        financial_rows = {
            3: "Fee V4",
            4: "Investimento de mídia",
            5: "Custo total",
            6: "Faturamento",
            7: "Ticket médio",
            8: "Margem de contribuição",
            9: "Resultado MC",
            10: "Resultado líquido do mês",
            11: "Resultado líquido acumulado",
            12: "ROAS",
            13: "Status",
        }
        for row_num, text in financial_rows.items():
            ws.write(row_num - 1, 0, text, label)

        current_financial = {
            3: fee_total,
            4: media_total,
            5: current_cost,
            6: revenue_total,
            7: current_ticket,
            8: margin,
            9: current_mc,
            10: current_result,
            11: current_result,
            12: revenue_total / media_total,
        }
        for row_num, value in current_financial.items():
            fmt = formula_percent if row_num == 8 else formula_number if row_num == 12 else formula_currency
            ws.write_number(row_num - 1, 1, value, fmt)
        ws.write(12, 1, "Déficit a recuperar", status_bad_small)

        competence_revenue = (monthly_fee + config["media"][0]) / margin
        competence_ticket = config["ticket"][0]
        competence_financial = {
            3: monthly_fee,
            4: config["media"][0],
            5: monthly_fee + config["media"][0],
            6: competence_revenue,
            7: competence_ticket,
            8: margin,
            9: competence_revenue * margin,
            10: 0,
            11: 0,
            12: competence_revenue / config["media"][0],
        }
        competence_formulas = {
            3: "='Premissas'!F4",
            4: "=F4",
            5: "=C3+C4",
            6: "=C5/C8",
            7: "=F7",
            8: "='Premissas'!F7",
            9: "=C6*C8",
            10: "=C9-C5",
            11: "=C10",
            12: "=C6/C4",
        }
        for row_num, value in competence_financial.items():
            fmt = formula_percent if row_num == 8 else formula_number if row_num == 12 else formula_currency
            ws.write_formula(row_num - 1, 2, competence_formulas[row_num], fmt, value)
        ws.write(12, 2, "ZERA A COMPETÊNCIA", status_ok_small)

        financial_plan = scenario_financial_plans[name]
        cached_months = []
        for idx in range(projection_months):
            fin = financial_plan[idx]
            revenue = fin["revenue"]
            media = fin["media"]
            ticket = fin["ticket"]
            fee = monthly_fee
            cost = fin["monthly_cost"]
            mc = fin["monthly_mc"]
            result = fin["monthly_result"]
            cumulative = fin["cumulative_result"]
            sales = fin["sales"]
            if is_inside_sales:
                funnel_volumes = build_inside_sales_funnel_volumes(
                    sales,
                    inside_sales_funnel_rates(config, idx, has_lead_quali),
                    has_lead_quali=has_lead_quali,
                )
                orders = funnel_volumes["checkout"]
                payment = funnel_volumes["payment"]
                shipping = funnel_volumes["shipping"]
                checkout = funnel_volumes["checkout"]
                view_cart = funnel_volumes["view_cart"]
                add_cart = funnel_volumes["add_cart"]
                view_item = funnel_volumes["view_item"]
                sessions = funnel_volumes["sessions"]
            else:
                orders = sales / config["order_sale"][idx]
                payment = orders / config["payment_order"][idx]
                shipping = payment / config["shipping_payment"][idx]
                checkout = shipping / config["checkout_shipping"][idx]
                view_cart = checkout / config["viewcart_checkout"][idx]
                add_cart = view_cart / config["add_view_cart"][idx]
                view_item = add_cart / config["view_add"][idx]
                sessions = view_item / config["session_view"][idx]
            cached_months.append(
                {
                    "fee": fee,
                    "media": media,
                    "cost": cost,
                    "revenue": revenue,
                    "ticket": ticket,
                    "mc": mc,
                    "result": result,
                    "cumulative": cumulative,
                    "roas": fin["roas"],
                    "sessions": sessions,
                    "view_item": view_item,
                    "add_cart": add_cart,
                    "view_cart": view_cart,
                    "begin_checkout": funnel_volumes.get("begin_checkout", checkout) if is_inside_sales else checkout,
                    "checkout": checkout,
                    "shipping": shipping,
                    "payment": payment,
                    "orders": orders,
                    "sales": sales,
                }
            )

        for idx, cached in enumerate(cached_months):
            col = 5 + idx
            col_name = xlsxwriter.utility.xl_col_to_name(col)
            previous_col = xlsxwriter.utility.xl_col_to_name(col - 1)
            values = {
                3: cached["fee"],
                4: cached["media"],
                5: cached["cost"],
                6: cached["revenue"],
                7: cached["ticket"],
                8: margin,
                9: cached["mc"],
                10: cached["result"],
                11: cached["cumulative"],
                12: cached["roas"],
            }
            formulas = {
                3: "='Premissas'!F4",
                4: None,
                5: f"={col_name}3+{col_name}4",
                6: None,
                7: None,
                8: "='Premissas'!F7",
                9: f"={col_name}6*{col_name}8",
                10: f"={col_name}9-{col_name}5",
                11: (
                    f"=ROUND($B11+{col_name}10,2)"
                    if idx == 0
                    else f"=ROUND({previous_col}11+{col_name}10,2)"
                ),
                12: f"={col_name}6/{col_name}4",
            }
            for row_num, value in values.items():
                fmt = input_percent if row_num == 8 else input_currency if row_num in (4, 6, 7) else formula_number if row_num == 12 else formula_currency
                if formulas[row_num] is None:
                    ws.write_number(row_num - 1, col, value, fmt)
                else:
                    calc_fmt = formula_percent if row_num == 8 else formula_number if row_num == 12 else formula_currency
                    ws.write_formula(row_num - 1, col, formulas[row_num], calc_fmt, value)
            ws.write_formula(
                12,
                col,
                f'=IF({col_name}11>=0,"BREAKEVEN","EM RECUPERAÇÃO")',
                status_ok_small if cached["cumulative"] >= 0 else status_bad_small,
                "BREAKEVEN" if cached["cumulative"] >= 0 else "EM RECUPERAÇÃO",
            )

        total_financial = {
            3: projection_months * monthly_fee,
            4: sum(fin["media"] for fin in financial_plan),
            5: projection_months * monthly_fee + sum(fin["media"] for fin in financial_plan),
            6: sum(config["revenue"]),
            7: sum(config["revenue"]) / sum(x["sales"] for x in cached_months),
            8: margin,
            9: sum(config["revenue"]) * margin,
            10: sum(config["revenue"]) * margin - (projection_months * monthly_fee + sum(fin["media"] for fin in financial_plan)),
            11: cached_months[-1]["cumulative"],
            12: sum(config["revenue"]) / sum(fin["media"] for fin in financial_plan),
        }
        total_formulas = {
            3: f"=SUM(F3:{scen_proj_last_name}3)",
            4: f"=SUM(F4:{scen_proj_last_name}4)",
            5: f"=SUM(F5:{scen_proj_last_name}5)",
            6: f"=SUM(F6:{scen_proj_last_name}6)",
            7: "=D6/D32",
            8: "='Premissas'!F7",
            9: "=D6*D8",
            10: "=D9-D5",
            11: f"={scen_proj_last_name}11",
            12: "=D6/D4",
        }
        for row_num, value in total_financial.items():
            fmt = formula_percent if row_num == 8 else formula_number if row_num == 12 else formula_currency
            ws.write_formula(row_num - 1, 3, total_formulas[row_num], fmt, value)
        ws.write_formula(
            12,
            3,
            '=IF(D11>=0,"BREAKEVEN ATINGIDO","NÃO BREAKEVA")',
            status_ok_small if cached_months[-1]["cumulative"] >= 0 else status_bad_small,
            "BREAKEVEN ATINGIDO" if cached_months[-1]["cumulative"] >= 0 else "NÃO BREAKEVA",
        )

        ws.merge_range(f"A15:{scen_sheet_last_name}15", "Funil completo mês a mês", section)
        funnel_rows = scenario_funnel_row_labels(is_inside_sales, final_funnel_rate_label, has_lead_quali)
        for row_num, text in funnel_rows.items():
            ws.write(row_num - 1, 0, text, label)

        if is_inside_sales:
            if has_lead_quali:
                actual_rates = {
                    17: current_view_item / current_sessions,
                    19: current_add_cart / current_view_item,
                    21: min(max_conversion_rate, current_view_cart / current_add_cart),
                    23: current_checkout / current_view_cart if current_view_cart else 0,
                    25: current_shipping / current_checkout if current_checkout else 0,
                    27: current_sales / current_shipping if current_shipping else 0,
                }
                actual_volumes = {
                    16: current_sessions,
                    18: current_view_item,
                    20: current_add_cart,
                    22: current_view_cart,
                    24: current_checkout,
                    26: current_shipping,
                    32: current_sales,
                    33: current_lead_to_sale,
                    34: current_month_media / current_sessions if current_sessions else 0,
                    35: current_month_media / current_shipping if current_shipping else 0,
                    36: current_month_media / current_sales if current_sales else 0,
                    37: current_month_revenue,
                    38: 0,
                }
            else:
                actual_rates = {
                    17: current_view_item / current_sessions,
                    19: current_add_cart / current_view_item,
                    21: min(max_conversion_rate, current_view_cart / current_add_cart),
                    23: current_checkout / current_view_cart,
                    25: current_sales / current_checkout if current_checkout else 0,
                }
                actual_volumes = {
                    16: current_sessions,
                    18: current_view_item,
                    20: current_add_cart,
                    22: current_view_cart,
                    24: current_checkout,
                    32: current_sales,
                    33: current_lead_to_sale,
                    34: current_month_media / current_sessions,
                    35: current_month_media / current_checkout if current_checkout else 0,
                    36: current_month_media / current_sales,
                    37: current_month_revenue,
                    38: 0,
                }
        else:
            actual_rates = {
                17: current_view_item / current_sessions,
                19: current_add_cart / current_view_item,
                21: min(1, current_view_cart / current_add_cart),
                23: current_checkout / current_view_cart,
                25: min(1, current_shipping / current_checkout),
                27: current_payment / current_shipping,
                29: current_orders / current_payment,
                31: current_sales / current_orders,
            }
            actual_volumes = {
                16: current_sessions,
                18: current_view_item,
                20: current_add_cart,
                22: current_view_cart,
                24: current_checkout,
                26: current_shipping,
                28: current_payment,
                30: current_orders,
                32: current_sales,
                33: current_lead_to_sale if is_inside_sales else current_sales / current_sessions,
                34: current_month_media / current_sessions,
                35: current_month_media / current_orders,
                36: current_month_media / current_sales,
                37: current_month_revenue,
                38: 0,
            }
        for row_num, value in {**actual_rates, **actual_volumes}.items():
            fmt = formula_percent if row_num in (*actual_rates.keys(), 33) else formula_currency if row_num in (34, 35, 36, 37, 38) else formula_int
            ws.write_number(row_num - 1, 1, value, fmt)

        competence_sales = competence_revenue / competence_ticket
        if is_inside_sales:
            competence_rates = inside_sales_funnel_rates(config, 0, has_lead_quali)
            competence_volumes = build_inside_sales_funnel_volumes(
                competence_sales,
                competence_rates,
                has_lead_quali=has_lead_quali,
            )
            competence_sessions = competence_volumes["sessions"]
            competence_view_item = competence_volumes["view_item"]
            competence_add_cart = competence_volumes["add_cart"]
            competence_view_cart = competence_volumes["view_cart"]
            competence_checkout = competence_volumes["begin_checkout"]
            competence_shipping = competence_volumes["checkout"]
            competence_orders = competence_shipping
            competence_payment = competence_sales
        else:
            competence_orders = competence_sales / config["order_sale"][0]
            competence_payment = competence_orders / config["payment_order"][0]
            competence_shipping = competence_payment / config["shipping_payment"][0]
            competence_checkout = competence_shipping / config["checkout_shipping"][0]
            competence_view_cart = competence_checkout / config["viewcart_checkout"][0]
            competence_add_cart = competence_view_cart / config["add_view_cart"][0]
            competence_view_item = competence_add_cart / config["view_add"][0]
            competence_sessions = competence_view_item / config["session_view"][0]
        if is_inside_sales:
            competence_rate_values = inside_sales_scenario_rate_values(config, 0, has_lead_quali)
        else:
            competence_rate_values = {
                17: config["session_view"][0],
                19: config["view_add"][0],
                21: config["add_view_cart"][0],
                23: config["viewcart_checkout"][0],
                25: config["checkout_shipping"][0],
                27: config["shipping_payment"][0],
                29: config["payment_order"][0],
                31: config["order_sale"][0],
            }
        for row_num, value in competence_rate_values.items():
            ws.write_formula(row_num - 1, 2, f"=F{row_num}", formula_percent, value)
        if is_inside_sales:
            if has_lead_quali:
                competence_volume_values = {
                    16: competence_sessions,
                    18: competence_view_item,
                    20: competence_add_cart,
                    22: competence_view_cart,
                    24: competence_checkout,
                    26: competence_shipping,
                    32: competence_sales,
                    33: competence_sales / competence_add_cart if competence_add_cart else 0,
                    34: config["media"][0] / competence_sessions if competence_sessions else 0,
                    35: config["media"][0] / competence_shipping if competence_shipping else 0,
                    36: config["media"][0] / competence_sales if competence_sales else 0,
                    37: competence_revenue,
                    38: 0,
                }
            else:
                competence_volume_values = {
                    16: competence_sessions,
                    18: competence_view_item,
                    20: competence_add_cart,
                    22: competence_view_cart,
                    24: competence_checkout,
                    32: competence_sales,
                    33: competence_sales / competence_add_cart if competence_add_cart else 0,
                    34: config["media"][0] / competence_sessions,
                    35: config["media"][0] / competence_checkout if competence_checkout else 0,
                    36: config["media"][0] / competence_sales,
                    37: competence_revenue,
                    38: 0,
                }
            competence_volume_formulas = inside_sales_scenario_volume_formulas("C", final_rate_volume_row, has_lead_quali)
        else:
            competence_volume_values = {
                16: competence_sessions,
                18: competence_view_item,
                20: competence_add_cart,
                22: competence_view_cart,
                24: competence_checkout,
                26: competence_shipping,
                28: competence_payment,
                30: competence_orders,
                32: competence_sales,
                33: competence_sales / competence_add_cart if is_inside_sales else competence_sales / competence_sessions,
                34: config["media"][0] / competence_sessions,
                35: config["media"][0] / competence_orders,
                36: config["media"][0] / competence_sales,
                37: competence_revenue,
                38: 0,
            }
            competence_volume_formulas = {
                32: "=C6/C7",
                30: "=C32/C31",
                28: "=C30/C29",
                26: "=C28/C27",
                24: "=C26/C25",
                22: "=C24/C23",
                20: "=C22/C21",
                18: "=C20/C19",
                16: "=C18/C17",
                33: f"=C32/C{final_rate_volume_row}",
                34: "=C4/C16",
                35: "=C4/C30",
                36: "=C4/C32",
                37: "=C32*C7",
                38: "=ROUND(C37-C6,2)",
            }
        for row_num, formula in competence_volume_formulas.items():
            fmt = formula_percent if row_num == 33 else formula_currency if row_num in (34, 35, 36, 37, 38) else formula_int
            ws.write_formula(row_num - 1, 2, formula, fmt, competence_volume_values[row_num])

        for idx, cached in enumerate(cached_months):
            col = 5 + idx
            col_name = xlsxwriter.utility.xl_col_to_name(col)
            if is_inside_sales:
                rate_values = inside_sales_scenario_rate_values(config, idx, has_lead_quali)
            else:
                rate_values = {
                    17: config["session_view"][idx],
                    19: config["view_add"][idx],
                    21: config["add_view_cart"][idx],
                    23: config["viewcart_checkout"][idx],
                    25: config["checkout_shipping"][idx],
                    27: config["shipping_payment"][idx],
                    29: config["payment_order"][idx],
                    31: config["order_sale"][idx],
                }
            for row_num, value in rate_values.items():
                ws.write_number(row_num - 1, col, value, input_percent)
            if is_inside_sales:
                volume_values = {
                    16: cached["sessions"],
                    18: cached["view_item"],
                    20: cached["add_cart"],
                    22: cached["view_cart"],
                    24: cached["begin_checkout"] if has_lead_quali else cached["checkout"],
                    32: cached["sales"],
                    33: cached["sales"] / cached["add_cart"] if cached["add_cart"] else 0,
                    34: cached["media"] / cached["sessions"] if cached["sessions"] else 0,
                    36: cached["media"] / cached["sales"] if cached["sales"] else 0,
                    37: cached["sales"] * cached["ticket"],
                    38: 0,
                }
                if has_lead_quali:
                    volume_values[26] = cached["checkout"]
                    volume_values[35] = cached["media"] / cached["checkout"] if cached["checkout"] else 0
                else:
                    volume_values[35] = cached["media"] / cached["checkout"] if cached["checkout"] else 0
                volume_formulas = inside_sales_scenario_volume_formulas(col_name, final_rate_volume_row, has_lead_quali)
            else:
                volume_values = {
                    16: cached["sessions"],
                    18: cached["view_item"],
                    20: cached["add_cart"],
                    22: cached["view_cart"],
                    24: cached["checkout"],
                    26: cached["shipping"],
                    28: cached["payment"],
                    30: cached["orders"],
                    32: cached["sales"],
                    33: cached["sales"] / cached["sessions"],
                    34: cached["media"] / cached["sessions"],
                    35: cached["media"] / cached["orders"],
                    36: cached["media"] / cached["sales"],
                    37: cached["sales"] * cached["ticket"],
                    38: 0,
                }
                volume_formulas = {
                    32: f"={col_name}6/{col_name}7",
                    30: f"={col_name}32/{col_name}31",
                    28: f"={col_name}30/{col_name}29",
                    26: f"={col_name}28/{col_name}27",
                    24: f"={col_name}26/{col_name}25",
                    22: f"={col_name}24/{col_name}23",
                    20: f"={col_name}22/{col_name}21",
                    18: f"={col_name}20/{col_name}19",
                    16: f"={col_name}18/{col_name}17",
                    33: f"={col_name}32/{col_name}{final_rate_volume_row}",
                    34: f"={col_name}4/{col_name}16",
                    35: f"={col_name}4/{col_name}30",
                    36: f"={col_name}4/{col_name}32",
                    37: f"={col_name}32*{col_name}7",
                    38: f"=ROUND({col_name}37-{col_name}6,2)",
                }
            for row_num, formula in volume_formulas.items():
                fmt = formula_percent if row_num == 33 else formula_currency if row_num in (34, 35, 36, 37, 38) else formula_int
                ws.write_formula(row_num - 1, col, formula, fmt, volume_values[row_num])

        if is_inside_sales:
            if has_lead_quali:
                aggregate_funnel = {
                    16: sum(x["sessions"] for x in cached_months),
                    18: sum(x["view_item"] for x in cached_months),
                    20: sum(x["add_cart"] for x in cached_months),
                    22: sum(x["view_cart"] for x in cached_months),
                    24: sum(x["begin_checkout"] for x in cached_months),
                    26: sum(x["checkout"] for x in cached_months),
                    32: sum(x["sales"] for x in cached_months),
                }
                aggregate_rate_formulas = {
                    17: "=D18/D16",
                    19: "=D20/D18",
                    21: "=D22/D20",
                    23: "=D24/D22",
                    25: "=D26/D24",
                    27: "=D32/D26",
                    33: f"=D32/D{final_rate_volume_row}",
                }
                aggregate_rate_pairs = {
                    17: (18, 16),
                    19: (20, 18),
                    21: (22, 20),
                    23: (24, 22),
                    25: (26, 24),
                    27: (32, 26),
                    33: (32, final_rate_volume_row),
                }
            else:
                aggregate_funnel = {
                    16: sum(x["sessions"] for x in cached_months),
                    18: sum(x["view_item"] for x in cached_months),
                    20: sum(x["add_cart"] for x in cached_months),
                    22: sum(x["view_cart"] for x in cached_months),
                    24: sum(x["checkout"] for x in cached_months),
                    32: sum(x["sales"] for x in cached_months),
                }
                aggregate_rate_formulas = {
                    17: "=D18/D16",
                    19: "=D20/D18",
                    21: "=D22/D20",
                    23: "=D24/D22",
                    25: "=D32/D24",
                    33: f"=D32/D{final_rate_volume_row}",
                }
                aggregate_rate_pairs = {
                    17: (18, 16),
                    19: (20, 18),
                    21: (22, 20),
                    23: (24, 22),
                    25: (32, 24),
                    33: (32, final_rate_volume_row),
                }
        else:
            aggregate_funnel = {
                16: sum(x["sessions"] for x in cached_months),
                18: sum(x["view_item"] for x in cached_months),
                20: sum(x["add_cart"] for x in cached_months),
                22: sum(x["view_cart"] for x in cached_months),
                24: sum(x["checkout"] for x in cached_months),
                26: sum(x["shipping"] for x in cached_months),
                28: sum(x["payment"] for x in cached_months),
                30: sum(x["orders"] for x in cached_months),
                32: sum(x["sales"] for x in cached_months),
            }
            aggregate_rate_formulas = {
                17: "=D18/D16",
                19: "=D20/D18",
                21: "=D22/D20",
                23: "=D24/D22",
                25: "=D26/D24",
                27: "=D28/D26",
                29: "=D30/D28",
                31: "=D32/D30",
                33: f"=D32/D{final_rate_volume_row}",
            }
            aggregate_rate_pairs = {
                17: (18, 16),
                19: (20, 18),
                21: (22, 20),
                23: (24, 22),
                25: (26, 24),
                27: (28, 26),
                29: (30, 28),
                31: (32, 30),
                33: (32, final_rate_volume_row),
            }
        for row_num, value in aggregate_funnel.items():
            ws.write_formula(row_num - 1, 3, f"=SUM(F{row_num}:{scen_proj_last_name}{row_num})", formula_int, value)
        for row_num, formula in aggregate_rate_formulas.items():
            if row_num == 33:
                cached_value = aggregate_funnel[32] / aggregate_funnel[final_rate_volume_row]
            else:
                numerator, denominator = aggregate_rate_pairs[row_num]
                cached_value = aggregate_funnel[numerator] / aggregate_funnel[denominator]
            ws.write_formula(row_num - 1, 3, formula, formula_percent, cached_value)
        ws.write_formula(33, 3, "=D4/D16", formula_currency, total_financial[4] / aggregate_funnel[16])
        if is_inside_sales:
            sql_row = 26 if has_lead_quali else 24
            ws.write_formula(34, 3, f"=D4/D{sql_row}", formula_currency, total_financial[4] / aggregate_funnel[sql_row])
        else:
            ws.write_formula(34, 3, "=D4/D30", formula_currency, total_financial[4] / aggregate_funnel[30])
        ws.write_formula(35, 3, "=D4/D32", formula_currency, total_financial[4] / aggregate_funnel[32])
        ws.write_formula(36, 3, "=D32*D7", formula_currency, total_financial[6])
        ws.write_formula(37, 3, "=ROUND(D37-D6,2)", formula_currency, 0)

        ws.conditional_format(f"F11:{scen_proj_last_name}11", {"type": "cell", "criteria": "<", "value": 0, "format": status_bad})
        ws.conditional_format(f"F11:{scen_proj_last_name}11", {"type": "cell", "criteria": ">=", "value": 0, "format": status_ok})
        ws.merge_range(
            f"A41:{scen_sheet_last_name}43",
            "A coluna Breakeven da competência mostra o funil necessário para pagar Fee + mídia do mês, sem recuperar o carry over. Células amarelas são premissas do cenário; os volumes são calculados de trás para frente.",
            note,
        )
        return ws

    # Dados Fonte
    data = workbook.add_worksheet("Dados Fonte")
    data.set_tab_color(colors["navy2"])
    data.hide_gridlines(2)
    data.freeze_panes(4, 0)
    data.set_column("A:A", 19)
    data.set_column("B:D", 19)
    data.set_column("E:G", 17)
    data.set_column("H:H", 24)
    data.set_column("I:I", 18)
    data.merge_range("A1:I1", f"Dados Fonte — {client}", title)
    data.write("A3", "Mês", header)
    data.write("B3", "Fee V4", header)
    data.write("C3", "Investimento", header)
    if is_inside_sales:
        data.write("D3", "Impressões", header)
        data.write("E3", "SQLs", header)
    else:
        data.write("D3", "Sessões", header)
        data.write("E3", "Pedidos", header)
    data.write("F3", "Vendas", header)
    data.write("G3", "Faturamento", header)
    data.write("H3", "Período válido", header)
    for row_idx, row in enumerate(source_months, 3):
        month, fee, media, sessions, orders, sales, revenue = row
        data.write(row_idx, 0, month, normal)
        data.write_number(row_idx, 1, fee, normal_currency)
        data.write_number(row_idx, 2, media, normal_currency)
        data.write_number(row_idx, 3, sessions, normal_int)
        data.write_number(row_idx, 4, orders, normal_int)
        data.write_number(row_idx, 5, sales, normal_int)
        data.write_number(row_idx, 6, revenue, normal_currency)
        data.write(row_idx, 7, "Sim — mês com fee", normal)
    total_row = 3 + len(source_months)
    data.write(total_row, 0, "TOTAL", label)
    for col in range(1, 7):
        fmt = normal_currency if col in (1, 2, 6) else normal_int
        data.write_formula(
            total_row,
            col,
            f"=SUM({xlsxwriter.utility.xl_col_to_name(col)}4:{xlsxwriter.utility.xl_col_to_name(col)}{total_row})",
            fmt,
            [fee_total, media_total, sessions_total, orders_total, sales_total, revenue_total][col - 1],
        )
    data.write(total_row, 7, "Somente meses com Fee V4", label)

    funnel_first_row = 16
    funnel_summary_row = funnel_first_row + len(current_funnel)
    funnel_leads_row = funnel_first_row + 2
    funnel_last_row = funnel_first_row + len(current_funnel) - 1

    data.merge_range("A15:F15", f"Funil atual — {current_period}", section)
    for col, text in enumerate(["Etapa", "Volume", "Taxa atual", "Bench interno", "Status", "Fonte"]):
        data.write(15, col, text, header)
    for idx, row in enumerate(current_funnel, funnel_first_row):
        stage, volume, rate, bench, status = row
        data.write(idx, 0, stage, normal)
        data.write_number(idx, 1, volume, normal_int)
        if rate is None:
            data.write(idx, 2, "-", normal)
        else:
            data.write_number(idx, 2, rate, normal_percent)
        if bench is None:
            data.write(idx, 3, "-", normal)
        else:
            data.write_number(idx, 3, bench, normal_percent)
        data.write(idx, 4, status, status_bad if "sequencial" in status or "duplicidade" in status else normal)
        data.write(idx, 5, "GA4 / Growth Pack", normal)
    summary_label = "Leads → Vendas" if is_inside_sales else "Sessão → Purchase"
    if is_inside_sales:
        summary_rate = current_sales / current_add_cart if current_add_cart else 0
        summary_formula = f"=B{funnel_last_row + 1}/B{funnel_leads_row + 1}"
        summary_bench = bench_lead_to_sale
    else:
        summary_rate = current_purchase / current_sessions
        summary_formula = f"=B{funnel_last_row + 1}/B{funnel_first_row + 1}"
        summary_bench = bench_session_purchase
    data.write(funnel_summary_row, 0, summary_label, label)
    data.write_formula(
        funnel_summary_row, 1, summary_formula, formula_percent, summary_rate
    )
    data.write_number(
        funnel_summary_row, 2, summary_rate, normal_percent
    )
    data.write_number(funnel_summary_row, 3, summary_bench, normal_percent)
    data.write(funnel_summary_row, 4, f"Bench: mediana {len(benchmark_months)}M", normal)
    data.write(funnel_summary_row, 5, config_data["lt_period"], normal)
    source_mapping = config_data.get("source_mapping", {})
    data.merge_range(
        "A29:I31",
        (
            f"Fonte: Growth Pack {client}. O cenário financeiro usa Fee V4 "
            f"{source_mapping.get('fee', '')}, investimento "
            f"{source_mapping.get('media', '')} e faturamento "
            f"{source_mapping.get('revenue', '')}, apenas nos meses válidos."
        ),
        note,
    )

    if is_inside_sales:
        if has_lead_quali:
            event_headers = ["Mês", "Impressões", "Cliques", "Leads", "Lead quali", "MQLs", "SQLs", "Vendas"]
            bench_last_col_name = "H"
        else:
            event_headers = ["Mês", "Impressões", "Cliques", "Leads", "MQLs", "SQLs", "Vendas"]
            bench_last_col_name = "G"
    else:
        event_headers = [
            "Mês",
            "Sessões",
            "View item",
            "Add to cart",
            "View cart",
            "Begin checkout",
            "Add shipping info",
            "Add payment info",
            "Purchase",
        ]
        bench_last_col_name = "I"
    data.merge_range(f"A34:{bench_last_col_name}34", "Base mensal do bench — volumes de eventos", section)
    for col, text in enumerate(event_headers):
        data.write(34, col, text, header)
    for row_idx, row in enumerate(benchmark_months, 35):
        month, sessions, view_item, add_cart, view_cart, checkout, _shipping, _payment, purchase = row
        data.write(row_idx, 0, month, normal)
        if is_inside_sales:
            if has_lead_quali:
                values = [sessions, view_item, add_cart, view_cart, checkout, shipping, purchase]
            else:
                values = [sessions, view_item, add_cart, view_cart, checkout, purchase]
        else:
            values = list(row[1:])
        for col, value in enumerate(values, 1):
            data.write_number(row_idx, col, value, normal_int)

    rate_title_excel_row = 38 + len(benchmark_months)
    rate_header_idx = rate_title_excel_row
    rate_data_start_idx = rate_header_idx + 1
    data.merge_range(
        f"A{rate_title_excel_row}:{bench_last_col_name}{rate_title_excel_row}",
        f"Bench interno — taxas mensais e mediana dos {len(benchmark_months)} meses",
        section,
    )
    if is_inside_sales:
        if has_lead_quali:
            rate_headers = [
                "Mês",
                "Impressões → Cliques",
                "Cliques → Leads",
                "Leads → Lead quali",
                "Lead quali → MQLs",
                "MQLs → SQLs",
                "SQLs → Vendas",
                "Leads → Vendas",
            ]
        else:
            rate_headers = [
                "Mês",
                "Impressões → Cliques",
                "Cliques → Leads",
                "Leads → MQLs",
                "MQLs → SQLs",
                "SQLs → Vendas",
                "Leads → Vendas",
            ]
    else:
        rate_headers = [
            "Mês",
            "Sessão → View item",
            "View item → Add cart",
            "Add to cart → View cart",
            "View cart → Checkout",
            "Checkout → Shipping",
            "Shipping → Payment",
            "Payment → Purchase",
            "Sessão → Purchase",
        ]
    for col, text in enumerate(rate_headers):
        data.write(rate_header_idx, col, text, header)
    for offset, row in enumerate(benchmark_rates):
        row_idx = rate_data_start_idx + offset
        data.write(row_idx, 0, row[0], normal)
        source_row = 36 + offset
        if is_inside_sales:
            if has_lead_quali:
                rate_formulas = [
                    f"=MIN({max_conversion_rate},C{source_row}/B{source_row})",
                    f"=MIN({max_conversion_rate},D{source_row}/C{source_row})",
                    f"=MIN({max_conversion_rate},E{source_row}/D{source_row})",
                    f"=MIN({max_conversion_rate},F{source_row}/E{source_row})",
                    f"=MIN({max_conversion_rate},G{source_row}/F{source_row})",
                    f"=MIN({max_conversion_rate},H{source_row}/G{source_row})",
                    f"=MIN({max_conversion_rate},H{source_row}/D{source_row})",
                ]
                month_data = benchmark_months[offset]
                _, _, _, add_cart, _, _, _, _, purchase = month_data
                lead_to_sale = min(max_conversion_rate, purchase / add_cart) if add_cart else 0
                rate_values = (row[1], row[2], row[3], row[4], row[5], row[6], lead_to_sale)
            else:
                rate_formulas = [
                    f"=MIN({max_conversion_rate},C{source_row}/B{source_row})",
                    f"=MIN({max_conversion_rate},D{source_row}/C{source_row})",
                    f"=MIN({max_conversion_rate},E{source_row}/D{source_row})",
                    f"=MIN({max_conversion_rate},F{source_row}/E{source_row})",
                    f"=MIN({max_conversion_rate},G{source_row}/F{source_row})",
                    f"=MIN({max_conversion_rate},G{source_row}/D{source_row})",
                ]
                month_data = benchmark_months[offset]
                _, _, _, add_cart, _, _, _, _, purchase = month_data
                lead_to_sale = min(max_conversion_rate, purchase / add_cart) if add_cart else 0
                rate_values = (row[1], row[2], row[3], row[4], row[6], lead_to_sale)
        else:
            rate_formulas = [
                f"=MIN(1,C{source_row}/B{source_row})",
                f"=MIN(1,D{source_row}/C{source_row})",
                f"=MIN(1,E{source_row}/D{source_row})",
                f"=MIN(1,F{source_row}/E{source_row})",
                f"=MIN(1,G{source_row}/F{source_row})",
                f"=MIN(1,H{source_row}/G{source_row})",
                f"=MIN(1,I{source_row}/H{source_row})",
                f"=MIN(1,I{source_row}/B{source_row})",
            ]
            rate_values = row[1:]
        for col, (formula, value) in enumerate(zip(rate_formulas, rate_values), 1):
            data.write_formula(row_idx, col, formula, formula_percent, value)
    median_row = rate_data_start_idx + len(benchmark_months)
    data.write(median_row, 0, f"MEDIANA {len(benchmark_months)}M", label)
    rate_first_excel_row = rate_data_start_idx + 1
    rate_last_excel_row = rate_data_start_idx + len(benchmark_months)
    median_values = (
        [
            bench_session_view,
            bench_view_add,
            bench_add_viewcart,
            bench_viewcart_checkout,
            bench_checkout_shipping,
            bench_shipping_payment,
            bench_lead_to_sale,
        ]
        if is_inside_sales and has_lead_quali
        else [
            bench_session_view,
            bench_view_add,
            bench_add_viewcart,
            bench_viewcart_checkout,
            bench_shipping_payment,
            bench_lead_to_sale,
        ]
        if is_inside_sales
        else list(benchmark_medians)
    )
    for col, value in enumerate(median_values, 1):
        col_name = xlsxwriter.utility.xl_col_to_name(col)
        data.write_formula(
            median_row,
            col,
            f"=MEDIAN({col_name}{rate_first_excel_row}:{col_name}{rate_last_excel_row})",
            formula_percent,
            value,
        )
    note_start = median_row + 3
    note_end = median_row + 5
    final_rate_label = "Leads → Vendas" if is_inside_sales else "Sessão → Purchase"
    data.merge_range(
        f"A{note_start}:{bench_last_col_name}{note_end}",
        f"Metodologia: para cada etapa, as taxas mensais são ordenadas e a mediana é calculada sobre todos os meses de LT. Taxas mensais acima de 100% são limitadas a 100% antes do cálculo. A conversão final {final_rate_label} é calculada diretamente por mês e não pela multiplicação das medianas das etapas.",
        note,
    )

    # Premissas
    prem = workbook.add_worksheet("Premissas")
    prem.set_tab_color(colors["yellow_dark"])
    prem.hide_gridlines(2)
    prem.freeze_panes(3, 0)
    prem.set_column("A:A", 34)
    prem.set_column("B:B", 20)
    prem.set_column("C:C", 54)
    prem.set_column(f"E:{prem_proj_last_name}", 15)
    prem.merge_range(
        f"A1:{prem_proj_last_name}1",
        f"Premissas — Breakeven {'Inside Sales' if is_inside_sales else 'E-commerce'} {client}",
        title,
    )
    prem.merge_range("A3:C3", "Cenário atual", section)
    if is_inside_sales:
        current_rows = [
            ("Cliente", client, "Editável"),
            ("Período atual", config_data["lt_period"], "Meses válidos"),
            ("Meses com fee", months_with_fee, "Calculado a partir dos dados fonte"),
            ("Fee acumulado", fee_total, "Linha 6"),
            ("Investimento acumulado", media_total, "Linha 9"),
            ("Custo acumulado", current_cost, "Fee + investimento"),
            ("Faturamento acumulado", revenue_total, "Linha 28"),
            ("Impressões acumuladas", sessions_total, "Meses com fee"),
            ("SQLs acumulados", orders_total, "Meses com fee"),
            ("Vendas acumuladas", sales_total, "Meses com fee"),
            ("Ticket médio", current_ticket, "Faturamento ÷ vendas"),
            ("Margem de contribuição", margin, "Premissa editável"),
            ("Resultado MC", current_mc, "Faturamento × margem"),
            ("Resultado líquido", current_result, "MC - custo"),
        ]
    else:
        current_rows = [
            ("Cliente", client, "Editável"),
            ("Período atual", config_data["lt_period"], "Meses válidos"),
            ("Meses com fee", months_with_fee, "Calculado a partir dos dados fonte"),
            ("Fee acumulado", fee_total, "Linha 6"),
            ("Investimento acumulado", media_total, "Linha 9"),
            ("Custo acumulado", current_cost, "Fee + investimento"),
            ("Faturamento acumulado", revenue_total, "Linha 28"),
            ("Sessões acumuladas", sessions_total, "Meses com fee"),
            ("Pedidos acumulados", orders_total, "Meses com fee"),
            ("Vendas acumuladas", sales_total, "Meses com fee"),
            ("Ticket médio", current_ticket, "Faturamento ÷ vendas"),
            ("Margem de contribuição", margin, "Premissa editável"),
            ("Resultado MC", current_mc, "Faturamento × margem"),
            ("Resultado líquido", current_result, "MC - custo"),
        ]
    for idx, (name, value, description) in enumerate(current_rows, 3):
        prem.write(idx, 0, name, label)
        if name in ("Cliente", "Período atual"):
            prem.write(idx, 1, value, input_text)
        elif name == "Margem de contribuição":
            prem.write_number(idx, 1, value, input_percent)
        elif "Meses" in name or "Impressões" in name or "SQLs" in name or "Sessões" in name or "Pedidos" in name or "Vendas" in name:
            if name == "Meses com fee":
                prem.write_formula(
                    idx,
                    1,
                    f"=COUNTA('Dados Fonte'!A{source_data_first_excel_row}:A{source_data_last_excel_row})",
                    formula_int,
                    value,
                )
            else:
                source_col = {
                    "Sessões acumuladas": "D",
                    "Impressões acumuladas": "D",
                    "Pedidos acumulados": "E",
                    "SQLs acumulados": "E",
                    "Vendas acumuladas": "F",
                }[name]
                prem.write_formula(
                    idx,
                    1,
                    f"='Dados Fonte'!{source_col}{source_total_excel_row}",
                    formula_int,
                    value,
                )
        elif name == "Fee acumulado":
            prem.write_formula(
                idx,
                1,
                f"='Dados Fonte'!B{source_total_excel_row}",
                formula_currency,
                value,
            )
        elif name == "Investimento acumulado":
            prem.write_formula(
                idx,
                1,
                f"='Dados Fonte'!C{source_total_excel_row}",
                formula_currency,
                value,
            )
        elif name == "Custo acumulado":
            prem.write_formula(idx, 1, "=B7+B8", formula_currency, value)
        elif name == "Faturamento acumulado":
            prem.write_formula(
                idx,
                1,
                f"='Dados Fonte'!G{source_total_excel_row}",
                formula_currency,
                value,
            )
        elif name == "Ticket médio":
            prem.write_formula(idx, 1, div_formula("B10/B13"), formula_currency, value)
        elif name == "Resultado MC":
            prem.write_formula(idx, 1, "=B10*B15", formula_currency, value)
        elif name == "Resultado líquido":
            prem.write_formula(idx, 1, "=B16-B9", formula_currency, value)
        else:
            prem.write_number(idx, 1, value, formula_currency)
        prem.write(idx, 2, description, normal)

    prem.merge_range(f"E3:{prem_proj_last_name}3", "Premissas futuras — células amarelas são editáveis", section)
    future_inputs = [
        ("Fee mensal", monthly_fee, input_currency),
        ("Mídia mensal", monthly_media, input_currency),
        ("Meses para recuperar", projection_months, input_int),
        ("Margem", margin, input_percent),
        ("Breakeven mensal", current_monthly_break_even, formula_currency),
        ("Custo futuro", future_cost, formula_currency),
        ("Receita futura necessária", future_revenue_required, formula_currency),
    ]
    for idx, (name, value, fmt) in enumerate(future_inputs, 3):
        prem.write(idx, 4, name, label)
        if idx <= 6:
            prem.write_number(idx, 5, value, fmt)
        elif name == "Breakeven mensal":
            prem.write_formula(idx, 5, "=(F4+F5)/F7", fmt, value)
        elif name == "Custo futuro":
            prem.write_formula(idx, 5, "=(F4+F5)*F6", fmt, value)
        else:
            prem.write_formula(idx, 5, "=(ABS(B17)+F9)/F7", fmt, value)
        prem.merge_range(idx, 6, idx, 10, "", normal)

    prem.merge_range(f"E12:{prem_proj_last_name}12", "Curva mensal editável", section)
    prem.write("E13", "Premissa", header)
    for idx in range(projection_months):
        prem.write(12, prem_proj_start_col + idx, month_headers[idx], header)
    prem.write("E14", "Faturamento alvo", label)
    use_unified_breakeven = (is_inside_sales and has_lead_quali) or (not is_inside_sales)
    if is_inside_sales and has_lead_quali:
        prem_rate_rows = [
            (14, "Impressões → Cliques"),
            (15, "Cliques → Leads"),
            (16, "Leads → Lead quali"),
            (17, "Lead quali → MQLs"),
            (18, "MQLs → SQLs"),
            (19, "SQLs → Vendas"),
        ]
        for row_idx, label_text in prem_rate_rows:
            prem.write(row_idx, 4, label_text, label)
        prem.write(20, 4, "Leads → Vendas", label)
    elif not is_inside_sales and use_unified_breakeven:
        prem_rate_rows = [
            (14, "Sessão → View item"),
            (15, "View item → Add cart"),
            (16, "Add cart → View cart"),
            (17, "View cart → Checkout"),
            (18, "Checkout → Pedido"),
            (19, "Pedido → Venda"),
        ]
        for row_idx, label_text in prem_rate_rows:
            prem.write(row_idx, 4, label_text, label)
        prem.write(20, 4, "Sessão → Venda", label)
    elif is_inside_sales:
        prem.write("E15", "Impressões → Cliques", label)
        prem.write("E16", "Cliques → Leads", label)
        prem.write("E17", "Leads → Vendas", label)
        prem.write("E18", "Aprovação pedido → venda", label)
    else:
        prem.write("E15", "View item / sessão", label)
        prem.write("E16", "Add to cart / view item", label)
        prem.write("E17", "Purchase / add to cart", label)
        prem.write("E18", "Aprovação pedido → venda", label)
    for idx in range(projection_months):
        col = prem_proj_start_col + idx
        prem_col = xlsxwriter.utility.xl_col_to_name(col)
        revenue = projected_revenue[idx]
        prem.write_number(13, col, revenue, input_currency)
        prem.write_number(14, col, view_rates[idx], input_percent)
        prem.write_number(15, col, cart_rates[idx], input_percent)
        if is_inside_sales and has_lead_quali:
            prem.write_number(16, col, lead_lead_quali_rates[idx], input_percent)
            prem.write_number(17, col, lead_quali_mql_rates[idx], input_percent)
            prem.write_number(18, col, mql_sql_rates[idx], input_percent)
            prem.write_number(19, col, sql_sale_rates[idx], input_percent)
            prem.write_formula(
                20,
                col,
                f"={prem_col}17*{prem_col}18*{prem_col}19*{prem_col}20",
                formula_percent,
                lead_to_sale_rates[idx],
            )
        elif not is_inside_sales and use_unified_breakeven:
            checkout_to_order = (
                realista["checkout_shipping"][idx]
                * realista["shipping_payment"][idx]
                * realista["payment_order"][idx]
            )
            prem.write_number(16, col, realista["add_view_cart"][idx], input_percent)
            prem.write_number(17, col, realista["viewcart_checkout"][idx], input_percent)
            prem.write_number(18, col, checkout_to_order, input_percent)
            prem.write_number(19, col, approval_rates[idx], input_percent)
            session_to_sale = (
                view_rates[idx]
                * cart_rates[idx]
                * realista["add_view_cart"][idx]
                * realista["viewcart_checkout"][idx]
                * checkout_to_order
                * approval_rates[idx]
            )
            prem.write_formula(
                20,
                col,
                f"={prem_col}15*{prem_col}16*{prem_col}17*{prem_col}18*{prem_col}19*{prem_col}20",
                formula_percent,
                session_to_sale,
            )
        elif is_inside_sales:
            prem.write_number(16, col, lead_to_sale_rates[idx], input_percent)
            prem.write_number(17, col, approval_rates[idx], input_percent)
        else:
            prem.write_number(16, col, cart_to_purchase, input_percent)
            prem.write_number(17, col, approval_rates[idx], input_percent)
    prem.data_validation("F4:F7", {"validate": "decimal", "criteria": ">", "value": 0})
    prem.data_validation(f"F14:{prem_proj_last_name}14", {"validate": "decimal", "criteria": ">", "value": 0})
    if is_inside_sales and has_lead_quali:
        prem.data_validation(
            f"F15:{prem_proj_last_name}20",
            {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": max_conversion_rate},
        )
    elif not is_inside_sales and use_unified_breakeven:
        prem.data_validation(
            f"F15:{prem_proj_last_name}20",
            {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": max_conversion_rate},
        )
    else:
        prem.data_validation(f"F15:{prem_proj_last_name}18", {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 1})
    prem_note_row = 23 if use_unified_breakeven else 20
    prem.merge_range(
        f"A{prem_note_row}:{prem_proj_last_name}{prem_note_row + 2}",
        (
            f"Como usar: altere somente as células amarelas. A projeção roda por {projection_months} meses "
            f"até o breakeven ({minimum_breakeven_label}) ou até o limite de {MAX_PROJECTION_MONTHS} meses. "
            + (
                "Leads → Vendas (linha 21) é calculada automaticamente a partir das taxas operacionais. "
                if is_inside_sales and has_lead_quali
                else (
                    "Sessão → Venda (linha 21) é calculada automaticamente a partir das taxas operacionais. "
                    if not is_inside_sales and use_unified_breakeven
                    else ""
                )
            )
            + "Os volumes do funil e indicadores são recalculados automaticamente."
        ),
        note,
    )

    # Breakeven
    minimum_cached = build_minimum_funnel_cache(
        projections,
        minimum_full_rates,
        has_lead_quali,
        is_inside_sales,
    )

    if use_unified_breakeven:
        from breakeven_unified_sheet import BEU, write_unified_breakeven_worksheet

        final_conversion_expr = (
            lambda prem_col, _has_lead_quali=True: ecommerce_session_to_sale_expr(prem_col)
            if not is_inside_sales
            else inside_sales_lead_to_sale_expr(prem_col, has_lead_quali)
        )

        be = write_unified_breakeven_worksheet(
            workbook=workbook,
            client=client,
            projection_months=projection_months,
            month_headers=month_headers,
            be_proj_last_name=be_proj_last_name,
            title=title,
            header=header,
            label=label,
            note=note,
            status_ok=status_ok,
            status_bad=status_bad,
            formula_currency=formula_currency,
            formula_percent=formula_percent,
            formula_int=formula_int,
            formula_number=formula_number,
            input_percent=input_percent,
            div_formula=div_formula,
            inside_sales_lead_to_sale_expr=final_conversion_expr,
            funnel_mode="ecommerce" if not is_inside_sales else "inside_sales",
            colors=colors,
            current_cost=current_cost,
            fee_total=fee_total,
            media_total=media_total,
            sessions_total=sessions_total,
            sales_total=sales_total,
            revenue_total=revenue_total,
            current_ticket=current_ticket,
            margin=margin,
            current_mc=current_mc,
            current_result=current_result,
            current_lead_to_sale=current_lead_to_sale,
            current_view_item=current_view_item,
            current_add_cart=current_add_cart,
            current_view_cart=current_view_cart,
            current_checkout=current_checkout,
            current_shipping=current_shipping,
            current_orders=current_orders,
            monthly_fee=monthly_fee,
            monthly_media=monthly_media,
            future_revenue_required=future_revenue_required,
            minimum_breakeven_label=minimum_breakeven_label,
            projections=projections,
            minimum_cached=minimum_cached,
        )
    if not use_unified_breakeven:
        be = workbook.add_worksheet("Breakeven 7M")
        be.set_tab_color(colors["teal"])
        be.hide_gridlines(2)
        be.freeze_panes(2, 4)
        be.set_column("A:A", 36)
        be.set_column("B:C", 19)
        be.set_column("D:D", 3)
        be.set_column(f"E:{be_proj_last_name}", 15)
        be.merge_range(f"A1:{be_proj_last_name}1", f"Projeção Breakeven — {client}", title)
        headers = ["", "Feito até o momento", f"Cenário mínimo {projection_months}M", "", *month_headers]
        for col, text in enumerate(headers):
            be.write(1, col, text, header if col != 3 else normal)
        row_labels = breakeven_financial_row_labels(is_inside_sales, funnel_conversion_label)
        for row_num, text in row_labels.items():
            be.write(row_num, 0, text, label)
    
        current_values = {
            2: current_cost,
            3: fee_total,
            4: media_total,
            5: sessions_total,
            6: media_total / sessions_total,
            7: orders_total / sessions_total,
            8: orders_total,
            9: media_total / orders_total,
            10: sales_total / orders_total,
            11: sales_total,
            12: media_total / sales_total,
            13: sales_total / leads_total if is_inside_sales and leads_total else sales_total / sessions_total,
            15: current_ticket,
            16: margin,
            18: revenue_total,
            19: revenue_total,
            20: revenue_total / media_total,
            21: current_mc,
            22: current_mc,
            24: current_cost,
            25: current_cost,
            27: current_result,
            28: current_result,
            29: current_mc / current_cost,
            30: current_mc / current_cost,
            32: future_revenue_required,
        }
        current_formulas = {
            2: "='Premissas'!B9",
            3: "='Premissas'!B7",
            4: "='Premissas'!B8",
            5: "='Premissas'!B11",
            6: div_formula("B4/B5"),
            7: div_formula("B8/B5"),
            8: "='Premissas'!B12",
            9: div_formula("B4/B8"),
            10: div_formula("B11/B8"),
            11: "='Premissas'!B13",
            12: div_formula("B4/B11"),
            13: div_formula("B11/B41") if is_inside_sales else div_formula("B11/B5"),
            15: "='Premissas'!B14",
            16: "='Premissas'!B15",
            18: "='Premissas'!B10",
            19: "=B18",
            20: "=B18/B4",
            21: "=B18*B16",
            22: "=B21",
            24: "=B2",
            25: "=B24",
            27: "=B21-B24",
            28: "=B27",
            29: "=B21/B24",
            30: "=B22/B25",
            32: "='Premissas'!F10",
        }
        for row_num, value in current_values.items():
            fmt = formula_percent if row_num in (7, 10, 13, 16) else formula_int if row_num in (5, 8, 11) else formula_number if row_num in (20, 29, 30) else formula_currency
            if row_num == 13 and is_inside_sales:
                be.write_number(row_num - 1, 1, value, fmt)
                continue
            be.write_formula(row_num - 1, 1, current_formulas[row_num], fmt, value)
        be.write_formula(32, 1, '=IF(B28>=0,"Já breakevado","Déficit a recuperar")', status_bad, "Déficit a recuperar")
    
        for idx, proj in enumerate(projections):
            col = 4 + idx
            month_col = xlsxwriter.utility.xl_col_to_name(col)
            prem_col = xlsxwriter.utility.xl_col_to_name(5 + idx)
            previous_col = xlsxwriter.utility.xl_col_to_name(col - 1)
            monthly_values = {
                2: proj["monthly_cost"],
                3: monthly_fee,
                4: monthly_media,
                5: proj["sessions"],
                6: proj["cps"],
                7: proj["orders"] / proj["sessions"],
                8: proj["orders"],
                9: proj["cpp"],
                10: proj["approval"],
                11: proj["sales"],
                12: proj["cpv"],
                13: lead_to_sale_rates[idx] if is_inside_sales else proj["final_conversion"],
                15: proj["ticket"],
                16: margin,
                18: proj["revenue"],
                19: sum(p["revenue"] for p in projections[: idx + 1]),
                20: proj["roas"],
                21: proj["monthly_mc"],
                22: sum(p["monthly_mc"] for p in projections[: idx + 1]),
                24: proj["monthly_cost"],
                25: (idx + 1) * proj["monthly_cost"],
                27: proj["monthly_result"],
                28: proj["cumulative_result"],
                29: proj["monthly_mc"] / proj["monthly_cost"],
                30: (current_mc + sum(p["monthly_mc"] for p in projections[: idx + 1]))
                / (current_cost + (idx + 1) * proj["monthly_cost"]),
            }
            formulas = {
                2: f"={month_col}3+{month_col}4",
                3: "='Premissas'!F4",
                4: "='Premissas'!F5",
                5: div_formula(
                    f"{month_col}11/({inside_sales_full_funnel_rate_expr(prem_col, has_lead_quali)})"
                    if is_inside_sales
                    else f"{month_col}11/{month_col}13"
                ),
                6: div_formula(f"{month_col}4/{month_col}5"),
                7: div_formula(f"{month_col}8/{month_col}5"),
                8: div_formula(f"{month_col}11/{month_col}10"),
                9: div_formula(f"{month_col}4/{month_col}8"),
                10: "=1" if is_inside_sales and has_lead_quali else f"='Premissas'!{prem_col}18",
                11: div_formula(f"{month_col}18/{month_col}15"),
                12: div_formula(f"{month_col}4/{month_col}11"),
                13: (
                    f"={inside_sales_lead_to_sale_expr(prem_col, has_lead_quali)}"
                    if is_inside_sales
                    else f"='Premissas'!{prem_col}15*'Premissas'!{prem_col}16*'Premissas'!{prem_col}17"
                ),
                15: "=B15" if idx == 0 else f"={previous_col}15*1.01",
                16: "='Premissas'!F7",
                18: f"='Premissas'!{prem_col}14",
                19: f"=SUM($E18:{month_col}18)",
                20: f"={month_col}18/{month_col}4",
                21: f"={month_col}18*{month_col}16",
                22: f"=SUM($E21:{month_col}21)",
                24: f"={month_col}2",
                25: f"=SUM($E24:{month_col}24)",
                27: f"={month_col}21-{month_col}24",
                28: f"=ROUND($B28+SUM($E27:{month_col}27),2)",
                29: f"={month_col}21/{month_col}24",
                30: f"=($B22+{month_col}22)/($B25+{month_col}25)",
            }
            for row_num, value in monthly_values.items():
                fmt = formula_percent if row_num in (7, 10, 13, 16) else formula_int if row_num in (5, 8, 11) else formula_number if row_num in (20, 29, 30) else formula_currency
                be.write_formula(row_num - 1, col, formulas[row_num], fmt, value)
    
        aggregate_values = {
            2: future_cost,
            3: projection_months * monthly_fee,
            4: projection_months * monthly_media,
            5: sum(p["sessions"] for p in projections),
            6: projection_months * monthly_media / sum(p["sessions"] for p in projections),
            7: sum(p["orders"] for p in projections) / sum(p["sessions"] for p in projections),
            8: sum(p["orders"] for p in projections),
            9: projection_months * monthly_media / sum(p["orders"] for p in projections),
            10: sum(p["sales"] for p in projections) / sum(p["orders"] for p in projections),
            11: sum(p["sales"] for p in projections),
            12: projection_months * monthly_media / sum(p["sales"] for p in projections),
            13: (
                sum(p["sales"] for p in projections)
                / sum(
                    p["sales"] / lead_to_sale_rates[i]
                    for i, p in enumerate(projections)
                    if lead_to_sale_rates[i]
                )
                if is_inside_sales
                else sum(p["sales"] for p in projections) / sum(p["sessions"] for p in projections)
            ),
            15: future_revenue_required / sum(p["sales"] for p in projections),
            16: margin,
            18: future_revenue_required,
            19: future_revenue_required,
            20: future_revenue_required / (projection_months * monthly_media),
            21: future_revenue_required * margin,
            22: future_revenue_required * margin,
            24: future_cost,
            25: future_cost,
            27: future_revenue_required * margin - future_cost,
            28: 0,
            29: (future_revenue_required * margin) / future_cost,
            30: (current_mc + future_revenue_required * margin) / (current_cost + future_cost),
            32: future_revenue_required,
        }
        aggregate_formulas = {
            2: f"=SUM(E2:{be_proj_last_name}2)",
            3: f"=SUM(E3:{be_proj_last_name}3)",
            4: f"=SUM(E4:{be_proj_last_name}4)",
            5: f"=SUM(E5:{be_proj_last_name}5)",
            6: div_formula("C4/C5"),
            7: div_formula("C8/C5"),
            8: f"=SUM(E8:{be_proj_last_name}8)",
            9: div_formula("C4/C8"),
            10: div_formula("C11/C8"),
            11: f"=SUM(E11:{be_proj_last_name}11)",
            12: div_formula("C4/C11"),
            13: (
                div_formula(f"C11/SUM(E41:{be_proj_last_name}41)")
                if is_inside_sales
                else div_formula("C11/C5")
            ),
            15: div_formula("C18/C11"),
            16: "='Premissas'!F7",
            18: f"=SUM(E18:{be_proj_last_name}18)",
            19: "=C18",
            20: "=C18/C4",
            21: "=C18*C16",
            22: "=C21",
            24: "=C2",
            25: "=C24",
            27: "=C21-C24",
            28: "=ROUND(B28+C27,2)",
            29: "=C21/C24",
            30: "=(B22+C22)/(B25+C25)",
            32: "='Premissas'!F10",
        }
        for row_num, value in aggregate_values.items():
            fmt = formula_percent if row_num in (7, 10, 13, 16) else formula_int if row_num in (5, 8, 11) else formula_number if row_num in (20, 29, 30) else formula_currency
            be.write_formula(row_num - 1, 2, aggregate_formulas[row_num], fmt, value)
        be.write_formula(32, 2, '=IF(C28>=-0.01,"Breakeven atingido","Revisar premissas")', status_ok, "Breakeven atingido")
    
        be.conditional_format(f"B27:{be_proj_last_name}28", {"type": "cell", "criteria": "<", "value": 0, "format": status_bad})
        be.conditional_format(f"B27:{be_proj_last_name}28", {"type": "cell", "criteria": ">=", "value": 0, "format": status_ok})
        be.conditional_format(f"E6:{be_proj_last_name}6", {"type": "3_color_scale", "min_color": "#63BE7B", "mid_color": "#FFEB84", "max_color": "#F8696B"})
    
        # Funil completo integrado na mesma aba de breakeven.
        be.merge_range(f"A36:{be_proj_last_name}36", "Funil completo do cenário mínimo", section)
        integrated_rows = integrated_funnel_row_labels(is_inside_sales, final_funnel_rate_label, has_lead_quali)
        for row_num, text in integrated_rows.items():
            be.write(row_num - 1, 0, text, label)
    
        if is_inside_sales:
            if has_lead_quali:
                current_integrated = {
                    37: current_sessions,
                    38: current_view_item / current_sessions,
                    39: current_view_item,
                    40: current_add_cart / current_view_item,
                    41: current_add_cart,
                    42: min(max_conversion_rate, current_view_cart / current_add_cart),
                    43: current_view_cart,
                    44: current_checkout / current_view_cart if current_view_cart else 0,
                    45: current_checkout,
                    46: current_shipping / current_checkout if current_checkout else 0,
                    47: current_shipping,
                    48: current_sales / current_shipping if current_shipping else 0,
                    53: current_sales,
                    54: current_lead_to_sale,
                    55: current_month_media / current_sessions if current_sessions else 0,
                    56: current_month_media / current_shipping if current_shipping else 0,
                    57: current_month_media / current_sales if current_sales else 0,
                }
                integrated_percent_rows = {38, 40, 42, 44, 46, 48, 54}
            else:
                current_integrated = {
                    37: current_sessions,
                    38: current_view_item / current_sessions,
                    39: current_view_item,
                    40: current_add_cart / current_view_item,
                    41: current_add_cart,
                    42: min(max_conversion_rate, current_view_cart / current_add_cart),
                    43: current_view_cart,
                    44: current_checkout / current_view_cart,
                    45: current_checkout,
                    48: current_sales / current_checkout if current_checkout else 0,
                    53: current_sales,
                    54: current_lead_to_sale,
                    55: current_month_media / current_sessions,
                    56: current_month_media / current_checkout if current_checkout else 0,
                    57: current_month_media / current_sales,
                }
                integrated_percent_rows = {38, 40, 42, 44, 48, 54}
        else:
            current_integrated = {
                37: current_sessions,
                38: current_view_item / current_sessions,
                39: current_view_item,
                40: current_add_cart / current_view_item,
                41: current_add_cart,
                42: min(1, current_view_cart / current_add_cart),
                43: current_view_cart,
                44: current_checkout / current_view_cart,
                45: current_checkout,
                46: min(1, current_shipping / current_checkout),
                47: current_shipping,
                48: current_payment / current_shipping,
                49: current_payment,
                50: current_orders / current_payment,
                51: current_orders,
                52: current_sales / current_orders,
                53: current_sales,
                54: current_sales / current_sessions,
                55: current_month_media / current_sessions,
                56: current_month_media / current_orders,
                57: current_month_media / current_sales,
            }
            integrated_percent_rows = {38, 40, 42, 44, 46, 48, 50, 52, 54}
        for row_num, value in current_integrated.items():
            fmt = formula_percent if row_num in integrated_percent_rows else formula_currency if row_num in (55, 56, 57) else formula_int
            be.write_number(row_num - 1, 1, value, fmt)
    
        minimum_cached = []
        for idx, proj in enumerate(projections):
            sales = proj["sales"]
            if is_inside_sales:
                funnel_volumes = build_inside_sales_funnel_volumes(
                    sales,
                    {
                        "shipping_payment": minimum_full_rates["shipping_payment"][idx],
                        "checkout_shipping": minimum_full_rates["checkout_shipping"][idx],
                        "viewcart_checkout": minimum_full_rates["viewcart_checkout"][idx],
                        "add_view_cart": minimum_full_rates["add_view_cart"][idx],
                        "view_add": minimum_full_rates["view_add"][idx],
                        "session_view": minimum_full_rates["session_view"][idx],
                    },
                    has_lead_quali=has_lead_quali,
                )
                sessions = funnel_volumes["sessions"]
                view_item = funnel_volumes["view_item"]
                add_cart = funnel_volumes["add_cart"]
                view_cart = funnel_volumes["view_cart"]
                checkout = funnel_volumes["begin_checkout"] if has_lead_quali else funnel_volumes["checkout"]
                shipping = funnel_volumes["checkout"]
                payment = funnel_volumes["payment"]
                orders = funnel_volumes["orders"]
            else:
                orders = sales / minimum_full_rates["order_sale"][idx]
                payment = orders / minimum_full_rates["payment_order"][idx]
                shipping = payment / minimum_full_rates["shipping_payment"][idx]
                checkout = shipping / minimum_full_rates["checkout_shipping"][idx]
                view_cart = checkout / minimum_full_rates["viewcart_checkout"][idx]
                add_cart = view_cart / minimum_full_rates["add_view_cart"][idx]
                view_item = add_cart / minimum_full_rates["view_add"][idx]
                sessions = view_item / minimum_full_rates["session_view"][idx]
            minimum_cached.append(
                {
                    "sessions": sessions,
                    "view_item": view_item,
                    "add_cart": add_cart,
                    "view_cart": view_cart,
                    "checkout": checkout,
                    "shipping": shipping,
                    "payment": payment,
                    "orders": orders,
                    "sales": sales,
                }
            )
            col = 4 + idx
            col_name = xlsxwriter.utility.xl_col_to_name(col)
            prem_col = xlsxwriter.utility.xl_col_to_name(5 + idx)
            if is_inside_sales:
                if has_lead_quali:
                    rate_map = {
                        38: (f"='Premissas'!{prem_col}15", minimum_full_rates["session_view"][idx]),
                        40: (f"='Premissas'!{prem_col}16", minimum_full_rates["view_add"][idx]),
                        42: (f"='Premissas'!{prem_col}17", minimum_full_rates["add_view_cart"][idx]),
                        44: (f"='Premissas'!{prem_col}18", minimum_full_rates["viewcart_checkout"][idx]),
                        46: (f"='Premissas'!{prem_col}19", minimum_full_rates["checkout_shipping"][idx]),
                        48: (f"='Premissas'!{prem_col}20", minimum_full_rates["shipping_payment"][idx]),
                    }
                    volume_map = {
                        53: (f"={col_name}11", sales),
                        47: (div_formula(f"{col_name}53/{col_name}48"), shipping),
                        45: (div_formula(f"{col_name}47/{col_name}46"), checkout),
                        43: (div_formula(f"{col_name}45/{col_name}44"), view_cart),
                        41: (div_formula(f"{col_name}43/{col_name}42"), add_cart),
                        39: (div_formula(f"{col_name}41/{col_name}40"), view_item),
                        37: (div_formula(f"{col_name}39/{col_name}38"), sessions),
                        54: (
                            f"={inside_sales_lead_to_sale_expr(prem_col, True)}",
                            sales / add_cart if add_cart else 0,
                        ),
                        55: (div_formula(f"{col_name}4/{col_name}37"), monthly_media / sessions if sessions else 0),
                        56: (div_formula(f"{col_name}4/{col_name}47"), monthly_media / shipping if shipping else 0),
                        57: (div_formula(f"{col_name}4/{col_name}53"), monthly_media / sales if sales else 0),
                    }
                else:
                    rate_map = {
                        38: minimum_full_rates["session_view"][idx],
                        40: minimum_full_rates["view_add"][idx],
                        42: minimum_full_rates["add_view_cart"][idx],
                        44: minimum_full_rates["viewcart_checkout"][idx],
                        48: minimum_full_rates["shipping_payment"][idx],
                    }
                    volume_map = {
                        53: (f"={col_name}11", sales),
                        45: (div_formula(f"{col_name}53/{col_name}48"), checkout),
                        43: (div_formula(f"{col_name}45/{col_name}44"), view_cart),
                        41: (div_formula(f"{col_name}43/{col_name}42"), add_cart),
                        39: (div_formula(f"{col_name}41/{col_name}40"), view_item),
                        37: (div_formula(f"{col_name}39/{col_name}38"), sessions),
                        54: (
                            div_formula(f"{col_name}53/{col_name}{final_rate_integrated_row}"),
                            sales / add_cart if add_cart else 0,
                        ),
                        55: (div_formula(f"{col_name}4/{col_name}37"), monthly_media / sessions),
                        56: (div_formula(f"{col_name}4/{col_name}45"), monthly_media / checkout if checkout else 0),
                        57: (div_formula(f"{col_name}4/{col_name}53"), monthly_media / sales),
                    }
            else:
                rate_map = {
                    38: minimum_full_rates["session_view"][idx],
                    40: minimum_full_rates["view_add"][idx],
                    42: minimum_full_rates["add_view_cart"][idx],
                    44: minimum_full_rates["viewcart_checkout"][idx],
                    46: minimum_full_rates["checkout_shipping"][idx],
                    48: minimum_full_rates["shipping_payment"][idx],
                    50: minimum_full_rates["payment_order"][idx],
                    52: minimum_full_rates["order_sale"][idx],
                }
                volume_map = {
                    53: (f"={col_name}11", sales),
                    51: (div_formula(f"{col_name}53/{col_name}52"), orders),
                    49: (div_formula(f"{col_name}51/{col_name}50"), payment),
                    47: (div_formula(f"{col_name}49/{col_name}48"), shipping),
                    45: (div_formula(f"{col_name}47/{col_name}46"), checkout),
                    43: (div_formula(f"{col_name}45/{col_name}44"), view_cart),
                    41: (div_formula(f"{col_name}43/{col_name}42"), add_cart),
                    39: (div_formula(f"{col_name}41/{col_name}40"), view_item),
                    37: (div_formula(f"{col_name}39/{col_name}38"), sessions),
                    54: (
                        div_formula(f"{col_name}53/{col_name}{final_rate_integrated_row}"),
                        sales / sessions,
                    ),
                    55: (div_formula(f"{col_name}4/{col_name}37"), monthly_media / sessions),
                    56: (div_formula(f"{col_name}4/{col_name}51"), monthly_media / orders),
                    57: (div_formula(f"{col_name}4/{col_name}53"), monthly_media / sales),
                }
            for row_num, value in rate_map.items():
                if has_lead_quali and is_inside_sales:
                    formula, cached = value
                    be.write_formula(row_num - 1, col, formula, input_percent, cached)
                else:
                    be.write_number(row_num - 1, col, value, input_percent)
            for row_num, (formula, value) in volume_map.items():
                fmt = formula_percent if row_num == 54 else formula_currency if row_num in (55, 56, 57) else formula_int
                be.write_formula(row_num - 1, col, formula, fmt, value)
    
        if is_inside_sales:
            if has_lead_quali:
                integrated_aggregate = {
                    37: sum(x["sessions"] for x in minimum_cached),
                    39: sum(x["view_item"] for x in minimum_cached),
                    41: sum(x["add_cart"] for x in minimum_cached),
                    43: sum(x["view_cart"] for x in minimum_cached),
                    45: sum(x["checkout"] for x in minimum_cached),
                    47: sum(x["shipping"] for x in minimum_cached),
                    53: sum(x["sales"] for x in minimum_cached),
                }
                integrated_rates = {
                    38: (39, 37),
                    40: (41, 39),
                    42: (43, 41),
                    44: (45, 43),
                    46: (47, 45),
                    48: (53, 47),
                    54: (53, final_rate_integrated_row),
                }
            else:
                integrated_aggregate = {
                    37: sum(x["sessions"] for x in minimum_cached),
                    39: sum(x["view_item"] for x in minimum_cached),
                    41: sum(x["add_cart"] for x in minimum_cached),
                    43: sum(x["view_cart"] for x in minimum_cached),
                    45: sum(x["checkout"] for x in minimum_cached),
                    53: sum(x["sales"] for x in minimum_cached),
                }
                integrated_rates = {
                    38: (39, 37),
                    40: (41, 39),
                    42: (43, 41),
                    44: (45, 43),
                    48: (53, 45),
                    54: (53, final_rate_integrated_row),
                }
        else:
            integrated_aggregate = {
                37: sum(x["sessions"] for x in minimum_cached),
                39: sum(x["view_item"] for x in minimum_cached),
                41: sum(x["add_cart"] for x in minimum_cached),
                43: sum(x["view_cart"] for x in minimum_cached),
                45: sum(x["checkout"] for x in minimum_cached),
                47: sum(x["shipping"] for x in minimum_cached),
                49: sum(x["payment"] for x in minimum_cached),
                51: sum(x["orders"] for x in minimum_cached),
                53: sum(x["sales"] for x in minimum_cached),
            }
            integrated_rates = {
                38: (39, 37),
                40: (41, 39),
                42: (43, 41),
                44: (45, 43),
                46: (47, 45),
                48: (49, 47),
                50: (51, 49),
                52: (53, 51),
                54: (53, final_rate_integrated_row),
            }
        for row_num, value in integrated_aggregate.items():
            be.write_formula(row_num - 1, 2, f"=SUM(E{row_num}:{be_proj_last_name}{row_num})", formula_int, value)
        for row_num, (numerator, denominator) in integrated_rates.items():
            value = integrated_aggregate[numerator] / integrated_aggregate[denominator]
            be.write_formula(row_num - 1, 2, div_formula(f"C{numerator}/C{denominator}"), formula_percent, value)
        be.write_formula(54, 2, div_formula("C4/C37"), formula_currency, projection_months * monthly_media / integrated_aggregate[37])
        if is_inside_sales:
            sql_cost_row = 47 if has_lead_quali else 45
            be.write_formula(55, 2, div_formula(f"C4/C{sql_cost_row}"), formula_currency, projection_months * monthly_media / integrated_aggregate[sql_cost_row])
        else:
            be.write_formula(55, 2, div_formula("C4/C51"), formula_currency, projection_months * monthly_media / integrated_aggregate[51])
        be.write_formula(56, 2, div_formula("C4/C53"), formula_currency, projection_months * monthly_media / integrated_aggregate[53])
        be.merge_range(
            f"A60:{be_proj_last_name}62",
            "As taxas amarelas são premissas editáveis. Os volumes são calculados de trás para frente e alimentam diretamente a leitura financeira do breakeven.",
            note,
        )
    
    pessimista = write_scenario_sheet("Pessimista", scenario_configs["Pessimista"])
    realista = write_scenario_sheet("Realista", scenario_configs["Realista"])
    otimista = write_scenario_sheet("Otimista", scenario_configs["Otimista"])

    # Funil Completo
    funnel = workbook.add_worksheet("Funil Completo")
    funnel.set_tab_color("#5B9BD5")
    funnel.hide_gridlines(2)
    funnel.freeze_panes(4, 0)
    funnel.set_column("A:A", 28)
    funnel.set_column("B:D", 17)
    funnel.set_column("E:E", 31)
    funnel.set_column(f"G:{funnel_proj_last_name}", 15)
    funnel.merge_range(
        f"A1:{funnel_proj_last_name}1",
        f"Funil Completo — Atual, Bench Mediana {len(benchmark_months)}M e Projeção Gerencial",
        title,
    )
    funnel.merge_range("A3:E3", f"Funil atual — {current_period}", section)
    for col, text in enumerate(["Etapa", "Volume atual", "Taxa atual", "Bench interno", "Validação"]):
        funnel.write(3, col, text, header)
    funnel_first_row_fc = 4
    funnel_summary_row_fc = funnel_first_row_fc + len(current_funnel)
    funnel_leads_row_fc = funnel_first_row_fc + 2
    funnel_last_row_fc = funnel_first_row_fc + len(current_funnel) - 1
    for idx, row in enumerate(current_funnel, funnel_first_row_fc):
        stage, volume, rate, bench, status = row
        funnel.write(idx, 0, stage, normal)
        funnel.write_number(idx, 1, volume, normal_int)
        if rate is None:
            funnel.write(idx, 2, "-", normal)
        else:
            funnel.write_number(idx, 2, rate, normal_percent)
        if bench is None:
            funnel.write(idx, 3, "-", normal)
        else:
            funnel.write_number(idx, 3, bench, normal_percent)
        funnel.write(idx, 4, status, status_bad if "sequencial" in status or "duplicidade" in status else normal)
    summary_label_fc = "Leads → Vendas" if is_inside_sales else "Sessão → Purchase"
    if is_inside_sales:
        summary_rate_fc = current_sales / current_add_cart if current_add_cart else 0
        summary_formula_fc = f"=B{funnel_last_row_fc + 1}/B{funnel_leads_row_fc + 1}"
    else:
        summary_rate_fc = current_purchase / current_sessions
        summary_formula_fc = f"=B{funnel_last_row_fc + 1}/B{funnel_first_row_fc + 1}"
    funnel.write(funnel_summary_row_fc, 0, summary_label_fc, label)
    funnel.write_formula(
        funnel_summary_row_fc, 1, summary_formula_fc, formula_percent, summary_rate_fc
    )
    funnel.write_number(
        funnel_summary_row_fc, 2, summary_rate_fc, normal_percent
    )
    funnel.write_number(
        funnel_summary_row_fc, 3, final_conversion_bench, normal_percent
    )
    funnel.write(
        funnel_summary_row_fc, 4, f"Bench: mediana dos {len(benchmark_months)} meses de LT", normal
    )
    note_row_fc = funnel_summary_row_fc + 3
    funnel.merge_range(
        f"A{note_row_fc}:E{note_row_fc + 2}",
        "Atenção: valide a sequência dos eventos no GA4 antes de interpretar taxas intermediárias. O bench usa a mediana mensal de todos os meses de LT, com taxas acima de 100% limitadas a 100%. A conversão final é calculada diretamente por mês e não pela multiplicação das medianas das etapas.",
        note,
    )

    funnel.merge_range(f"G3:{funnel_proj_last_name}3", "Funil gerencial projetado — volumes necessários", section)
    funnel.write("G4", "Etapa", header)
    for idx in range(projection_months):
        funnel.write(3, funnel_proj_start_col + idx, month_headers[idx], header)
    if is_inside_sales:
        projected_stages = [
            "Faturamento",
            "Ticket médio",
            "Vendas",
            "Leads",
            "Cliques",
            "Impressões",
            "Conversão final",
            "CPM",
            "Custo por impressão",
            "Custo por venda",
        ]
    else:
        projected_stages = [
            "Faturamento",
            "Ticket médio",
            "Purchase",
            "Add to cart",
            "View item",
            "Sessões",
            "Page views",
            "Conversão final",
            "CPS necessário",
            "Custo por compra",
        ]
    for idx, stage in enumerate(projected_stages, 4):
        funnel.write(idx, 6, stage, label)
    pageviews_per_session = current_pageviews / current_sessions if current_sessions else 1
    for idx, proj in enumerate(projections):
        col = 7 + idx
        col_name = xlsxwriter.utility.xl_col_to_name(col)
        be_col = xlsxwriter.utility.xl_col_to_name(4 + idx)
        prem_col = xlsxwriter.utility.xl_col_to_name(5 + idx)
        purchase = proj["sales"]
        if use_unified_breakeven:
            be_revenue_row, be_ticket_row, be_sales_row, be_media_row, be_cps_row, be_cpv_row = 25, 23, 18, 5, 20, 22
        else:
            be_revenue_row, be_ticket_row, be_sales_row, be_media_row, be_cps_row, be_cpv_row = 18, 15, 11, 4, 6, 12
        if is_inside_sales and has_lead_quali:
            lead_to_sale_formula = inside_sales_lead_to_sale_expr(prem_col, True)
            add_cart = purchase / lead_to_sale_rates[idx] if lead_to_sale_rates[idx] else 0
            view_item = add_cart / cart_rates[idx] if cart_rates[idx] else 0
            sessions = view_item / view_rates[idx] if view_rates[idx] else 0
            values = [
                proj["revenue"],
                proj["ticket"],
                purchase,
                add_cart,
                view_item,
                sessions,
                lead_to_sale_rates[idx],
                proj["cpm"],
                proj["cps"],
                proj["cpv"],
            ]
            formulas = [
                f"='Breakeven 7M'!{be_col}{be_revenue_row}",
                f"='Breakeven 7M'!{be_col}{be_ticket_row}",
                f"='Breakeven 7M'!{be_col}{be_sales_row}",
                div_formula(f"{col_name}6/({lead_to_sale_formula})"),
                div_formula(f"{col_name}7/'Premissas'!{prem_col}16"),
                div_formula(f"{col_name}8/'Premissas'!{prem_col}15"),
                f"={lead_to_sale_formula}",
                div_formula(f"'Breakeven 7M'!{be_col}{be_media_row}/{col_name}9*1000"),
                f"='Breakeven 7M'!{be_col}{be_cps_row}",
                f"='Breakeven 7M'!{be_col}{be_cpv_row}",
            ]
            percent_rows = {10}
            currency_rows = {4, 5, 11, 12, 13, 14}
        elif is_inside_sales:
            add_cart = purchase / lead_to_sale_rates[idx] if lead_to_sale_rates[idx] else 0
            view_item = add_cart / cart_rates[idx] if cart_rates[idx] else 0
            sessions = view_item / view_rates[idx] if view_rates[idx] else 0
            values = [
                proj["revenue"],
                proj["ticket"],
                purchase,
                add_cart,
                view_item,
                sessions,
                lead_to_sale_rates[idx],
                proj["cpm"],
                proj["cps"],
                proj["cpv"],
            ]
            formulas = [
                f"='Breakeven 7M'!{be_col}{be_revenue_row}",
                f"='Breakeven 7M'!{be_col}{be_ticket_row}",
                f"='Breakeven 7M'!{be_col}{be_sales_row}",
                f"={col_name}6/'Premissas'!{prem_col}17",
                f"={col_name}7/'Premissas'!{prem_col}16",
                f"={col_name}8/'Premissas'!{prem_col}15",
                f"='Premissas'!{prem_col}17",
                div_formula(f"'Breakeven 7M'!{be_col}{be_media_row}/{col_name}9*1000"),
                f"='Breakeven 7M'!{be_col}{be_cps_row}",
                f"='Breakeven 7M'!{be_col}{be_cpv_row}",
            ]
            percent_rows = {10}
            currency_rows = {4, 5, 11, 12, 13, 14}
        else:
            page_views = sessions * pageviews_per_session
            values = [
                proj["revenue"],
                proj["ticket"],
                purchase,
                add_cart,
                view_item,
                sessions,
                page_views,
                proj["final_conversion"],
                proj["cps"],
                proj["cpv"],
            ]
            formulas = [
                f"='Breakeven 7M'!{be_col}18",
                f"='Breakeven 7M'!{be_col}15",
                f"='Breakeven 7M'!{be_col}11",
                f"={col_name}6/'Premissas'!{prem_col}17",
                f"={col_name}7/'Premissas'!{prem_col}16",
                f"={col_name}8/'Premissas'!{prem_col}15",
                f"={col_name}9*($B$6/$B$5)",
                f"='Breakeven 7M'!{be_col}13",
                f"='Breakeven 7M'!{be_col}6",
                f"='Breakeven 7M'!{be_col}12",
            ]
            percent_rows = {11}
            currency_rows = {4, 5, 12, 13}
        for row_offset, (formula, value) in enumerate(zip(formulas, values), 4):
            fmt = formula_percent if row_offset in percent_rows else formula_currency if row_offset in currency_rows else formula_int
            funnel.write_formula(row_offset, col, formula, fmt, value)

    funnel.merge_range(f"G16:{funnel_proj_last_name}16", "Taxas usadas na projeção", section)
    if is_inside_sales and has_lead_quali:
        rate_rows = [
            "Impressões → Cliques",
            "Cliques → Leads",
            "Leads → Lead quali",
            "Lead quali → MQLs",
            "MQLs → SQLs",
            "SQLs → Vendas",
        ]
        rate_prem_rows = [15, 16, 17, 18, 19, 20]
        note_start_row = 23
    elif is_inside_sales:
        rate_rows = ["Impressões → Cliques", "Cliques → Leads", "Leads → Vendas"]
        rate_prem_rows = [15, 16, 17]
        note_start_row = 21
    else:
        rate_rows = ["Sessão → View item", "View item → Add to cart", "Add to cart → Purchase"]
        rate_prem_rows = [15, 16, 17]
        note_start_row = 21
    for idx, stage in enumerate(rate_rows, 16):
        funnel.write(idx, 6, stage, label)
    rate_series_by_prem_row = {
        15: view_rates,
        16: cart_rates,
        17: lead_lead_quali_rates if is_inside_sales and has_lead_quali else lead_to_sale_rates,
        18: lead_quali_mql_rates,
        19: mql_sql_rates,
        20: sql_sale_rates,
    }
    for idx in range(projection_months):
        col = funnel_proj_start_col + idx
        prem_col = xlsxwriter.utility.xl_col_to_name(prem_proj_start_col + idx)
        for offset, prem_row in enumerate(rate_prem_rows):
            series = rate_series_by_prem_row[prem_row]
            funnel.write_formula(
                16 + offset,
                col,
                f"='Premissas'!{prem_col}{prem_row}",
                formula_percent,
                series[idx],
            )
    funnel.merge_range(
        f"G{note_start_row}:{funnel_proj_last_name}{note_start_row + 2}",
        "O funil gerencial preserva as etapas confiáveis do tracking. As etapas detalhadas permanecem no bloco da esquerda para orientar a auditoria técnica do GTM/GA4.",
        note,
    )

    # Resumo Executivo
    summary = workbook.add_worksheet("Resumo Executivo")
    summary.set_tab_color(colors["navy"])
    summary.hide_gridlines(2)
    summary.set_column("A:A", 3)
    summary.set_column("B:J", 14)
    summary.merge_range("B2:J3", build_resumo_title(client, is_inside_sales), title)
    summary.merge_range("B5:D5", "Resultado atual", card_label)
    summary.merge_range("B6:D8", "", card_value)
    summary.write_formula("B6", f"='Breakeven 7M'!B{33 if use_unified_breakeven else 28}", card_value, current_result)
    summary.merge_range("E5:G5", "Breakeven mensal", card_label)
    summary.merge_range("E6:G8", "", card_value)
    summary.write_formula("E6", "='Premissas'!F8", card_value, current_monthly_break_even)
    summary.merge_range("H5:J5", f"Receita necessária em {projection_months} meses", card_label)
    summary.merge_range("H6:J8", "", card_value)
    summary.write_formula("H6", f"='Breakeven 7M'!C{36 if use_unified_breakeven else 32}", card_value, future_revenue_required)

    summary.merge_range("B11:J11", "Cenário atual x cenário mínimo", section)
    summary_headers = ["Indicador", "Atual", f"Mínimo {projection_months}M", "Leitura"]
    summary.merge_range("B12:C12", summary_headers[0], header)
    summary.merge_range("D12:E12", summary_headers[1], header)
    summary.merge_range("F12:G12", summary_headers[2], header)
    summary.merge_range("H12:J12", summary_headers[3], header)
    comparison = [
        ("Faturamento", revenue_total, future_revenue_required, "Recupera déficit + custos futuros"),
        ("Conversão final", sales_total / leads_total if is_inside_sales and leads_total else sales_total / sessions_total, (sum(p["sales"] for p in projections) / sum(p["sales"] / lead_to_sale_rates[i] for i, p in enumerate(projections) if lead_to_sale_rates[i])) if is_inside_sales else sum(p["sales"] for p in projections) / sum(p["sessions"] for p in projections), "Melhora gradual do funil"),
        ("Ticket médio", current_ticket, future_revenue_required / sum(p["sales"] for p in projections), "Crescimento leve de 1% ao mês"),
        (
            "Custo por impressão" if is_inside_sales else "Custo por sessão",
            media_total / sessions_total,
            projection_months * monthly_media / sum(p["sessions"] for p in projections),
            "Exige eficiência e tráfego não pago",
        ),
        ("Resultado líquido", current_result, 0, f"Projeto zerado no {minimum_breakeven_label}"),
    ]
    for ridx, (indicator, current, minimum, reading) in enumerate(comparison, 12):
        summary.merge_range(ridx, 1, ridx, 2, indicator, label)
        fmt = normal_percent if "Conversão" in indicator else normal_currency
        summary.merge_range(ridx, 3, ridx, 4, current, fmt)
        summary.merge_range(ridx, 5, ridx, 6, minimum, fmt)
        summary.merge_range(ridx, 7, ridx, 9, reading, normal)

    summary.merge_range("B20:J20", "Evolução financeira", section)
    chart = workbook.add_chart({"type": "line"})
    chart_result_row = 33 if use_unified_breakeven else 28
    chart_header_row = 2 if use_unified_breakeven else 2
    chart.add_series(
        {
            "name": "Resultado líquido acumulado",
            "categories": f"='Breakeven 7M'!$E${chart_header_row}:${be_proj_last_name}${chart_header_row}",
            "values": f"='Breakeven 7M'!$E${chart_result_row}:${be_proj_last_name}${chart_result_row}",
            "line": {"color": colors["teal"], "width": 3},
            "marker": {"type": "circle", "size": 6, "border": {"color": colors["teal"]}, "fill": {"color": colors["white"]}},
        }
    )
    chart.set_title({"name": "Recuperação do déficit acumulado"})
    chart.set_y_axis({"name": "Resultado acumulado", "num_format": 'R$ #,##0', "major_gridlines": {"visible": True}})
    chart.set_x_axis({"name": "Mês"})
    chart.set_legend({"none": True})
    chart.set_style(10)
    summary.insert_chart("B22", chart, {"x_scale": 1.15, "y_scale": 1.2})

    summary.merge_range(
        "H22:J27",
        build_strategic_reading(
            config_data,
            is_inside_sales=is_inside_sales,
            minimum_breakeven_label=minimum_breakeven_label,
            financial_rows=minimum_financial,
        ),
        note,
    )
    breakeven_status_text = (
        "JÁ BREAKEVADO NO HISTÓRICO"
        if already_historical_breakeven
        else (
            f"BREAKEVEN NO {minimum_breakeven_label.upper()}"
            if projections[-1]["cumulative_result"] >= -0.01
            else f"REVISAR CENÁRIO — {minimum_breakeven_label.upper()}"
        )
    )
    summary_status_fmt = status_ok if projections[-1]["cumulative_result"] >= -0.01 or already_historical_breakeven else status_bad
    summary.merge_range("H29:J29", "Status", card_label)
    summary.merge_range("H30:J32", breakeven_status_text, summary_status_fmt)

    summary.merge_range("B42:J42", "Comparativo dos três cenários", section)
    for col, text in enumerate(["Cenário", f"Receita {projection_months}M", f"Mídia {projection_months}M", "Saldo final", "Mês de breakeven"], 1):
        if col == 1:
            summary.merge_range(42, 1, 42, 2, text, header)
        elif col == 2:
            summary.merge_range(42, 3, 42, 4, text, header)
        elif col == 3:
            summary.merge_range(42, 5, 42, 6, text, header)
        elif col == 4:
            summary.merge_range(42, 7, 42, 8, text, header)
        else:
            summary.write(42, 9, text, header)
    scenario_summary = [
        (
            "Cenário mínimo (Breakeven)",
            sum(projected_revenue),
            sum(row["media"] for row in minimum_financial),
            projections[-1]["cumulative_result"],
            minimum_breakeven_label,
        )
    ]
    for scenario_name in ("Pessimista", "Realista", "Otimista"):
        config = scenario_configs[scenario_name]
        plan = scenario_financial_plans[scenario_name]
        scenario_summary.append(
            (
                scenario_name,
                sum(config["revenue"]),
                sum(row["media"] for row in plan),
                plan[-1]["cumulative_result"],
                breakeven_month_from_rows(plan),
            )
        )
    for idx, (name, revenue, media, balance, month) in enumerate(scenario_summary, 43):
        summary.merge_range(idx, 1, idx, 2, name, label)
        if name == "Cenário mínimo (Breakeven)":
            be_revenue_row = 25 if use_unified_breakeven else 18
            be_media_row = 5 if use_unified_breakeven else 4
            be_result_last_col = f"{be_proj_last_name}{33 if use_unified_breakeven else 28}"
            summary.merge_range(idx, 3, idx, 4, "", formula_currency)
            summary.write_formula(idx, 3, f"='Breakeven 7M'!C{be_revenue_row}", formula_currency, revenue)
            summary.merge_range(idx, 5, idx, 6, "", formula_currency)
            summary.write_formula(idx, 5, f"='Breakeven 7M'!C{be_media_row}", formula_currency, media)
            summary.merge_range(idx, 7, idx, 8, "", formula_currency)
            summary.write_formula(idx, 7, f"='Breakeven 7M'!{be_result_last_col}", formula_currency, balance)
        else:
            sheet = name
            summary.merge_range(idx, 3, idx, 4, "", formula_currency)
            summary.write_formula(idx, 3, f"='{sheet}'!D6", formula_currency, revenue)
            summary.merge_range(idx, 5, idx, 6, "", formula_currency)
            summary.write_formula(idx, 5, f"='{sheet}'!D4", formula_currency, media)
            summary.merge_range(idx, 7, idx, 8, "", formula_currency)
            summary.write_formula(idx, 7, f"='{sheet}'!D11", formula_currency, balance)
        summary.write(
            idx,
            9,
            month,
            status_ok if month != "Não breakeva" else status_bad,
        )

    # Ordem das abas
    summary.activate()
    summary.set_first_sheet()
    workbook.worksheets_objs = [summary, be, pessimista, realista, otimista, funnel, prem, data]

    workbook.close()
    print(output)


if __name__ == "__main__":
    main()
