"""Aba Breakeven unificada — funil completo + financeiro (inside sales + e-commerce)."""
from __future__ import annotations

import xlsxwriter

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


def beu_row_labels_ecommerce() -> dict[int, str]:
    return {
        BEU["cost_total"]: "Custos Fixos V4 + Mídia",
        BEU["fee"]: "Fee Mensal",
        BEU["media"]: "Verba de mídia",
        BEU["impressions"]: "Sessões por mês",
        BEU["rate_imp_click"]: "Taxa Sessão → View item",
        BEU["clicks"]: "View item",
        BEU["rate_click_lead"]: "Taxa View item → Add cart",
        BEU["leads"]: "Add to cart",
        BEU["rate_lead_quali"]: "Taxa Add cart → View cart",
        BEU["lead_quali"]: "View cart",
        BEU["rate_quali_mql"]: "Taxa View cart → Checkout",
        BEU["mqls"]: "Checkout",
        BEU["rate_mql_sql"]: "Taxa Checkout → Pedido",
        BEU["sqls"]: "Pedidos por mês",
        BEU["rate_sql_sale"]: "Taxa Pedido → Venda",
        BEU["sales"]: "Vendas por mês",
        BEU["rate_lead_sale"]: "Taxa Sessão → Venda",
        BEU["cps"]: "Custo por sessão",
        BEU["cost_sql"]: "Custo por pedido",
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


def beu_row_labels(extra_label: str = "Lead quali") -> dict[int, str]:
    return {
        BEU["cost_total"]: "Custos Fixos V4 + Mídia",
        BEU["fee"]: "Fee Mensal",
        BEU["media"]: "Verba de mídia",
        BEU["impressions"]: "Impressões por mês",
        BEU["rate_imp_click"]: "Taxa Impressões → Cliques",
        BEU["clicks"]: "Cliques",
        BEU["rate_click_lead"]: "Taxa Cliques → Leads",
        BEU["leads"]: "Leads",
        BEU["rate_lead_quali"]: f"Taxa Leads → {extra_label}",
        BEU["lead_quali"]: extra_label,
        BEU["rate_quali_mql"]: f"Taxa {extra_label} → MQLs",
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


def write_unified_breakeven_worksheet(
    *,
    workbook: xlsxwriter.Workbook,
    client: str,
    projection_months: int,
    month_headers: list[str],
    be_proj_last_name: str,
    title,
    header,
    label,
    note,
    status_ok,
    status_bad,
    formula_currency,
    formula_percent,
    formula_int,
    formula_number,
    input_percent,
    div_formula,
    inside_sales_lead_to_sale_expr,
    funnel_mode: str = "inside_sales",
    extra_label: str = "Lead quali",
    colors: dict,
    current_cost: float,
    fee_total: float,
    media_total: float,
    sessions_total: float,
    sales_total: float,
    revenue_total: float,
    current_ticket: float,
    margin: float,
    current_mc: float,
    current_result: float,
    current_lead_to_sale: float,
    current_view_item: float,
    current_add_cart: float,
    current_view_cart: float,
    current_checkout: float,
    current_shipping: float,
    current_orders: float | None = None,
    monthly_fee: float,
    monthly_media: float,
    future_revenue_required: float,
    minimum_breakeven_label: str,
    projections: list[dict],
    minimum_cached: list[dict],
) -> xlsxwriter.worksheet.Worksheet:
    is_ecommerce = funnel_mode == "ecommerce"
    row_labels = beu_row_labels_ecommerce() if is_ecommerce else beu_row_labels(extra_label)
    order_volume = current_orders if is_ecommerce and current_orders else current_shipping
    be = workbook.add_worksheet("Breakeven 7M")
    be.set_tab_color(colors["teal"])
    be.hide_gridlines(2)
    be.freeze_panes(2, 4)
    be.set_column("A:A", 38)
    be.set_column("B:C", 19)
    be.set_column("D:D", 3)
    be.set_column(f"E:{be_proj_last_name}", 15)

    be.merge_range(f"A1:{be_proj_last_name}1", f"Projeção Breakeven — {client}", title)
    header_cells = [
        "Indicador",
        "Feito até o momento",
        f"Cenário mínimo {projection_months}M",
        "",
        *month_headers,
    ]
    for col, text in enumerate(header_cells):
        be.write(beu_write_index(BEU["header"]), col, text, header if col != 3 else label)

    for row, text in row_labels.items():
        be.write(beu_write_index(row), 0, text, label)

    rate_rows = {
        BEU["rate_imp_click"],
        BEU["rate_click_lead"],
        BEU["rate_lead_quali"],
        BEU["rate_quali_mql"],
        BEU["rate_mql_sql"],
        BEU["rate_sql_sale"],
        BEU["rate_lead_sale"],
    }
    volume_rows = {
        BEU["impressions"],
        BEU["clicks"],
        BEU["leads"],
        BEU["lead_quali"],
        BEU["mqls"],
        BEU["sqls"],
        BEU["sales"],
    }

    def fmt_for(row: int, editable_rate: bool = False):
        if row in rate_rows or row == BEU["margin"]:
            return input_percent if editable_rate else formula_percent
        if row in {BEU["roas"], BEU["roi_month"], BEU["roi_project"]}:
            return formula_number
        if row in volume_rows:
            return formula_int
        return formula_currency

    current_values = {
        BEU["cost_total"]: current_cost,
        BEU["fee"]: fee_total,
        BEU["media"]: media_total,
        BEU["impressions"]: sessions_total,
        BEU["rate_imp_click"]: current_view_item / sessions_total if sessions_total else 0,
        BEU["clicks"]: current_view_item,
        BEU["rate_click_lead"]: current_add_cart / current_view_item if current_view_item else 0,
        BEU["leads"]: current_add_cart,
        BEU["rate_lead_quali"]: current_view_cart / current_add_cart if current_add_cart else 0,
        BEU["lead_quali"]: current_view_cart,
        BEU["rate_quali_mql"]: current_checkout / current_view_cart if current_view_cart else 0,
        BEU["mqls"]: current_checkout,
        BEU["rate_mql_sql"]: current_shipping / current_checkout if current_checkout else 0,
        BEU["sqls"]: order_volume,
        BEU["rate_sql_sale"]: (
            sales_total / order_volume if is_ecommerce and order_volume else sales_total / current_shipping if current_shipping else 0
        ),
        BEU["sales"]: sales_total,
        BEU["rate_lead_sale"]: (
            sales_total / sessions_total
            if is_ecommerce and sessions_total
            else current_lead_to_sale
        ),
        BEU["cps"]: media_total / sessions_total if sessions_total else 0,
        BEU["cost_sql"]: (
            media_total / order_volume
            if is_ecommerce and order_volume
            else media_total / current_shipping if current_shipping else 0
        ),
        BEU["cpv"]: media_total / sales_total if sales_total else 0,
        BEU["ticket"]: current_ticket,
        BEU["margin"]: margin,
        BEU["revenue"]: revenue_total,
        BEU["revenue_acc"]: revenue_total,
        BEU["roas"]: revenue_total / media_total if media_total else 0,
        BEU["mc_month"]: current_mc,
        BEU["mc_acc"]: current_mc,
        BEU["cost_month"]: current_cost,
        BEU["cost_acc"]: current_cost,
        BEU["result_month"]: current_result,
        BEU["result_acc"]: current_result,
        BEU["roi_month"]: current_mc / current_cost if current_cost else 0,
        BEU["roi_project"]: current_mc / current_cost if current_cost else 0,
        BEU["future_revenue"]: future_revenue_required,
    }
    current_formulas = {
        BEU["cost_total"]: "='Premissas'!B9",
        BEU["fee"]: "='Premissas'!B7",
        BEU["media"]: "='Premissas'!B8",
        BEU["impressions"]: "='Premissas'!B11",
        BEU["rate_imp_click"]: div_formula(f"B{BEU['clicks']}/B{BEU['impressions']}"),
        BEU["rate_click_lead"]: div_formula(f"B{BEU['leads']}/B{BEU['clicks']}"),
        BEU["rate_lead_quali"]: div_formula(f"B{BEU['lead_quali']}/B{BEU['leads']}"),
        BEU["rate_quali_mql"]: div_formula(f"B{BEU['mqls']}/B{BEU['lead_quali']}"),
        BEU["rate_mql_sql"]: div_formula(f"B{BEU['sqls']}/B{BEU['mqls']}"),
        BEU["rate_sql_sale"]: div_formula(f"B{BEU['sales']}/B{BEU['sqls']}"),
        BEU["sales"]: "='Premissas'!B13",
        BEU["rate_lead_sale"]: (
            div_formula(f"B{BEU['sales']}/B{BEU['impressions']}")
            if is_ecommerce
            else div_formula(f"B{BEU['sales']}/B{BEU['leads']}")
        ),
        BEU["cps"]: div_formula(f"B{BEU['media']}/B{BEU['impressions']}"),
        BEU["cost_sql"]: div_formula(f"B{BEU['media']}/B{BEU['sqls']}"),
        BEU["cpv"]: div_formula(f"B{BEU['media']}/B{BEU['sales']}"),
        BEU["ticket"]: "='Premissas'!B14",
        BEU["margin"]: "='Premissas'!B15",
        BEU["revenue"]: "='Premissas'!B10",
        BEU["revenue_acc"]: f"=B{BEU['revenue']}",
        BEU["roas"]: div_formula(f"B{BEU['revenue']}/B{BEU['media']}"),
        BEU["mc_month"]: f"=B{BEU['revenue']}*B{BEU['margin']}",
        BEU["mc_acc"]: f"=B{BEU['mc_month']}",
        BEU["cost_month"]: f"=B{BEU['cost_total']}",
        BEU["cost_acc"]: f"=B{BEU['cost_month']}",
        BEU["result_month"]: f"=B{BEU['mc_month']}-B{BEU['cost_month']}",
        BEU["result_acc"]: f"=B{BEU['result_month']}",
        BEU["roi_month"]: div_formula(f"B{BEU['mc_month']}/B{BEU['cost_month']}"),
        BEU["roi_project"]: div_formula(f"B{BEU['mc_acc']}/B{BEU['cost_acc']}"),
        BEU["future_revenue"]: "='Premissas'!F10",
    }
    volume_only = {BEU["clicks"], BEU["leads"], BEU["lead_quali"], BEU["mqls"], BEU["sqls"]}
    for row in row_labels:
        if row == BEU["status"]:
            continue
        value = current_values[row]
        if row in volume_only:
            be.write_number(beu_write_index(row), 1, value, formula_int)
            continue
        be.write_formula(beu_write_index(row), 1, current_formulas[row], fmt_for(row), value)

    be.write_formula(
        beu_write_index(BEU["status"]),
        1,
        f'=IF(B{BEU["result_acc"]}>=0,"Já breakevado","Déficit a recuperar")',
        status_bad,
        "Déficit a recuperar",
    )

    for idx, proj in enumerate(projections):
        col = 4 + idx
        col_name = xlsxwriter.utility.xl_col_to_name(col)
        prem_col = xlsxwriter.utility.xl_col_to_name(5 + idx)
        previous_col = xlsxwriter.utility.xl_col_to_name(col - 1)
        cached = minimum_cached[idx]

        monthly_formulas = {
            BEU["cost_total"]: f"={col_name}{BEU['fee']}+{col_name}{BEU['media']}",
            BEU["fee"]: "='Premissas'!F4",
            BEU["media"]: "='Premissas'!F5",
            BEU["rate_imp_click"]: f"='Premissas'!{prem_col}15",
            BEU["rate_click_lead"]: f"='Premissas'!{prem_col}16",
            BEU["rate_lead_quali"]: f"='Premissas'!{prem_col}17",
            BEU["rate_quali_mql"]: f"='Premissas'!{prem_col}18",
            BEU["rate_mql_sql"]: f"='Premissas'!{prem_col}19",
            BEU["rate_sql_sale"]: f"='Premissas'!{prem_col}20",
            BEU["rate_lead_sale"]: f"={inside_sales_lead_to_sale_expr(prem_col, True)}",
            BEU["ticket"]: f"=B{BEU['ticket']}" if idx == 0 else f"={previous_col}{BEU['ticket']}*1.01",
            BEU["margin"]: "='Premissas'!F7",
            BEU["revenue"]: f"='Premissas'!{prem_col}14",
            BEU["revenue_acc"]: f"=SUM($E{BEU['revenue']}:{col_name}{BEU['revenue']})",
            BEU["sales"]: div_formula(f"{col_name}{BEU['revenue']}/{col_name}{BEU['ticket']}"),
            BEU["sqls"]: div_formula(f"{col_name}{BEU['sales']}/{col_name}{BEU['rate_sql_sale']}"),
            BEU["mqls"]: div_formula(f"{col_name}{BEU['sqls']}/{col_name}{BEU['rate_mql_sql']}"),
            BEU["lead_quali"]: div_formula(f"{col_name}{BEU['mqls']}/{col_name}{BEU['rate_quali_mql']}"),
            BEU["leads"]: div_formula(f"{col_name}{BEU['lead_quali']}/{col_name}{BEU['rate_lead_quali']}"),
            BEU["clicks"]: div_formula(f"{col_name}{BEU['leads']}/{col_name}{BEU['rate_click_lead']}"),
            BEU["impressions"]: div_formula(f"{col_name}{BEU['clicks']}/{col_name}{BEU['rate_imp_click']}"),
            BEU["cps"]: div_formula(f"{col_name}{BEU['media']}/{col_name}{BEU['impressions']}"),
            BEU["cost_sql"]: div_formula(f"{col_name}{BEU['media']}/{col_name}{BEU['sqls']}"),
            BEU["cpv"]: div_formula(f"{col_name}{BEU['media']}/{col_name}{BEU['sales']}"),
            BEU["roas"]: div_formula(f"{col_name}{BEU['revenue']}/{col_name}{BEU['media']}"),
            BEU["mc_month"]: f"={col_name}{BEU['revenue']}*{col_name}{BEU['margin']}",
            BEU["mc_acc"]: f"=SUM($E{BEU['mc_month']}:{col_name}{BEU['mc_month']})",
            BEU["cost_month"]: f"={col_name}{BEU['cost_total']}",
            BEU["cost_acc"]: f"=SUM($E{BEU['cost_month']}:{col_name}{BEU['cost_month']})",
            BEU["result_month"]: f"={col_name}{BEU['mc_month']}-{col_name}{BEU['cost_month']}",
            BEU["result_acc"]: f"=ROUND($B{BEU['result_acc']}+SUM($E{BEU['result_month']}:{col_name}{BEU['result_month']}),2)",
            BEU["roi_month"]: div_formula(f"{col_name}{BEU['mc_month']}/{col_name}{BEU['cost_month']}"),
            BEU["roi_project"]: div_formula(
                f"($B{BEU['mc_acc']}+{col_name}{BEU['mc_acc']})/($B{BEU['cost_acc']}+{col_name}{BEU['cost_acc']})"
            ),
        }
        monthly_values = {
            BEU["cost_total"]: proj["monthly_cost"],
            BEU["fee"]: monthly_fee,
            BEU["media"]: proj["monthly_media"],
            BEU["impressions"]: cached["sessions"],
            BEU["clicks"]: cached["view_item"],
            BEU["leads"]: cached["add_cart"],
            BEU["lead_quali"]: cached["view_cart"],
            BEU["mqls"]: cached["begin_checkout"],
            BEU["sqls"]: cached["orders"] if is_ecommerce else cached["checkout"],
            BEU["sales"]: proj["sales"],
            BEU["cps"]: proj["cps"],
            BEU["cost_sql"]: (
                proj["monthly_media"] / cached["orders"]
                if is_ecommerce and cached["orders"]
                else proj["monthly_media"] / cached["checkout"] if cached["checkout"] else 0
            ),
            BEU["cpv"]: proj["cpv"],
            BEU["ticket"]: proj["ticket"],
            BEU["margin"]: margin,
            BEU["revenue"]: proj["revenue"],
            BEU["revenue_acc"]: sum(p["revenue"] for p in projections[: idx + 1]),
            BEU["roas"]: proj["roas"],
            BEU["mc_month"]: proj["monthly_mc"],
            BEU["mc_acc"]: sum(p["monthly_mc"] for p in projections[: idx + 1]),
            BEU["cost_month"]: proj["monthly_cost"],
            BEU["cost_acc"]: sum(p["monthly_cost"] for p in projections[: idx + 1]),
            BEU["result_month"]: proj["monthly_result"],
            BEU["result_acc"]: proj["cumulative_result"],
            BEU["roi_month"]: proj["monthly_mc"] / proj["monthly_cost"] if proj["monthly_cost"] else 0,
        }

        for row in row_labels:
            if row in {BEU["future_revenue"], BEU["status"]}:
                continue
            formula = monthly_formulas.get(row)
            if not formula:
                continue
            be.write_formula(
                beu_write_index(row),
                col,
                formula,
                fmt_for(row, editable_rate=row in rate_rows),
                monthly_values.get(row, 0),
            )

    future_cost = projection_months * (monthly_fee + monthly_media)
    total_sales = sum(x["sales"] for x in minimum_cached)
    total_leads = sum(x["add_cart"] for x in minimum_cached)
    total_sessions = sum(x["sessions"] for x in minimum_cached)
    aggregate_values = {
        BEU["cost_total"]: future_cost,
        BEU["fee"]: projection_months * monthly_fee,
        BEU["media"]: projection_months * monthly_media,
        BEU["impressions"]: sum(x["sessions"] for x in minimum_cached),
        BEU["clicks"]: sum(x["view_item"] for x in minimum_cached),
        BEU["leads"]: total_leads,
        BEU["lead_quali"]: sum(x["view_cart"] for x in minimum_cached),
        BEU["mqls"]: sum(x["begin_checkout"] for x in minimum_cached),
        BEU["sqls"]: sum(x["orders"] if is_ecommerce else x["checkout"] for x in minimum_cached),
        BEU["sales"]: total_sales,
        BEU["revenue"]: future_revenue_required,
        BEU["result_acc"]: 0,
        BEU["future_revenue"]: future_revenue_required,
        BEU["rate_lead_sale"]: (
            total_sales / total_sessions
            if is_ecommerce and total_sessions
            else total_sales / total_leads if total_leads else 0
        ),
    }
    aggregate_formulas = {
        BEU["cost_total"]: f"=SUM(E{BEU['cost_total']}:{be_proj_last_name}{BEU['cost_total']})",
        BEU["fee"]: f"=SUM(E{BEU['fee']}:{be_proj_last_name}{BEU['fee']})",
        BEU["media"]: f"=SUM(E{BEU['media']}:{be_proj_last_name}{BEU['media']})",
        BEU["impressions"]: f"=SUM(E{BEU['impressions']}:{be_proj_last_name}{BEU['impressions']})",
        BEU["clicks"]: f"=SUM(E{BEU['clicks']}:{be_proj_last_name}{BEU['clicks']})",
        BEU["leads"]: f"=SUM(E{BEU['leads']}:{be_proj_last_name}{BEU['leads']})",
        BEU["lead_quali"]: f"=SUM(E{BEU['lead_quali']}:{be_proj_last_name}{BEU['lead_quali']})",
        BEU["mqls"]: f"=SUM(E{BEU['mqls']}:{be_proj_last_name}{BEU['mqls']})",
        BEU["sqls"]: f"=SUM(E{BEU['sqls']}:{be_proj_last_name}{BEU['sqls']})",
        BEU["sales"]: f"=SUM(E{BEU['sales']}:{be_proj_last_name}{BEU['sales']})",
        BEU["rate_imp_click"]: div_formula(f"C{BEU['clicks']}/C{BEU['impressions']}"),
        BEU["rate_click_lead"]: div_formula(f"C{BEU['leads']}/C{BEU['clicks']}"),
        BEU["rate_lead_quali"]: div_formula(f"C{BEU['lead_quali']}/C{BEU['leads']}"),
        BEU["rate_quali_mql"]: div_formula(f"C{BEU['mqls']}/C{BEU['lead_quali']}"),
        BEU["rate_mql_sql"]: div_formula(f"C{BEU['sqls']}/C{BEU['mqls']}"),
        BEU["rate_sql_sale"]: div_formula(f"C{BEU['sales']}/C{BEU['sqls']}"),
        BEU["rate_lead_sale"]: (
            div_formula(f"C{BEU['sales']}/C{BEU['impressions']}")
            if is_ecommerce
            else div_formula(f"C{BEU['sales']}/C{BEU['leads']}")
        ),
        BEU["cps"]: div_formula(f"C{BEU['media']}/C{BEU['impressions']}"),
        BEU["cost_sql"]: div_formula(f"C{BEU['media']}/C{BEU['sqls']}"),
        BEU["cpv"]: div_formula(f"C{BEU['media']}/C{BEU['sales']}"),
        BEU["ticket"]: div_formula(f"C{BEU['revenue']}/C{BEU['sales']}"),
        BEU["margin"]: "='Premissas'!F7",
        BEU["revenue"]: f"=SUM(E{BEU['revenue']}:{be_proj_last_name}{BEU['revenue']})",
        BEU["revenue_acc"]: f"=C{BEU['revenue']}",
        BEU["roas"]: div_formula(f"C{BEU['revenue']}/C{BEU['media']}"),
        BEU["mc_month"]: f"=C{BEU['revenue']}*C{BEU['margin']}",
        BEU["mc_acc"]: f"=C{BEU['mc_month']}",
        BEU["cost_month"]: f"=C{BEU['cost_total']}",
        BEU["cost_acc"]: f"=C{BEU['cost_month']}",
        BEU["result_month"]: f"=C{BEU['mc_month']}-C{BEU['cost_month']}",
        BEU["result_acc"]: f"=ROUND(B{BEU['result_acc']}+C{BEU['result_month']},2)",
        BEU["roi_month"]: div_formula(f"C{BEU['mc_month']}/C{BEU['cost_month']}"),
        BEU["roi_project"]: div_formula(f"(B{BEU['mc_acc']}+C{BEU['mc_acc']})/(B{BEU['cost_acc']}+C{BEU['cost_acc']})"),
        BEU["future_revenue"]: "='Premissas'!F10",
    }
    for row, formula in aggregate_formulas.items():
        be.write_formula(beu_write_index(row), 2, formula, fmt_for(row), aggregate_values.get(row, 0))

    be.write_formula(
        beu_write_index(BEU["status"]),
        2,
        f'=IF(C{BEU["result_acc"]}>=-0.01,"Breakeven atingido","Revisar premissas")',
        status_ok,
        "Breakeven atingido",
    )

    be.conditional_format(
        f"B{BEU['result_month']}:{be_proj_last_name}{BEU['result_acc']}",
        {"type": "cell", "criteria": "<", "value": 0, "format": status_bad},
    )
    be.conditional_format(
        f"B{BEU['result_month']}:{be_proj_last_name}{BEU['result_acc']}",
        {"type": "cell", "criteria": ">=", "value": 0, "format": status_ok},
    )

    be.merge_range(
        f"A39:{be_proj_last_name}41",
        (
            "Funil completo e financeiro unificados. Taxas vêm das Premissas; volumes de trás para frente "
            f"a partir de vendas e faturamento alvo. Breakeven projetado: {minimum_breakeven_label}."
        ),
        note,
    )
    return be
