"""
Helper puro do gerador de breakeven.

Extraído de generate_breakeven.py (linhas 31–1007) para reduzir o custo de
leitura por sessão: mudanças em helpers não exigem carregar as 4849 linhas
do arquivo principal. Importar via:

    from generate_breakeven_helpers import *   # em generate_breakeven.py
"""

# ── Constantes ────────────────────────────────────────────────────────────────

MAX_PROJECTION_MONTHS = 72
DEFAULT_SCENARIO_SHEET_ORDER = ("Pessimista", "Realista", "Otimista")
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

# Linhas de "ruído" do funil marketplace (pass-through MQL→SQL/SQL→Venda + nós e CPS
# duplicados) que são ocultadas. O funil continua completo e auditável (linhas existem,
# só ficam hidden), mas a visão fica limpa: Impressões → Cliques → Visitas → Compras → Faturado.
MARKETPLACE_SCENARIO_HIDE_ROWS = (22, 23, 24, 25, 35)
MARKETPLACE_INTEGRATED_HIDE_ROWS = (43, 44, 45, 46, 47, 48, 56)

# Renomeação das etapas do funil para os termos do marketplace.
MARKETPLACE_STAGE_LABELS = {
    "impression_click": "Impressões → Cliques",
    "click_lead": "Cliques → Visitas",
    "lead_mql": "Visitas → Compras",
}
# Linhas do painel de controle de Premissas (advance A20:A24 / baseline A28:A32)
# correspondentes às etapas pass-through ocultadas no marketplace.
MARKETPLACE_PREM_HIDE_ROWS = (23, 24, 31, 32)

PREM_SCENARIO_ADVANCE_COL = {
    "Pessimista": "B",
    "Realista": "C",
    "Otimista": "D",
    "Mídia V4": "C",
}
# (rate_key, scenario_sheet_row, baseline_excel_row, advance_excel_row, label)
PREM_FUNNEL_CONTROL_STAGES = (
    ("impression_click", 17, 28, 20, "Impressões → Cliques"),
    ("click_lead", 19, 29, 21, "Cliques → Leads"),
    ("lead_mql", 21, 30, 22, "Leads → MQL"),
    ("mql_sql", 23, 31, 23, "MQL → SQL"),
    ("sql_sale", 25, 32, 24, "SQLs → Vendas"),
)
PREM_MONTHLY_RATE_ROWS = (14, 15, 16, 17, 18)

INSIDE_SALES_INTEGRATED_SKIP_ROWS = frozenset({46, 47, 49, 50, 51, 52})
INSIDE_SALES_INTEGRATED_SKIP_ROWS_LEAD_QUALI = frozenset({49, 50, 51, 52})
INSIDE_SALES_SCENARIO_SKIP_ROWS = frozenset({26, 27, 28, 29, 30, 31})
INSIDE_SALES_SCENARIO_SKIP_ROWS_LEAD_QUALI = frozenset({28, 29, 30, 31})
INSIDE_SALES_INTEGRATED_RATE_ROWS = frozenset({38, 40, 42, 44, 48})
INSIDE_SALES_INTEGRATED_RATE_ROWS_LEAD_QUALI = frozenset({38, 40, 42, 44, 46, 48})
INSIDE_SALES_SCENARIO_RATE_ROWS = frozenset({17, 19, 21, 23, 25})
INSIDE_SALES_SCENARIO_RATE_ROWS_LEAD_QUALI = frozenset({17, 19, 21, 23, 25, 27})

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

INSIDE_SALES_BASELINE_VOLUME_ROWS = {
    16: "impressions",
    18: "clicks",
    20: "leads",
    22: "mqls",
    24: "sqls",
    32: "sales",
}


# ── Funções utilitárias ───────────────────────────────────────────────────────

def div_formula(expr: str, default: str = "0") -> str:
    """Wrap a division expression with IFERROR for Google Sheets stability."""
    return f"=IFERROR({expr},{default})"


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


# ── Expressões de taxa (fórmulas de referência ao Premissas) ─────────────────

def full_funnel_rate_expr(prem_col: str) -> str:
    return f"'Premissas'!{prem_col}15*'Premissas'!{prem_col}16*'Premissas'!{prem_col}17"


def inside_sales_lead_to_sale_expr(prem_col: str, has_lead_quali: bool) -> str:
    if has_lead_quali:
        return (
            f"'Premissas'!{prem_col}17*'Premissas'!{prem_col}18*"
            f"'Premissas'!{prem_col}19*'Premissas'!{prem_col}20"
        )
    return (
        f"'Premissas'!{prem_col}17*'Premissas'!{prem_col}18*"
        f"'Premissas'!{prem_col}19"
    )


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
    return (
        f"'Premissas'!{prem_col}15*'Premissas'!{prem_col}16*'Premissas'!{prem_col}17*"
        f"'Premissas'!{prem_col}18*'Premissas'!{prem_col}19"
    )


# ── BEU helpers ───────────────────────────────────────────────────────────────

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


# ── Detecção de modelo ────────────────────────────────────────────────────────

def is_inside_sales_model(project_model: str) -> bool:
    return "inside sales" in (project_model or "").lower()


def is_marketplace_model(project_model: str) -> bool:
    """Funil de marketplace (3º funil GP): Impressões → Cliques → Visitas → Compras → Faturado.

    Estruturalmente reusa todo o trilho Inside Sales (entrada por impressões, CPS por
    impressão, 5 estágios), porém as 2 últimas taxas (MQL→SQL, SQL→Venda) são pass-through
    1,0 e ficam OCULTAS na planilha; as etapas visíveis são renomeadas para os termos do
    marketplace. Os números são idênticos ao IS — só muda o funil exibido.
    """
    return "marketplace" in (project_model or "").lower()


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


# ── Células de referência ao Premissas ───────────────────────────────────────

def prem_baseline_cell(excel_row: int) -> str:
    return f"'Premissas'!$B${excel_row}"


def prem_scenario_advance_cell(scenario_name: str, excel_row: int) -> str:
    col = PREM_SCENARIO_ADVANCE_COL.get(scenario_name, "C")
    return f"'Premissas'!${col}${excel_row}"


def prem_realista_advance_cell(excel_row: int) -> str:
    return prem_scenario_advance_cell("Realista", excel_row)


def prem_ceiling_cell(baseline_excel_row: int) -> str:
    """Teto da etapa fica na coluna C, na mesma linha do baseline (C28:C32)."""
    return f"'Premissas'!$C${baseline_excel_row}"


def rate_cap_term(baseline_excel_row: int, max_rate: float, use_stage_ceilings: bool) -> str:
    """Termo do MIN(): teto editável por etapa (Premissas C) ou cap único 95%."""
    return prem_ceiling_cell(baseline_excel_row) if use_stage_ceilings else f"{max_rate}"


def compound_stage_rate_formula(
    *,
    scenario_name: str,
    sheet_row: int,
    baseline_excel_row: int,
    advance_excel_row: int,
    prev_col_name: str | None,
    month_idx: int,
    max_rate: float,
    use_stage_ceilings: bool = False,
) -> str:
    if month_idx == 0:
        return f"={prem_baseline_cell(baseline_excel_row)}"
    assert prev_col_name
    cap = rate_cap_term(baseline_excel_row, max_rate, use_stage_ceilings)
    return (
        f"=MIN({cap},{prev_col_name}{sheet_row}"
        f"*(1+{prem_scenario_advance_cell(scenario_name, advance_excel_row)}))"
    )


def compound_premissas_rate_formula(
    *,
    prem_row_0: int,
    baseline_excel_row: int,
    advance_excel_row: int,
    prev_col_name: str | None,
    month_idx: int,
    max_rate: float,
    use_stage_ceilings: bool = False,
) -> str:
    excel_row = prem_row_0 + 1
    if month_idx == 0:
        return f"={prem_baseline_cell(baseline_excel_row)}"
    assert prev_col_name
    cap = rate_cap_term(baseline_excel_row, max_rate, use_stage_ceilings)
    return (
        f"=MIN({cap},{prev_col_name}{excel_row}"
        f"*(1+{prem_realista_advance_cell(advance_excel_row)}))"
    )


def scenario_stage_by_sheet_row() -> dict[int, tuple[str, int, int, int, str]]:
    return {stage[1]: stage for stage in PREM_FUNNEL_CONTROL_STAGES}


# ── Rótulos de linhas por aba ─────────────────────────────────────────────────

def integrated_funnel_row_labels(
    is_inside_sales: bool,
    final_funnel_rate_label: str,
    lead_quali: bool = False,
    extra_label: str = "Lead quali",
    is_marketplace: bool = False,
) -> dict[int, str]:
    if is_marketplace:
        return {
            37: "Impressões",
            38: "Taxa Impressões → Cliques",
            39: "Cliques",
            40: "Taxa Cliques → Visitas",
            41: "Visitas",
            42: "Taxa Visitas → Compras",
            53: "Compras",
            54: final_funnel_rate_label,
            55: "Custo por impressão",
            57: "Custo por compra",
        }
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
            42: f"Taxa Leads → {extra_label}",
            43: extra_label,
            44: f"Taxa {extra_label} → MQLs",
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
    extra_label: str = "Lead quali",
    is_marketplace: bool = False,
) -> dict[int, str]:
    if is_marketplace:
        return {
            16: "Impressões",
            17: "Taxa Impressões → Cliques",
            18: "Cliques",
            19: "Taxa Cliques → Visitas",
            20: "Visitas",
            21: "Taxa Visitas → Compras",
            32: "Compras",
            33: final_funnel_rate_label,
            34: "Custo por impressão",
            36: "Custo por compra",
            37: "Faturado",
            38: "Diferença vs. faturamento alvo",
        }
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
            21: f"Taxa Leads → {extra_label}",
            22: extra_label,
            23: f"Taxa {extra_label} → MQLs",
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


def breakeven_financial_row_labels(
    is_inside_sales: bool, funnel_conversion_label: str, is_marketplace: bool = False
) -> dict[int, str]:
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
    if is_marketplace:
        labels.update(
            {
                5: "Impressões por mês",
                6: "Custo por impressão",
                7: "Taxa Impressões → Compras",
                8: "Compras por mês",
                9: "Custo por compra",
                13: "Taxa de Conversão Impressões → Compras",
            }
        )
    elif is_inside_sales:
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


# ── Helpers de funil Inside Sales ─────────────────────────────────────────────

def accumulated_funnel_from_benchmark(
    benchmark_months: list,
    media_total: float,
    *,
    has_lead_quali: bool,
) -> dict[str, float]:
    impressions = sum(row[1] for row in benchmark_months)
    clicks = sum(row[2] for row in benchmark_months)
    leads = sum(row[3] for row in benchmark_months)
    if has_lead_quali:
        lead_quali = sum(row[4] for row in benchmark_months)
        mqls = sum(row[5] for row in benchmark_months)
        sqls = sum(row[6] for row in benchmark_months)
        sales = sum(row[8] for row in benchmark_months)
    else:
        mqls = sum(row[4] for row in benchmark_months)
        sqls = sum(row[5] for row in benchmark_months)
        sales = sum(row[8] for row in benchmark_months)
        lead_quali = mqls
    return {
        "media": media_total,
        "impressions": impressions,
        "clicks": clicks,
        "leads": leads,
        "lead_quali": lead_quali,
        "mqls": mqls,
        "sqls": sqls,
        "sales": sales,
    }


def inside_sales_reference_cps(
    *,
    current_month_media: float,
    current_sessions: float,
    accumulated_media: float,
    accumulated_sessions: float,
    min_cost_per_impression: float,
) -> float:
    if current_sessions > 0 and current_month_media > 0:
        cps = current_month_media / current_sessions
    elif accumulated_sessions > 0:
        cps = accumulated_media / accumulated_sessions
    else:
        cps = min_cost_per_impression
    return max(min_cost_per_impression, cps)


def project_inside_sales_impressions(monthly_media: float, reference_cps: float) -> float:
    if reference_cps <= 0:
        return 0.0
    return monthly_media / reference_cps


def build_inside_sales_funnel_forward(
    media: float,
    reference_cps: float,
    rates: dict[str, float],
    has_lead_quali: bool = False,
    *,
    baseline_volumes: dict[str, float] | None = None,
    month_idx: int = 0,
) -> dict[str, float]:
    if baseline_volumes:
        if month_idx == 0:
            impressions = baseline_volumes["impressions"]
            clicks = baseline_volumes["clicks"]
            leads = baseline_volumes["leads"]
            mqls = baseline_volumes["mqls"]
            sqls = baseline_volumes["sqls"]
            sales = baseline_volumes["sales"]
        else:
            impressions = baseline_volumes["impressions"]
            clicks = impressions * rates["session_view"]
            leads = clicks * rates["view_add"]
            mqls = leads * rates["add_view_cart"]
            sqls = mqls * rates["viewcart_checkout"]
            sales = sqls * rates["shipping_payment"]
        if has_lead_quali:
            view_cart = mqls
            begin_checkout = sqls
            checkout = sqls
        else:
            view_cart = mqls
            begin_checkout = sqls
            checkout = sqls
        return {
            "sessions": impressions,
            "view_item": clicks,
            "add_cart": leads,
            "view_cart": view_cart,
            "begin_checkout": begin_checkout,
            "checkout": checkout,
            "shipping": checkout,
            "payment": sales,
            "orders": checkout,
            "sales": sales,
        }
    sessions = project_inside_sales_impressions(media, reference_cps)
    view_item = sessions * rates["session_view"]
    add_cart = view_item * rates["view_add"]
    if has_lead_quali:
        view_cart = add_cart * rates["add_view_cart"]
        begin_checkout = view_cart * rates["viewcart_checkout"]
        checkout = begin_checkout * rates["checkout_shipping"]
    else:
        view_cart = add_cart * rates["add_view_cart"]
        begin_checkout = view_cart * rates["viewcart_checkout"]
        checkout = begin_checkout
    sales = checkout * rates["shipping_payment"]
    return {
        "sessions": sessions,
        "view_item": view_item,
        "add_cart": add_cart,
        "view_cart": view_cart,
        "begin_checkout": begin_checkout,
        "checkout": checkout,
        "shipping": checkout,
        "payment": sales,
        "orders": checkout,
        "sales": sales,
    }


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
            38: "=0",
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
        38: "=0",
    }


def inside_sales_ltv_revenue_formula(
    col_name: str,
    recurrence_months: int = 1,
    *,
    ticket_cell: str | None = None,
) -> str:
    """Faturamento LTV = vendas × ticket GP mensal (linha 7) × recorrência SR."""
    ticket_ref = ticket_cell or f"{col_name}7"
    if recurrence_months > 1:
        return f"={col_name}32*{ticket_ref}*{recurrence_months}"
    return f"={col_name}32*{ticket_ref}"


def inside_sales_forward_volume_formulas(
    col_name: str,
    *,
    has_lead_quali: bool,
    reference_cps_cell: str = "$B$34",
    baseline_impressions_cell: str | None = None,
    final_rate_volume_row: int = 20,
    tm_recurrence_months: int = 1,
) -> dict[int, str]:
    """Funil forward: impressões baseline (mediana 3M) × taxas editáveis → vendas → faturamento."""
    revenue_formula = inside_sales_ltv_revenue_formula(col_name, tm_recurrence_months)
    impressions_formula = (
        f"=ROUND({baseline_impressions_cell},0)"
        if baseline_impressions_cell
        else f"=ROUND({col_name}4/{reference_cps_cell},0)"
    )
    if has_lead_quali:
        return {
            16: impressions_formula,
            18: f"=ROUND({col_name}16*{col_name}17,0)",
            20: f"=ROUND({col_name}18*{col_name}19,0)",
            22: f"=ROUND({col_name}20*{col_name}21,0)",
            24: f"=ROUND({col_name}22*{col_name}23,0)",
            26: f"=ROUND({col_name}24*{col_name}25,0)",
            32: f"=ROUND({col_name}26*{col_name}27,0)",
            33: f"={col_name}32/{col_name}{final_rate_volume_row}",
            34: f"={col_name}4/{col_name}16",
            35: f"={col_name}4/{col_name}26",
            36: f"={col_name}4/{col_name}32",
            37: revenue_formula,
            38: "=0",
        }
    return {
        16: impressions_formula,
        18: f"=ROUND({col_name}16*{col_name}17,0)",
        20: f"=ROUND({col_name}18*{col_name}19,0)",
        22: f"=ROUND({col_name}20*{col_name}21,0)",
        24: f"=ROUND({col_name}22*{col_name}23,0)",
        32: f"=ROUND({col_name}24*{col_name}25,0)",
        33: f"={col_name}32/{col_name}{final_rate_volume_row}",
        34: f"={col_name}4/{col_name}16",
        35: f"={col_name}4/{col_name}24",
        36: f"={col_name}4/{col_name}32",
        37: revenue_formula,
        38: "=0",
    }
