#!/usr/bin/env python3
# ÍNDICE DE SEÇÕES (para leitura cirúrgica por linha)
# Helpers / constantes ......... generate_breakeven_helpers.py  (arquivo separado)
# main() setup + formatos ...... L1009–L1924
# write_scenario_sheet() ....... L1925–L2988   (inner fn de main)
# Aba "Dados Fonte" ............ L2989–L3326
# Aba "Premissas" .............. L3327–L3806
# Aba "Breakeven 7M" ........... L3807–L4088
# Aba "Integrada" .............. L4088–L4384
# Aba "Funil Completo" ......... L4393–L4644
# Aba "Resumo Executivo" ....... L4645–L4841

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
    PROJECTION_END_YEAR,
    breakeven_month_from_rows,
    compute_financial_projections,
    projection_month_count,
    projection_month_headers,
)
from generate_breakeven_helpers import (
    MAX_PROJECTION_MONTHS,
    DEFAULT_SCENARIO_SHEET_ORDER,
    RATE_KEYS,
    MARKETPLACE_SCENARIO_HIDE_ROWS,
    MARKETPLACE_INTEGRATED_HIDE_ROWS,
    MARKETPLACE_STAGE_LABELS,
    MARKETPLACE_PREM_HIDE_ROWS,
    PREM_SCENARIO_ADVANCE_COL,
    PREM_FUNNEL_CONTROL_STAGES,
    PREM_MONTHLY_RATE_ROWS,
    INSIDE_SALES_INTEGRATED_SKIP_ROWS,
    INSIDE_SALES_INTEGRATED_SKIP_ROWS_LEAD_QUALI,
    INSIDE_SALES_SCENARIO_SKIP_ROWS,
    INSIDE_SALES_SCENARIO_SKIP_ROWS_LEAD_QUALI,
    INSIDE_SALES_INTEGRATED_RATE_ROWS,
    INSIDE_SALES_INTEGRATED_RATE_ROWS_LEAD_QUALI,
    INSIDE_SALES_SCENARIO_RATE_ROWS,
    INSIDE_SALES_SCENARIO_RATE_ROWS_LEAD_QUALI,
    INSIDE_SALES_BASELINE_VOLUME_ROWS,
    BEU,
    div_formula,
    extend_numeric_series,
    extend_scenario_config,
    months_until_breakeven,
    breakeven_month_label,
    full_funnel_rate_expr,
    inside_sales_lead_to_sale_expr,
    ecommerce_session_to_sale_expr,
    unified_final_conversion_expr,
    inside_sales_full_funnel_rate_expr,
    beu_row_labels,
    beu_write_index,
    build_minimum_funnel_cache,
    build_projection_rate_series,
    is_inside_sales_model,
    is_marketplace_model,
    has_lead_quali_funnel,
    projection_rules,
    cap_conversion_rate,
    prem_baseline_cell,
    prem_scenario_advance_cell,
    prem_realista_advance_cell,
    prem_ceiling_cell,
    rate_cap_term,
    compound_stage_rate_formula,
    compound_premissas_rate_formula,
    scenario_stage_by_sheet_row,
    integrated_funnel_row_labels,
    scenario_funnel_row_labels,
    breakeven_financial_row_labels,
    accumulated_funnel_from_benchmark,
    inside_sales_reference_cps,
    project_inside_sales_impressions,
    build_inside_sales_funnel_forward,
    build_inside_sales_funnel_volumes,
    inside_sales_funnel_rates,
    inside_sales_scenario_rate_values,
    inside_sales_scenario_volume_formulas,
    inside_sales_ltv_revenue_formula,
    inside_sales_forward_volume_formulas,
)


def _helpers_imported() -> bool:
    """Sentinela — confirma que generate_breakeven_helpers foi carregado."""
    return True


# (Helpers, constantes e row-label fns movidos para generate_breakeven_helpers.py)


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
    # Marketplace reusa todo o trilho Inside Sales (mesma estrutura/fórmulas/refs); só renomeia
    # as etapas visíveis e oculta as 2 taxas pass-through. Por isso is_inside_sales = True aqui.
    is_marketplace = is_marketplace_model(config_data.get("project_model", ""))
    is_inside_sales = is_inside_sales_model(config_data.get("project_model", "")) or is_marketplace
    has_lead_quali = has_lead_quali_funnel(config_data) and is_inside_sales and not is_marketplace
    # Rótulo da etapa extra de qualificação (entre Leads e MQL). Vem do GP de cada cliente —
    # pode ser "Lead quali", "Agendamento", "Reunião", etc. Default preserva o comportamento antigo.
    extra_stage_label = (config_data.get("extra_stage_label") or "Lead quali").strip() or "Lead quali"
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
    funnel_lt_period = config_data.get("funnel_lt_period") or config_data["lt_period"]

    if is_marketplace:
        current_funnel = [
            ("Impressões", current_sessions, None, None, "Base"),
            ("Cliques", current_view_item, current_view_item / current_sessions, bench_session_view, bench_label),
            ("Visitas", current_add_cart, current_add_cart / current_view_item, bench_view_add, bench_label),
            ("Compras", current_view_cart, current_view_cart / current_add_cart, bench_add_viewcart, bench_label),
            ("Compras (plataforma)", current_checkout, current_checkout / current_view_cart if current_view_cart else 0, bench_viewcart_checkout, bench_label),
            (
                "Compras faturadas",
                current_sales,
                current_sales / current_checkout if current_checkout else 0,
                bench_shipping_payment,
                bench_label,
            ),
        ]
    elif is_inside_sales:
        if has_lead_quali:
            current_funnel = [
                ("Impressões", current_sessions, None, None, "Base"),
                ("Cliques", current_view_item, current_view_item / current_sessions, bench_session_view, bench_label),
                ("Leads", current_add_cart, current_add_cart / current_view_item, bench_view_add, bench_label),
                (
                    extra_stage_label,
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
    accumulated_funnel = config_data.get("accumulated_funnel") or accumulated_funnel_from_benchmark(
        benchmark_months,
        media_total,
        has_lead_quali=has_lead_quali,
    )
    inside_sales_cps = inside_sales_reference_cps(
        current_month_media=current_month_media,
        current_sessions=current_sessions,
        accumulated_media=media_total,
        accumulated_sessions=sessions_total,
        min_cost_per_impression=min_cost_per_impression,
    )
    gp_cps_projection = [float(value) for value in (config_data.get("gp_cps_projection") or [])]

    def inside_sales_month_cps(month_idx: int) -> float:
        if gp_cps_projection and month_idx < len(gp_cps_projection):
            return gp_cps_projection[month_idx]
        return inside_sales_cps

    margin = config_data["margin"]
    monthly_fee = config_data["monthly_fee"]
    monthly_media = config_data["monthly_media"]
    current_cost = fee_total + media_total
    _hist_rec = int(config_data.get("tm_recurrence_months") or 1)
    _hist_tk = config_data.get("ticket_monthly") or (revenue_total / sales_total if sales_total else 0)
    if is_inside_sales and _hist_rec > 1 and sales_total:
        current_mc = sales_total * float(_hist_tk) * _hist_rec * margin
    else:
        current_mc = revenue_total * margin
    current_result = current_mc - current_cost
    current_ticket = revenue_total / sales_total if sales_total else 0
    ticket_monthly = config_data.get("ticket_monthly")
    if ticket_monthly is not None:
        ticket_monthly = float(ticket_monthly)
    else:
        ticket_monthly = current_ticket
    tm_recurrence_months = config_data.get("tm_recurrence_months") or 1
    projection_ticket = config_data.get("projection_ticket")
    if projection_ticket is not None:
        projection_ticket = float(projection_ticket)
    elif tm_recurrence_months and tm_recurrence_months > 1:
        projection_ticket = ticket_monthly * float(tm_recurrence_months)
    else:
        projection_ticket = ticket_monthly
    current_ticket = ticket_monthly
    ticket_hist_desc = "Faturamento GP mensal ÷ vendas (mediana histórica)"
    if config_data.get("tm_recurrence_months"):
        ticket_hist_desc = (
            f"Ticket GP mensal (mediana) — LTV = faturamento mensal × {tm_recurrence_months} "
            f"(≈ R$ {projection_ticket:,.2f}/venda na projeção)"
        )
    current_monthly_break_even = (monthly_fee + monthly_media) / margin

    minimum = config_data["minimum_scenario"]
    scenario_configs = config_data["scenarios"]
    scenario_sheet_order = tuple(
        config_data.get("scenario_sheet_order") or DEFAULT_SCENARIO_SHEET_ORDER
    )
    base_minimum_revenue = list(minimum["revenue"])
    if not base_minimum_revenue:
        raise ValueError("minimum_scenario.revenue não pode ser vazio.")
    base_minimum_media = list(minimum.get("media") or [])
    analysis_media_from_gp = bool(base_minimum_media)
    avg_projection_media = (
        sum(base_minimum_media) / len(base_minimum_media) if base_minimum_media else monthly_media
    )

    horizon_candidates = [
        months_until_breakeven(
            base_minimum_revenue,
            margin=margin,
            monthly_fee=monthly_fee,
            monthly_media=avg_projection_media,
            current_result=current_result,
        )
    ]
    for cfg in scenario_configs.values():
        cfg_media = cfg.get("media") or base_minimum_media
        cfg_avg_media = sum(cfg_media) / len(cfg_media) if cfg_media else monthly_media
        horizon_candidates.append(
            months_until_breakeven(
                cfg["revenue"],
                margin=margin,
                monthly_fee=monthly_fee,
                monthly_media=cfg_avg_media,
                current_result=current_result,
            )
        )
    projection_end_year = int(config_data.get("projection_end_year") or PROJECTION_END_YEAR)
    horizon_to_end = projection_month_count(reference_date, end_year=projection_end_year)
    if config_data.get("projection_end_year"):
        projection_months = min(MAX_PROJECTION_MONTHS, horizon_to_end)
    else:
        projection_months = min(MAX_PROJECTION_MONTHS, max(horizon_candidates))
    future_cost = projection_months * monthly_fee + (
        sum(extend_numeric_series(base_minimum_media, projection_months, key="media"))
        if base_minimum_media
        else projection_months * monthly_media
    )
    future_revenue_required = (
        (abs(current_result) + future_cost) / margin
        if current_result < 0
        else future_cost / margin
    )

    projected_revenue = extend_numeric_series(base_minimum_revenue, projection_months, key="revenue")
    projected_media = (
        extend_numeric_series(base_minimum_media, projection_months, key="media")
        if base_minimum_media
        else [monthly_media] * projection_months
    )
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
    lead_mql_rates: list[float] = []
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
        current_lead_mql = current_view_cart / current_add_cart if current_add_cart else 0
        current_mql_sql = current_checkout / current_view_cart if current_view_cart else 0
        current_sql_sale = current_sales / current_checkout if current_checkout else 0
        if current_sql_sale <= 0:
            baseline_sql_sale = (config_data.get("baseline_funnel_rates") or {}).get("sql_sale")
            if baseline_sql_sale:
                current_sql_sale = float(baseline_sql_sale)
        lead_mql_rates = build_projection_rate_series(
            minimum,
            "add_view_cart",
            current_lead_mql,
            projection_months,
            max_conversion_rate,
        )
        mql_sql_rates = build_projection_rate_series(
            minimum,
            "viewcart_checkout",
            current_mql_sql,
            projection_months,
            max_conversion_rate,
        )
        sql_sale_key = "sql_sale" if minimum.get("sql_sale") else "shipping_payment"
        sql_sale_rates = build_projection_rate_series(
            minimum,
            sql_sale_key,
            current_sql_sale,
            projection_months,
            max_conversion_rate,
        )
        lead_to_sale_rates = [
            cap_conversion_rate(
                lead_mql_rates[i] * mql_sql_rates[i] * sql_sale_rates[i],
                max_conversion_rate,
            )
            for i in range(projection_months)
        ]
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
    SCEN_COL_ACTUAL = 1
    SCEN_COL_PREV_MONTH = 2
    SCEN_COL_COMPETENCE = 3
    # Col C = último mês real · Col D = competência · Col E = mediana (ponto de partida)
    # Aplica a todos os modelos (IS, e-commerce, Marketplace).
    SCEN_COL_MEDIANA = 4
    SCEN_COL_TOTAL = 5
    SCEN_COL_SPACER = 6
    scen_proj_start_col = 7
    scen_proj_first_name = xlsxwriter.utility.xl_col_to_name(scen_proj_start_col)
    scen_comp_col_name = xlsxwriter.utility.xl_col_to_name(SCEN_COL_COMPETENCE)
    scen_prev_col_name = xlsxwriter.utility.xl_col_to_name(SCEN_COL_PREV_MONTH)
    scen_mediana_col_name = xlsxwriter.utility.xl_col_to_name(SCEN_COL_MEDIANA)
    scen_total_col_name = xlsxwriter.utility.xl_col_to_name(SCEN_COL_TOTAL)
    prev_funnel = config_data.get("previous_month_funnel") or config_data["current_funnel"]
    prev_month_label = config_data.get("previous_month_label") or "Mês anterior"
    # Col C = último mês fechado GP. Marketplace usa previous_month (builder injeta o mês real,
    # ex. Mai com ads pausada). IS/e-commerce: current_funnel já é o último fechado (Jun parcial
    # excluído) — EXCETO quando o último fechado tem 0 vendas e foi removido do funil completo;
    # nesse caso o builder marca col_c_use_previous_month e injeta previous_month_funnel real.
    if not is_marketplace and not config_data.get("col_c_use_previous_month"):
        prev_funnel = config_data["current_funnel"]
        prev_month_label = config_data.get("last_month_funnel_label") or prev_month_label
    # Quando Col C é o mês fechado REAL (col_c_use_previous_month), respeitar 0 de vendas/receita
    # — ex.: Mai/26 com ads pausada teve 0 vendas; o fallback `0 or current` mostraria as vendas
    # do mês anterior (Abr) e uma taxa SQL→Venda falsa. Só vale quando o builder injeta o mês real.
    _col_c_real = bool(config_data.get("col_c_use_previous_month"))
    prev_month_media = float(prev_funnel.get("media") or current_month_media)
    if _col_c_real:
        prev_month_sales = float(prev_funnel.get("sales") or 0)
        prev_month_revenue_gp = float(prev_funnel.get("revenue") or 0)
    else:
        prev_month_sales = float(prev_funnel.get("sales") or current_sales)
        prev_month_revenue_gp = float(prev_funnel.get("revenue") or current_month_revenue)
    recurrence_months = int(tm_recurrence_months or 1)
    if is_inside_sales and recurrence_months > 1:
        prev_month_ticket = (
            prev_month_revenue_gp / prev_month_sales if prev_month_sales else ticket_monthly
        )
        prev_month_revenue = prev_month_revenue_gp * recurrence_months
    else:
        prev_month_revenue = prev_month_revenue_gp
        prev_month_ticket = prev_month_revenue / prev_month_sales if prev_month_sales else ticket_monthly
    prev_month_cost = monthly_fee + prev_month_media
    prev_month_mc = prev_month_revenue * margin
    prev_month_result = prev_month_mc - prev_month_cost
    prev_month_sessions = float(prev_funnel.get("sessions") or current_sessions)
    prev_month_view_item = float(prev_funnel.get("view_item") or current_view_item)
    prev_month_add_cart = float(prev_funnel.get("add_to_cart") or current_add_cart)
    prev_month_view_cart = float(prev_funnel.get("view_cart") or current_view_cart)
    prev_month_checkout = float(prev_funnel.get("begin_checkout") or current_checkout)
    prev_month_shipping = float(prev_funnel.get("add_shipping_info") or prev_funnel.get("shipping") or prev_month_checkout)
    prev_month_payment = float(prev_funnel.get("add_payment_info") or prev_funnel.get("payment") or prev_month_shipping)
    prev_month_orders = float(prev_funnel.get("orders") or prev_month_add_cart)
    prem_proj_start_col = 5
    prem_proj_last_col = prem_proj_start_col + projection_months - 1
    prem_proj_last_name = xlsxwriter.utility.xl_col_to_name(prem_proj_last_col)
    funnel_proj_start_col = 7
    funnel_proj_last_col = funnel_proj_start_col + projection_months - 1
    funnel_proj_last_name = xlsxwriter.utility.xl_col_to_name(funnel_proj_last_col)
    month_headers = projection_month_headers(projection_months, reference_date)
    gp_media_projection_cfg = config_data.get("gp_media_projection") or []
    scenario_visible_months = projection_months
    scenario_sheet_headers = month_headers[:scenario_visible_months]
    scen_proj_last_col = scen_proj_start_col + scenario_visible_months - 1
    scen_proj_last_name = xlsxwriter.utility.xl_col_to_name(scen_proj_last_col)
    scen_sheet_last_col = scen_proj_last_col + 1
    scen_sheet_last_name = xlsxwriter.utility.xl_col_to_name(scen_sheet_last_col)
    leads_total = sum(row[3] for row in benchmark_months)
    funnel_conversion_label = (
        "Taxa de Conversão Leads → Vendas"
        if is_inside_sales
        else "Taxa de Conversão do Funil"
    )
    final_funnel_rate_label = (
        "Taxa final Visitas → Compras"
        if is_marketplace
        else "Taxa final Leads → Venda"
        if is_inside_sales
        else "Taxa final Sessão → Venda"
    )
    final_rate_volume_row = 20 if is_inside_sales else 16
    final_rate_integrated_row = 41 if is_inside_sales else 37

    projections = []
    minimum_financial = compute_financial_projections(
        revenue_series=projected_revenue,
        media_series=projected_media,
        ticket_series=None,
        monthly_fee=monthly_fee,
        base_monthly_media=monthly_media if not analysis_media_from_gp else projected_media[0],
        margin=margin,
        current_result=current_result,
        projection_months=projection_months,
        media_lever_after_monthly_breakeven=media_lever_after_breakeven and not analysis_media_from_gp,
        current_ticket=ticket_monthly,
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
        elif is_inside_sales:
            lead_mql = lead_mql_rates[idx]
            mql_sql = mql_sql_rates[idx]
            sql_sale = sql_sale_rates[idx]
            lead_rate = cap_conversion_rate(lead_mql * mql_sql * sql_sale, max_conversion_rate)
            final_conversion = view_rate * cart_rate * lead_rate
        else:
            lead_rate = cap_conversion_rate(lead_to_sale_rates[idx], max_conversion_rate)
            final_conversion = view_rate * cart_rate * lead_rate
        if is_inside_sales:
            sessions = project_inside_sales_impressions(effective_monthly_media, inside_sales_cps)
        else:
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
            current_ticket=ticket_monthly,
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
    elif is_inside_sales:
        minimum_full_rates = {
            "session_view": view_rates,
            "view_add": cart_rates,
            "add_view_cart": lead_mql_rates,
            "viewcart_checkout": mql_sql_rates,
            "checkout_shipping": realista["checkout_shipping"],
            "shipping_payment": sql_sale_rates,
            "payment_order": realista["payment_order"],
            "order_sale": approval_rates,
        }
    else:
        minimum_full_rates = {
            "session_view": view_rates,
            "view_add": cart_rates,
            "add_view_cart": extend_numeric_series(
                list(realista["add_view_cart"]), projection_months, key="add_view_cart"
            ),
            "viewcart_checkout": extend_numeric_series(
                list(realista["viewcart_checkout"]), projection_months, key="viewcart_checkout"
            ),
            "checkout_shipping": extend_numeric_series(
                list(realista["checkout_shipping"]), projection_months, key="checkout_shipping"
            ),
            "shipping_payment": extend_numeric_series(
                list(realista["shipping_payment"]), projection_months, key="shipping_payment"
            ),
            "payment_order": extend_numeric_series(
                list(realista["payment_order"]), projection_months, key="payment_order"
            ),
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
        ws.freeze_panes(2, scen_proj_start_col)
        ws.set_column("A:A", 38)
        ws.set_column("B:B", 24)
        ws.set_column("C:F", 19)  # C=último mês, D=competência, E=mediana, F=total projetado
        ws.set_column("G:G", 3)   # spacer
        ws.set_column(f"{scen_proj_first_name}:{scen_proj_last_name}", 15)
        ws.merge_range(f"A1:{scen_sheet_last_name}1", f"Breakeven {name} — {client}", title)
        baseline_funnel_volumes_cfg = config_data.get("baseline_funnel_volumes") or {}
        baseline_window_label = config_data.get("funnel_rate_baseline_label") or "mediana 3M"
        col_c_header = f"Funil {prev_month_label}\n(último mês GP)"
        _baseline_labels = config_data.get("projection_baseline_labels") or []
        _baseline_months_str = " · ".join(_baseline_labels) if _baseline_labels else baseline_window_label
        headers = [
            "",
            scenario_actual_column_label(config_data),
            col_c_header,
            "Alvo breakeven\n(baseline + meta R$)",
            f"Mediana 3M\n({_baseline_months_str})\nponto de partida",
            "Total projetado",
            "",
            *scenario_sheet_headers,
        ]
        ws.set_row(1, 32)
        for col, text in enumerate(headers):
            ws.write(1, col, text, header if col != SCEN_COL_SPACER else normal)

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

        prev_financial_values = {
            3: monthly_fee,
            4: prev_month_media,
            5: prev_month_cost,
            6: prev_month_revenue,
            7: prev_month_ticket,
            8: margin,
            9: prev_month_mc,
            10: prev_month_result,
            11: prev_month_result,
            12: prev_month_revenue / prev_month_media if prev_month_media else 0,
        }
        # Col C = dados reais do último mês — nunca sobrescrever com mediana.
        if is_inside_sales and recurrence_months > 1:
            prev_financial_formulas = {
                5: f"={scen_prev_col_name}3+{scen_prev_col_name}4",
                6: inside_sales_ltv_revenue_formula(scen_prev_col_name, recurrence_months),
                8: "='Premissas'!F7",
                9: f"={scen_prev_col_name}6*{scen_prev_col_name}8",
                10: f"={scen_prev_col_name}9-{scen_prev_col_name}5",
                11: f"={scen_prev_col_name}10",
                12: f"={scen_prev_col_name}6/{scen_prev_col_name}4",
            }
            for row_num, value in prev_financial_values.items():
                fmt = formula_percent if row_num == 8 else formula_number if row_num == 12 else formula_currency
                formula = prev_financial_formulas.get(row_num)
                if formula:
                    ws.write_formula(row_num - 1, SCEN_COL_PREV_MONTH, formula, fmt, value)
                else:
                    ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, fmt)
        else:
            for row_num, value in prev_financial_values.items():
                fmt = formula_percent if row_num == 8 else formula_number if row_num == 12 else formula_currency
                ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, fmt)
        ws.write(12, SCEN_COL_PREV_MONTH, prev_month_label, status_ok_small)

        # Coluna E = mediana 3M: ponto de partida das projeções (todos os modelos).
        # Col E = mediana 3M — ponto de partida das projeções.
        # Amarelo (input_percent) SOMENTE nas taxas de conversão; financeiros e volumes sem amarelo.
        if baseline_funnel_volumes_cfg:
            _bfv = baseline_funnel_volumes_cfg
            _base_sales = float(_bfv.get("sales") or _bfv.get("purchase") or 0)
            _rec = int(config_data.get("tm_recurrence_months") or 1)
            _base_revenue = _base_sales * ticket_monthly * (_rec if _rec > 1 else 1)
            _base_cost = monthly_fee + monthly_media
            _base_mc = _base_revenue * margin
            _comp_revenue = (monthly_fee + monthly_media) / margin if margin else 0
            mediana_financial = {
                3: monthly_fee,
                4: monthly_media,
                5: _base_cost,
                6: _base_revenue,
                7: ticket_monthly,
                8: margin,
                9: _base_mc,
                10: _base_mc - _base_cost,
                11: _base_mc - _base_cost,
                12: _base_revenue / monthly_media if monthly_media else 0,
            }
            for row_num, value in mediana_financial.items():
                fmt = formula_percent if row_num == 8 else formula_number if row_num == 12 else formula_currency
                ws.write_number(row_num - 1, SCEN_COL_MEDIANA, value, fmt)
            ws.write(12, SCEN_COL_MEDIANA, "PONTO DE PARTIDA", status_ok_small)
            # Taxas de conversão DERIVADAS dos volumes da própria coluna Mediana (=E18/E16, etc.).
            # Razão das medianas (não mediana das razões) faz o funil fechar exato: E16×E17=E18…
            # Antes a taxa vinha do mês corrente (idx=0) e não batia com os volumes medianos
            # (ex.: 180.129 imp × 2,41% ≠ 1.683). Premissas B28-B32 carregam a mesma razão derivada.
            if is_inside_sales:
                _bfv_imp = float(_bfv.get("impressions") or _bfv.get("sessions") or 0)
                _bfv_clk = float(_bfv.get("clicks") or _bfv.get("view_item") or 0)
                _bfv_led = float(_bfv.get("leads") or _bfv.get("add_to_cart") or 0)
                _bfv_mql = float(_bfv.get("mqls") or _bfv.get("view_cart") or _bfv_led)
                _bfv_sql = float(_bfv.get("sqls") or _bfv.get("add_to_cart") or 0)
                _bfv_sal = float(_bfv.get("sales") or _bfv.get("purchase") or 0)
                _vol_by_row = {16: _bfv_imp, 18: _bfv_clk, 20: _bfv_led, 22: _bfv_mql, 24: _bfv_sql, 32: _bfv_sal}
                if has_lead_quali:
                    _vol_by_row[26] = _bfv_sql
                    rate_vol_pairs = {17: (18, 16), 19: (20, 18), 21: (22, 20), 23: (24, 22), 25: (26, 24), 27: (32, 26)}
                else:
                    rate_vol_pairs = {17: (18, 16), 19: (20, 18), 21: (22, 20), 23: (24, 22), 25: (32, 24)}
                _med_col = scen_mediana_col_name
                for _rrow, (_nrow, _drow) in rate_vol_pairs.items():
                    _den = _vol_by_row.get(_drow, 0)
                    _cached = (_vol_by_row.get(_nrow, 0) / _den) if _den else 0
                    ws.write_formula(
                        _rrow - 1,
                        SCEN_COL_MEDIANA,
                        f"={_med_col}{_nrow}/{_med_col}{_drow}",
                        formula_percent,
                        _cached,
                    )
            else:
                # E-commerce D2C: taxas derivadas dos volumes exibidos na Col E (=E18/E16, etc.),
                # mesma lógica do IS. Antes vinham do mês corrente (config[...][0]) e não batiam
                # com os volumes medianos (ex.: dalpack E17 mostrava 100% com 5.307→4.223 = 79,6%).
                _ec_vol_by_row = {
                    16: float(_bfv.get("sessions") or _bfv.get("impressions") or 0),
                    18: float(_bfv.get("view_item") or _bfv.get("clicks") or 0),
                    20: float(_bfv.get("add_to_cart") or _bfv.get("leads") or 0),
                    22: float(_bfv.get("view_cart") or _bfv.get("mqls") or 0),
                    24: float(_bfv.get("begin_checkout") or _bfv.get("sqls") or 0),
                    26: float(_bfv.get("add_shipping_info") or _bfv.get("shipping") or 0),
                    28: float(_bfv.get("add_payment_info") or _bfv.get("payment") or 0),
                    30: float(_bfv.get("orders") or 0),
                    32: float(_bfv.get("purchase") or _bfv.get("sales") or 0),
                }
                _ec_rate_fallback = {
                    17: config["session_view"][0], 19: config["view_add"][0],
                    21: config["add_view_cart"][0], 23: config["viewcart_checkout"][0],
                    25: config["checkout_shipping"][0], 27: config["shipping_payment"][0],
                    29: config["payment_order"][0], 31: config["order_sale"][0],
                }
                _ec_rate_pairs = {17: (18, 16), 19: (20, 18), 21: (22, 20), 23: (24, 22),
                                  25: (26, 24), 27: (28, 26), 29: (30, 28), 31: (32, 30)}
                _med_col = scen_mediana_col_name
                for _rrow, (_nrow, _drow) in _ec_rate_pairs.items():
                    _den = _ec_vol_by_row.get(_drow, 0)
                    _num = _ec_vol_by_row.get(_nrow, 0)
                    # Só deriva se ambos os volumes existem; senão usa a taxa baseline (evita #DIV/0
                    # em micro-etapas GA4 ausentes em GPs simplificados).
                    if _den > 0 and _num > 0:
                        ws.write_formula(_rrow - 1, SCEN_COL_MEDIANA, f"={_med_col}{_nrow}/{_med_col}{_drow}", formula_percent, _num / _den)
                    else:
                        ws.write_number(_rrow - 1, SCEN_COL_MEDIANA, _ec_rate_fallback[_rrow], input_percent)
            # Volumes do funil (sem amarelo)
            _bfv_impressions = float(_bfv.get("impressions") or _bfv.get("sessions") or 0)
            _bfv_leads = float(_bfv.get("leads") or _bfv.get("add_to_cart") or 0)
            # E-commerce usa a chave begin_checkout (não sqls); sem reconhecê-la, o fallback caía
            # em add_to_cart e inflava o volume (ex.: dalpack begin_checkout 223 virava 919,
            # quebrando o funil: view_cart 309 → begin_checkout 919).
            _bfv_sqls = float(_bfv.get("sqls") or _bfv.get("begin_checkout") or _bfv.get("add_to_cart") or 0)
            mediana_vol_map = {
                16: _bfv_impressions,
                18: float(_bfv.get("clicks") or _bfv.get("view_item") or 0),
                20: _bfv_leads,
                22: float(_bfv.get("mqls") or _bfv.get("view_cart") or _bfv_leads),
                24: _bfv_sqls,
                32: _base_sales,
                33: _base_sales / _bfv_leads if _bfv_leads else 0,
                34: monthly_media / _bfv_impressions if _bfv_impressions else 0,
                35: monthly_media / (_bfv.get("orders") or _bfv_leads) if (_bfv.get("orders") or _bfv_leads) else 0,
                36: monthly_media / _base_sales if _base_sales else 0,
                37: _base_revenue,
                38: _base_revenue - _comp_revenue,
            }
            if has_lead_quali:
                mediana_vol_map[26] = _bfv_sqls
            # E-commerce D2C: micro-etapas GA4 (shipping/payment/orders) entre checkout e compra,
            # exibidas em linhas próprias — necessárias p/ as taxas derivadas (E26/E24, etc.) fecharem.
            if not is_inside_sales:
                for _r, _k in ((26, "add_shipping_info"), (28, "add_payment_info"), (30, "orders")):
                    _v = _bfv.get(_k)
                    if _v:
                        mediana_vol_map[_r] = float(_v)
            for row_num, value in mediana_vol_map.items():
                if row_num == 33:
                    ws.write_number(row_num - 1, SCEN_COL_MEDIANA, value, formula_percent)
                elif row_num in (34, 35, 36, 37, 38):
                    ws.write_number(row_num - 1, SCEN_COL_MEDIANA, value, formula_currency)
                else:
                    ws.write_number(row_num - 1, SCEN_COL_MEDIANA, value, formula_int)

        competence_revenue = (monthly_fee + monthly_media) / margin
        competence_ticket = ticket_monthly
        competence_financial = {
            3: monthly_fee,
            4: monthly_media,
            5: monthly_fee + monthly_media,
            6: competence_revenue,
            7: competence_ticket,
            8: margin,
            9: competence_revenue * margin,
            10: 0,
            11: 0,
            12: competence_revenue / monthly_media if monthly_media else 0,
        }
        competence_formulas = {
            3: "='Premissas'!F4",
            4: "='Premissas'!F5",
            5: f"={scen_comp_col_name}3+{scen_comp_col_name}4",
            6: f"={scen_comp_col_name}5/{scen_comp_col_name}8",
            7: "=B7",
            8: "='Premissas'!F7",
            9: f"={scen_comp_col_name}6*{scen_comp_col_name}8",
            10: f"={scen_comp_col_name}9-{scen_comp_col_name}5",
            11: f"={scen_comp_col_name}10",
            12: f"={scen_comp_col_name}6/{scen_comp_col_name}4",
        }
        for row_num, value in competence_financial.items():
            fmt = formula_percent if row_num == 8 else formula_number if row_num == 12 else formula_currency
            ws.write_formula(row_num - 1, SCEN_COL_COMPETENCE, competence_formulas[row_num], fmt, value)
        ws.write(12, SCEN_COL_COMPETENCE, "ZERA A COMPETÊNCIA", status_ok_small)

        financial_plan = scenario_financial_plans[name]
        cached_months = []
        for idx in range(scenario_visible_months):
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
                month_cps = inside_sales_month_cps(idx)
                baseline_volumes = config_data.get("baseline_funnel_volumes")
                funnel_volumes = build_inside_sales_funnel_forward(
                    media,
                    month_cps,
                    inside_sales_funnel_rates(config, idx, has_lead_quali),
                    has_lead_quali=has_lead_quali,
                    baseline_volumes=baseline_volumes,
                    month_idx=idx,
                )
                sales = funnel_volumes["sales"]
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
            if is_inside_sales and recurrence_months > 1:
                revenue = sales * ticket_monthly * recurrence_months
                ticket = ticket_monthly
                mc = revenue * margin
                result = mc - cost
                cumulative = (
                    round(current_result + result, 2)
                    if idx == 0
                    else round(cached_months[idx - 1]["cumulative"] + result, 2)
                )
                roas = revenue / media if media else 0
            else:
                roas = fin["roas"]
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
                    "roas": roas,
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
            col = scen_proj_start_col + idx
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
                6: (
                    inside_sales_ltv_revenue_formula(col_name, recurrence_months)
                    if is_inside_sales and recurrence_months > 1
                    else (f"={col_name}37" if is_inside_sales else None)
                ),
                7: "=B7" if is_inside_sales and recurrence_months > 1 else None,
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

        visible_months = cached_months
        if is_inside_sales and recurrence_months > 1:
            total_revenue = sum(
                month["sales"] * ticket_monthly * recurrence_months for month in visible_months
            )
            total_ticket = ticket_monthly
        else:
            total_revenue = sum(fin["revenue"] for fin in financial_plan[:scenario_visible_months])
            total_ticket = (
                total_revenue / sum(x["sales"] for x in visible_months)
                if visible_months and sum(x["sales"] for x in visible_months)
                else ticket_monthly
            )
        total_financial = {
            3: scenario_visible_months * monthly_fee,
            4: sum(fin["media"] for fin in financial_plan[:scenario_visible_months]),
            5: scenario_visible_months * monthly_fee + sum(
                fin["media"] for fin in financial_plan[:scenario_visible_months]
            ),
            6: total_revenue,
            7: total_ticket,
            8: margin,
            9: total_revenue * margin,
            10: total_revenue * margin
            - (
                scenario_visible_months * monthly_fee
                + sum(fin["media"] for fin in financial_plan[:scenario_visible_months])
            ),
            11: visible_months[-1]["cumulative"] if visible_months else 0,
            12: total_revenue / sum(fin["media"] for fin in financial_plan[:scenario_visible_months])
            if sum(fin["media"] for fin in financial_plan[:scenario_visible_months])
            else 0,
        }
        total_formulas = {
            3: f"=SUM({scen_proj_first_name}3:{scen_proj_last_name}3)",
            4: f"=SUM({scen_proj_first_name}4:{scen_proj_last_name}4)",
            5: f"=SUM({scen_proj_first_name}5:{scen_proj_last_name}5)",
            6: f"=SUM({scen_proj_first_name}6:{scen_proj_last_name}6)",
            7: "=B7" if is_inside_sales and recurrence_months > 1 else f"={scen_total_col_name}6/{scen_total_col_name}32",
            8: "='Premissas'!F7",
            9: f"={scen_total_col_name}6*{scen_total_col_name}8",
            10: f"={scen_total_col_name}9-{scen_total_col_name}5",
            11: f"={scen_proj_last_name}11",
            12: f"={scen_total_col_name}6/{scen_total_col_name}4",
        }
        for row_num, value in total_financial.items():
            fmt = formula_percent if row_num == 8 else formula_number if row_num == 12 else formula_currency
            ws.write_formula(row_num - 1, SCEN_COL_TOTAL, total_formulas[row_num], fmt, value)
        final_cumulative = visible_months[-1]["cumulative"] if visible_months else 0
        ws.write_formula(
            12,
            SCEN_COL_TOTAL,
            f'=IF({scen_total_col_name}11>=0,"BREAKEVEN ATINGIDO","NÃO BREAKEVA")',
            status_ok_small if final_cumulative >= 0 else status_bad_small,
            "BREAKEVEN ATINGIDO" if final_cumulative >= 0 else "NÃO BREAKEVA",
        )

        ws.merge_range(f"A15:{scen_sheet_last_name}15", "Funil completo mês a mês", section)
        funnel_rows = scenario_funnel_row_labels(
            is_inside_sales, final_funnel_rate_label, has_lead_quali, extra_stage_label, is_marketplace
        )
        if is_marketplace:
            for _hidden_row in MARKETPLACE_SCENARIO_HIDE_ROWS:
                ws.set_row(_hidden_row - 1, None, None, {"hidden": True})
        for row_num, text in funnel_rows.items():
            ws.write(row_num - 1, 0, text, label)

        if is_inside_sales:
            acc = accumulated_funnel
            if has_lead_quali:
                actual_rates = {
                    17: acc["clicks"] / acc["impressions"] if acc["impressions"] else 0,
                    19: acc["leads"] / acc["clicks"] if acc["clicks"] else 0,
                    21: min(
                        max_conversion_rate,
                        acc["lead_quali"] / acc["leads"] if acc["leads"] else 0,
                    ),
                    23: acc["mqls"] / acc["lead_quali"] if acc["lead_quali"] else 0,
                    25: acc["sqls"] / acc["mqls"] if acc["mqls"] else 0,
                    27: acc["sales"] / acc["sqls"] if acc["sqls"] else 0,
                }
                actual_volumes = {
                    16: acc["impressions"],
                    18: acc["clicks"],
                    20: acc["leads"],
                    22: acc["lead_quali"],
                    24: acc["mqls"],
                    26: acc["sqls"],
                    32: acc["sales"],
                    33: acc["sales"] / acc["leads"] if acc["leads"] else 0,
                    34: media_total / acc["impressions"] if acc["impressions"] else 0,
                    35: media_total / acc["sqls"] if acc["sqls"] else 0,
                    36: media_total / acc["sales"] if acc["sales"] else 0,
                    37: revenue_total,
                    38: 0,
                }
            else:
                actual_rates = {
                    17: acc["clicks"] / acc["impressions"] if acc["impressions"] else 0,
                    19: acc["leads"] / acc["clicks"] if acc["clicks"] else 0,
                    21: min(max_conversion_rate, acc["mqls"] / acc["leads"] if acc["leads"] else 0),
                    23: acc["sqls"] / acc["mqls"] if acc["mqls"] else 0,
                    25: acc["sales"] / acc["sqls"] if acc["sqls"] else 0,
                }
                actual_volumes = {
                    16: acc["impressions"],
                    18: acc["clicks"],
                    20: acc["leads"],
                    22: acc["mqls"],
                    24: acc["sqls"],
                    32: acc["sales"],
                    33: acc["sales"] / acc["leads"] if acc["leads"] else 0,
                    34: media_total / acc["impressions"] if acc["impressions"] else 0,
                    35: media_total / acc["sqls"] if acc["sqls"] else 0,
                    36: media_total / acc["sales"] if acc["sales"] else 0,
                    37: (
                        acc["sales"] * ticket_monthly * recurrence_months
                        if recurrence_months > 1
                        else revenue_total
                    ),
                    38: (
                        acc["sales"] * ticket_monthly * recurrence_months - revenue_total
                        if recurrence_months > 1
                        else 0
                    ),
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

        if is_inside_sales:
            use_prem_funnel_controls = bool(config_data.get("scenario_stage_monthly_advance"))
            baseline_funnel_rates = config_data.get("baseline_funnel_rates") or {}
            # Col C = dados reais do último mês (não mediana). Taxas sem amarelo.
            if baseline_funnel_volumes_cfg:
                prev_rate_values_c = {
                    17: prev_month_view_item / prev_month_sessions if prev_month_sessions else 0,
                    19: prev_month_add_cart / prev_month_view_item if prev_month_view_item else 0,
                    21: min(
                        max_conversion_rate,
                        prev_month_view_cart / prev_month_add_cart if prev_month_add_cart else 0,
                    ),
                    23: prev_month_checkout / prev_month_view_cart if prev_month_view_cart else 0,
                    25: prev_month_sales / prev_month_checkout if prev_month_checkout else 0,
                }
                for row_num, value in prev_rate_values_c.items():
                    ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_percent)
                prev_volume_values = {
                    16: prev_month_sessions,
                    18: prev_month_view_item,
                    20: prev_month_add_cart,
                    22: prev_month_view_cart,
                    24: prev_month_checkout,
                    32: prev_month_sales,
                    33: prev_month_sales / prev_month_add_cart if prev_month_add_cart else 0,
                    34: prev_month_media / prev_month_sessions if prev_month_sessions else 0,
                    35: prev_month_media / prev_month_checkout if prev_month_checkout else 0,
                    36: prev_month_media / prev_month_sales if prev_month_sales else 0,
                    37: prev_month_revenue,
                    38: 0,
                }
                if has_lead_quali:
                    prev_volume_values[26] = prev_month_checkout
                for row_num, value in prev_volume_values.items():
                    if row_num == 33:
                        ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_percent)
                    elif row_num in (34, 35, 36, 37, 38):
                        ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_currency)
                    else:
                        ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_int)
            elif use_prem_funnel_controls:
                for key, sheet_row, baseline_row, _advance_row, _label in PREM_FUNNEL_CONTROL_STAGES:
                    ws.write_formula(
                        sheet_row - 1,
                        SCEN_COL_PREV_MONTH,
                        f"={prem_baseline_cell(baseline_row)}",
                        input_percent,
                        baseline_funnel_rates.get(key, 0),
                    )
            else:
                comp_rates = inside_sales_scenario_rate_values(config, 0, has_lead_quali)
                for row_num, value in comp_rates.items():
                    ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, input_percent)
                prev_rate_values = {
                    17: prev_month_view_item / prev_month_sessions if prev_month_sessions else 0,
                    19: prev_month_add_cart / prev_month_view_item if prev_month_view_item else 0,
                    21: min(
                        max_conversion_rate,
                        prev_month_view_cart / prev_month_add_cart if prev_month_add_cart else 0,
                    ),
                    23: prev_month_checkout / prev_month_view_cart if prev_month_view_cart else 0,
                    25: prev_month_sales / prev_month_checkout if prev_month_checkout else 0,
                }
                for row_num, value in prev_rate_values.items():
                    ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_percent)
                prev_volume_values = {
                    16: prev_month_sessions,
                    18: prev_month_view_item,
                    20: prev_month_add_cart,
                    22: prev_month_view_cart,
                    24: prev_month_checkout,
                    32: prev_month_sales,
                    33: prev_month_sales / prev_month_add_cart if prev_month_add_cart else 0,
                    34: prev_month_media / prev_month_sessions if prev_month_sessions else 0,
                    35: prev_month_media / prev_month_checkout if prev_month_checkout else 0,
                    36: prev_month_media / prev_month_sales if prev_month_sales else 0,
                    37: prev_month_revenue,
                    38: 0,
                }
                for row_num, value in prev_volume_values.items():
                    if row_num == 37 and recurrence_months > 1:
                        ws.write_formula(
                            row_num - 1,
                            SCEN_COL_PREV_MONTH,
                            f"={scen_prev_col_name}6",
                            formula_currency,
                            value,
                        )
                        continue
                    if row_num == 33:
                        ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_percent)
                    elif row_num in (34, 35, 36, 37, 38):
                        ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_currency)
                    else:
                        ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_int)
        elif not is_marketplace:
            # E-commerce D2C — col C = funil real do último mês GP
            prev_rate_values_c = {
                17: prev_month_view_item / prev_month_sessions if prev_month_sessions else 0,
                19: prev_month_add_cart / prev_month_view_item if prev_month_view_item else 0,
                21: min(
                    max_conversion_rate,
                    prev_month_view_cart / prev_month_add_cart if prev_month_add_cart else 0,
                ),
                23: prev_month_checkout / prev_month_view_cart if prev_month_view_cart else 0,
                25: prev_month_sales / prev_month_checkout if prev_month_checkout else 0,
                27: prev_month_payment / prev_month_shipping if prev_month_shipping else 0,
                29: prev_month_orders / prev_month_payment if prev_month_payment else 0,
                31: prev_month_sales / prev_month_orders if prev_month_orders else 0,
            }
            for row_num, value in prev_rate_values_c.items():
                ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_percent)
            prev_volume_values = {
                16: prev_month_sessions,
                18: prev_month_view_item,
                20: prev_month_add_cart,
                22: prev_month_view_cart,
                24: prev_month_checkout,
                26: prev_month_shipping,
                28: prev_month_payment,
                30: prev_month_orders,
                32: prev_month_sales,
                33: prev_month_sales / prev_month_sessions if prev_month_sessions else 0,
                34: prev_month_media / prev_month_sessions if prev_month_sessions else 0,
                35: prev_month_media / prev_month_orders if prev_month_orders else 0,
                36: prev_month_media / prev_month_sales if prev_month_sales else 0,
                37: prev_month_revenue,
                38: 0,
            }
            for row_num, value in prev_volume_values.items():
                if row_num == 33:
                    ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_percent)
                elif row_num in (34, 35, 36, 37, 38):
                    ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_currency)
                else:
                    ws.write_number(row_num - 1, SCEN_COL_PREV_MONTH, value, formula_int)
        if not is_inside_sales and not is_marketplace:
            competence_sales = competence_revenue / competence_ticket
            competence_orders = competence_sales / config["order_sale"][0]
            competence_payment = competence_orders / config["payment_order"][0]
            competence_shipping = competence_payment / config["shipping_payment"][0]
            competence_checkout = competence_shipping / config["checkout_shipping"][0]
            competence_view_cart = competence_checkout / config["viewcart_checkout"][0]
            competence_add_cart = competence_view_cart / config["add_view_cart"][0]
            competence_view_item = competence_add_cart / config["view_add"][0]
            competence_sessions = competence_view_item / config["session_view"][0]
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
        if is_inside_sales:
            use_prem_funnel_controls = bool(config_data.get("scenario_stage_monthly_advance"))
            baseline_funnel_rates = config_data.get("baseline_funnel_rates") or {}
            if use_prem_funnel_controls:
                for key, sheet_row, baseline_row, _advance_row, _label in PREM_FUNNEL_CONTROL_STAGES:
                    ws.write_formula(
                        sheet_row - 1,
                        SCEN_COL_COMPETENCE,
                        f"={prem_baseline_cell(baseline_row)}",
                        formula_percent,
                        baseline_funnel_rates.get(key, 0),
                    )
            else:
                comp_rates = inside_sales_scenario_rate_values(config, 0, has_lead_quali)
                for row_num, value in comp_rates.items():
                    ws.write_number(row_num - 1, SCEN_COL_COMPETENCE, value, formula_percent)
            recurrence = int(config_data.get("tm_recurrence_months") or 1)
            comp_ticket_value = ticket_monthly * recurrence if recurrence > 1 else ticket_monthly
            comp_sales_needed = competence_revenue / comp_ticket_value if comp_ticket_value else 0
            baseline_volumes = config_data.get("baseline_funnel_volumes") or {}
            if baseline_volumes:
                # Funil inverso: volumes calculados a partir das vendas necessárias para zerar
                # a competência, usando as taxas da mediana. Volumes diferentes da col E.
                comp_funnel_rates = inside_sales_funnel_rates(config, 0, has_lead_quali)
                comp_volumes_inv = build_inside_sales_funnel_volumes(
                    comp_sales_needed, comp_funnel_rates, has_lead_quali=has_lead_quali
                )
                comp_volume_values = {
                    16: comp_volumes_inv["sessions"],
                    18: comp_volumes_inv["view_item"],
                    20: comp_volumes_inv["add_cart"],
                    22: comp_volumes_inv["view_cart"],
                    24: comp_volumes_inv.get("begin_checkout", comp_volumes_inv["checkout"]),
                    32: comp_sales_needed,
                    33: comp_sales_needed / comp_volumes_inv["add_cart"] if comp_volumes_inv["add_cart"] else 0,
                    34: inside_sales_cps,
                    35: monthly_media / comp_volumes_inv["checkout"] if comp_volumes_inv["checkout"] else 0,
                    36: monthly_media / comp_sales_needed if comp_sales_needed else 0,
                    37: competence_revenue,
                    38: 0,
                }
                comp_volume_formulas = {
                    32: (
                        f"={scen_comp_col_name}6/({scen_comp_col_name}7*{recurrence})"
                        if recurrence > 1
                        else f"={scen_comp_col_name}6/{scen_comp_col_name}7"
                    ),
                    24: f"={scen_comp_col_name}32/{scen_comp_col_name}25",
                    22: f"={scen_comp_col_name}24/{scen_comp_col_name}23",
                    20: f"={scen_comp_col_name}22/{scen_comp_col_name}21",
                    18: f"={scen_comp_col_name}20/{scen_comp_col_name}19",
                    16: f"={scen_comp_col_name}18/{scen_comp_col_name}17",
                    33: f"={scen_comp_col_name}32/{scen_comp_col_name}{final_rate_volume_row}",
                    34: "=B34",
                    35: f"={scen_comp_col_name}4/{scen_comp_col_name}24",
                    36: f"={scen_comp_col_name}4/{scen_comp_col_name}32",
                    37: f"={scen_comp_col_name}6",
                    38: "=0",
                }
            else:
                comp_funnel_rates = inside_sales_funnel_rates(config, 0, has_lead_quali)
                comp_volumes = build_inside_sales_funnel_volumes(
                    comp_sales_needed,
                    comp_funnel_rates,
                    has_lead_quali=has_lead_quali,
                )
                comp_volume_values = {
                    16: comp_volumes["sessions"],
                    18: comp_volumes["view_item"],
                    20: comp_volumes["add_cart"],
                    22: comp_volumes["view_cart"],
                    24: comp_volumes.get("begin_checkout", comp_volumes["checkout"]),
                    32: comp_sales_needed,
                    33: comp_sales_needed / comp_volumes["add_cart"] if comp_volumes["add_cart"] else 0,
                    34: inside_sales_cps,
                    35: monthly_media / comp_volumes["checkout"] if comp_volumes["checkout"] else 0,
                    36: monthly_media / comp_sales_needed if comp_sales_needed else 0,
                    37: competence_revenue,
                    38: 0,
                }
                comp_volume_formulas = {
                    32: (
                        f"={scen_comp_col_name}6/({scen_comp_col_name}7*{recurrence})"
                        if recurrence > 1
                        else f"={scen_comp_col_name}6/{scen_comp_col_name}7"
                    ),
                    24: f"={scen_comp_col_name}32/{scen_comp_col_name}25",
                    22: f"={scen_comp_col_name}24/{scen_comp_col_name}23",
                    20: f"={scen_comp_col_name}22/{scen_comp_col_name}21",
                    18: f"={scen_comp_col_name}20/{scen_comp_col_name}19",
                    16: f"={scen_comp_col_name}18/{scen_comp_col_name}17",
                    33: f"={scen_comp_col_name}32/{scen_comp_col_name}{final_rate_volume_row}",
                    34: "=B34",
                    35: f"={scen_comp_col_name}4/{scen_comp_col_name}24",
                    36: f"={scen_comp_col_name}4/{scen_comp_col_name}32",
                    37: f"={scen_comp_col_name}6",
                    38: "=0",
                }
            if has_lead_quali:
                if baseline_volumes:
                    comp_volume_values[26] = baseline_volumes["sqls"]
                    comp_volume_formulas[26] = f"=${scen_mediana_col_name}$26"
                else:
                    comp_volume_values[26] = comp_volumes["checkout"]
                    comp_volume_formulas[26] = f"={scen_comp_col_name}32/{scen_comp_col_name}27"
            for row_num, formula in comp_volume_formulas.items():
                fmt = formula_percent if row_num == 33 else formula_currency if row_num in (34, 35, 36, 37, 38) else formula_int
                ws.write_formula(row_num - 1, SCEN_COL_COMPETENCE, formula, fmt, comp_volume_values[row_num])
        else:
            for row_num, value in competence_rate_values.items():
                ws.write_formula(row_num - 1, SCEN_COL_COMPETENCE, f"={scen_proj_first_name}{row_num}", formula_percent, value)
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
                32: f"={scen_comp_col_name}6/{scen_comp_col_name}7",
                30: f"={scen_comp_col_name}32/{scen_comp_col_name}31",
                28: f"={scen_comp_col_name}30/{scen_comp_col_name}29",
                26: f"={scen_comp_col_name}28/{scen_comp_col_name}27",
                24: f"={scen_comp_col_name}26/{scen_comp_col_name}25",
                22: f"={scen_comp_col_name}24/{scen_comp_col_name}23",
                20: f"={scen_comp_col_name}22/{scen_comp_col_name}21",
                18: f"={scen_comp_col_name}20/{scen_comp_col_name}19",
                16: f"={scen_comp_col_name}18/{scen_comp_col_name}17",
                33: f"={scen_comp_col_name}32/{scen_comp_col_name}{final_rate_volume_row}",
                34: f"={scen_comp_col_name}4/{scen_comp_col_name}16",
                35: f"={scen_comp_col_name}4/{scen_comp_col_name}30",
                36: f"={scen_comp_col_name}4/{scen_comp_col_name}32",
                37: f"={scen_comp_col_name}32*{scen_comp_col_name}7",
                38: "=0",
            }
            for row_num, formula in competence_volume_formulas.items():
                fmt = formula_percent if row_num == 33 else formula_currency if row_num in (34, 35, 36, 37, 38) else formula_int
                ws.write_formula(row_num - 1, SCEN_COL_COMPETENCE, formula, fmt, competence_volume_values[row_num])

        baseline_volumes = config_data.get("baseline_funnel_volumes")
        for idx, cached in enumerate(cached_months):
            col = scen_proj_start_col + idx
            col_name = xlsxwriter.utility.xl_col_to_name(col)
            # Coluna anterior recalculada por iteração: sem isso, o valor ficava preso
            # na última coluna do loop acima (BG), fazendo as taxas M2+ referenciarem BG
            # e gerando dependência circular (#REF!) ao recalcular no Google Sheets.
            previous_col = xlsxwriter.utility.xl_col_to_name(col - 1)
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
                if (
                    is_inside_sales
                    and config_data.get("scenario_stage_monthly_advance")
                    and row_num in INSIDE_SALES_SCENARIO_RATE_ROWS
                ):
                    stage = scenario_stage_by_sheet_row()[row_num]
                    _key, sheet_row, baseline_row, advance_row, _label = stage
                    rate_formula = compound_stage_rate_formula(
                        scenario_name=name,
                        sheet_row=sheet_row,
                        baseline_excel_row=baseline_row,
                        advance_excel_row=advance_row,
                        prev_col_name=previous_col if idx > 0 else None,
                        month_idx=idx,
                        max_rate=max_conversion_rate,
                        use_stage_ceilings=bool(config_data.get("stage_rate_ceilings")),
                    )
                    ws.write_formula(row_num - 1, col, rate_formula, input_percent, value)
                else:
                    ws.write_number(row_num - 1, col, value, input_percent)
            if is_inside_sales:
                ltv_revenue = cached["sales"] * ticket_monthly * recurrence_months
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
                    37: ltv_revenue if recurrence_months > 1 else cached["sales"] * cached["ticket"],
                    38: 0,
                }
                if has_lead_quali:
                    volume_values[26] = cached["checkout"]
                    volume_values[35] = cached["media"] / cached["checkout"] if cached["checkout"] else 0
                else:
                    volume_values[35] = cached["media"] / cached["checkout"] if cached["checkout"] else 0
                baseline_volumes = config_data.get("baseline_funnel_volumes")
                baseline_imp_cell = f"${scen_mediana_col_name}$16" if baseline_volumes else None
                proj_cps_anchor = f"${scen_mediana_col_name}$34"
                volume_formulas = inside_sales_forward_volume_formulas(
                    col_name,
                    has_lead_quali=has_lead_quali,
                    final_rate_volume_row=final_rate_volume_row,
                    tm_recurrence_months=int(config_data.get("tm_recurrence_months") or 1),
                    reference_cps_cell=proj_cps_anchor,
                    baseline_impressions_cell=baseline_imp_cell,
                )
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
                    38: "=0",
                }
            for row_num, formula in volume_formulas.items():
                fmt = formula_percent if row_num == 33 else formula_currency if row_num in (34, 35, 36, 37, 38) else formula_int
                if (
                    is_inside_sales
                    and baseline_volumes
                    and idx == 0
                    and row_num in INSIDE_SALES_BASELINE_VOLUME_ROWS
                ):
                    ws.write_formula(
                        row_num - 1,
                        col,
                        f"=${scen_mediana_col_name}${row_num}",
                        fmt,
                        volume_values[row_num],
                    )
                elif (
                    is_inside_sales
                    and baseline_volumes
                    and idx == 0
                    and has_lead_quali
                    and row_num == 26
                ):
                    ws.write_formula(
                        row_num - 1,
                        col,
                        f"=${scen_mediana_col_name}$26",
                        fmt,
                        volume_values[row_num],
                    )
                elif (
                    not is_inside_sales
                    and baseline_volumes
                    and idx == 0
                    and row_num in (16, 18, 20, 32)
                ):
                    ws.write_formula(
                        row_num - 1,
                        col,
                        f"=${scen_mediana_col_name}${row_num}",
                        fmt,
                        volume_values[row_num],
                    )
                else:
                    ws.write_formula(row_num - 1, col, formula, fmt, volume_values[row_num])
            if is_inside_sales and idx == 0:
                # G34 = CPS mediano 3M (referência Flow÷CPI). Impressões da projeção ancoram na mediana (G16).
                ws.write_number(33, col, inside_sales_month_cps(0), input_currency)

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
                    17: f"={scen_total_col_name}18/{scen_total_col_name}16",
                    19: f"={scen_total_col_name}20/{scen_total_col_name}18",
                    21: f"={scen_total_col_name}22/{scen_total_col_name}20",
                    23: f"={scen_total_col_name}24/{scen_total_col_name}22",
                    25: f"={scen_total_col_name}26/{scen_total_col_name}24",
                    27: f"={scen_total_col_name}32/{scen_total_col_name}26",
                    33: f"={scen_total_col_name}32/{scen_total_col_name}{final_rate_volume_row}",
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
                    17: f"={scen_total_col_name}18/{scen_total_col_name}16",
                    19: f"={scen_total_col_name}20/{scen_total_col_name}18",
                    21: f"={scen_total_col_name}22/{scen_total_col_name}20",
                    23: f"={scen_total_col_name}24/{scen_total_col_name}22",
                    25: f"={scen_total_col_name}32/{scen_total_col_name}24",
                    33: f"={scen_total_col_name}32/{scen_total_col_name}{final_rate_volume_row}",
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
                17: f"={scen_total_col_name}18/{scen_total_col_name}16",
                19: f"={scen_total_col_name}20/{scen_total_col_name}18",
                21: f"={scen_total_col_name}22/{scen_total_col_name}20",
                23: f"={scen_total_col_name}24/{scen_total_col_name}22",
                25: f"={scen_total_col_name}26/{scen_total_col_name}24",
                27: f"={scen_total_col_name}28/{scen_total_col_name}26",
                29: f"={scen_total_col_name}30/{scen_total_col_name}28",
                31: f"={scen_total_col_name}32/{scen_total_col_name}30",
                33: f"={scen_total_col_name}32/{scen_total_col_name}{final_rate_volume_row}",
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
            ws.write_formula(
                row_num - 1,
                SCEN_COL_TOTAL,
                f"=SUM({scen_proj_first_name}{row_num}:{scen_proj_last_name}{row_num})",
                formula_int,
                value,
            )
        for row_num, formula in aggregate_rate_formulas.items():
            if row_num == 33:
                cached_value = aggregate_funnel[32] / aggregate_funnel[final_rate_volume_row]
            else:
                numerator, denominator = aggregate_rate_pairs[row_num]
                cached_value = aggregate_funnel[numerator] / aggregate_funnel[denominator]
            ws.write_formula(row_num - 1, SCEN_COL_TOTAL, formula, formula_percent, cached_value)
        ws.write_formula(
            33,
            SCEN_COL_TOTAL,
            f"={scen_total_col_name}4/{scen_total_col_name}16",
            formula_currency,
            total_financial[4] / aggregate_funnel[16],
        )
        if is_inside_sales:
            sql_row = 26 if has_lead_quali else 24
            ws.write_formula(
                34,
                SCEN_COL_TOTAL,
                f"={scen_total_col_name}4/{scen_total_col_name}{sql_row}",
                formula_currency,
                total_financial[4] / aggregate_funnel[sql_row],
            )
        else:
            ws.write_formula(
                34,
                SCEN_COL_TOTAL,
                f"={scen_total_col_name}4/{scen_total_col_name}30",
                formula_currency,
                total_financial[4] / aggregate_funnel[30],
            )
        ws.write_formula(
            35,
            SCEN_COL_TOTAL,
            f"={scen_total_col_name}4/{scen_total_col_name}32",
            formula_currency,
            total_financial[4] / aggregate_funnel[32],
        )
        total_funnel_revenue_formula = (
            inside_sales_ltv_revenue_formula(scen_total_col_name, recurrence_months)
            if is_inside_sales and recurrence_months > 1
            else f"={scen_total_col_name}32*{scen_total_col_name}7"
        )
        ws.write_formula(
            36,
            SCEN_COL_TOTAL,
            total_funnel_revenue_formula,
            formula_currency,
            total_financial[6],
        )
        ws.write_formula(
            37,
            SCEN_COL_TOTAL,
            "=0",
            formula_currency,
            0,
        )

        ws.conditional_format(
            f"{scen_proj_first_name}11:{scen_proj_last_name}11",
            {"type": "cell", "criteria": "<", "value": 0, "format": status_bad},
        )
        ws.conditional_format(
            f"{scen_proj_first_name}11:{scen_proj_last_name}11",
            {"type": "cell", "criteria": ">=", "value": 0, "format": status_ok},
        )
        # Status (linha 13): a COR deve seguir o resultado acumulado (linha 11) AO VIVO, não o
        # cache da geração. Sem isto, "EM RECUPERAÇÃO" podia aparecer em verde (cor estática do
        # cache divergindo do texto, que é fórmula). Vale para projeção (G+) e Total projetado (E).
        scen_total_name = xlsxwriter.utility.xl_col_to_name(SCEN_COL_TOTAL)
        for status_range, anchor in (
            (f"{scen_proj_first_name}13:{scen_proj_last_name}13", scen_proj_first_name),
            (f"{scen_total_name}13:{scen_total_name}13", scen_total_name),
        ):
            ws.conditional_format(status_range, {"type": "formula", "criteria": f"={anchor}11<0", "format": status_bad_small})
            ws.conditional_format(status_range, {"type": "formula", "criteria": f"={anchor}11>=0", "format": status_ok_small})
        baseline_label = config_data.get("funnel_rate_baseline_label") or "média últimos 3 meses"
        comp_sales_hint = ""
        if is_inside_sales:
            _rec = int(config_data.get("tm_recurrence_months") or 1)
            _ticket = ticket_monthly * _rec if _rec > 1 else ticket_monthly
            _needed = competence_revenue / _ticket if _ticket else 0
            comp_sales_hint = (
                f"Vendas necessárias p/ meta ≈ alvo ÷ ticket (≈ {_needed:.1f} com ticket R$ {ticket_monthly:,.0f}). "
            )
        scenario_note = (
            f"A coluna {prev_month_label} traz o funil real do mês anterior fechado no Growth Pack. "
            "A coluna Alvo breakeven: linha 6 = receita meta (fee+mídia Flow ÷ margem); "
            "funil (linhas 16–32) = medianas 3M (igual Jul/26) — ponto de partida real, não funil reverso. "
            "Linha 38 = gap R$ até o alvo. "
            f"{comp_sales_hint}"
            "Colunas calendário (Jul/26+): mesmas medianas no M1; M2+ cresce taxas (Premissas). "
            f"Projeção: taxas baseline e evolução mensal em Premissas A18:D32 (editável); "
            f"colunas G+ recalculam funil, faturamento LTV e saldo. "
            f"Horizonte nas abas de cenário: {scenario_visible_months} meses (até {projection_end_year}); "
            f"aba Breakeven 7M: {projection_months} meses. "
            "Células amarelas são premissas do cenário."
        )
        if config.get("editable_media"):
            ramp = config.get("media_ramp") or {}
            scenario_note = (
                "Cenário Mídia V4 — teste de alavanca: linha 4 (investimento de mídia) e taxas do funil "
                "(linhas 17–25) são editáveis (amarelo). Projeção inicial: mídia "
                f"R$ {ramp.get('from', current_month_media):,.0f} → R$ {ramp.get('to', monthly_media):,.0f} "
                f"em {ramp.get('months', 7)} meses; faturamento deriva do funil × ticket. "
                + scenario_note
            )
        ws.merge_range(
            f"A41:{scen_sheet_last_name}43",
            scenario_note,
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

    funnel_section_row = total_row + 1
    funnel_col_header_row = funnel_section_row + 1
    funnel_first_row = funnel_col_header_row + 1
    funnel_summary_row = funnel_first_row + len(current_funnel)
    funnel_leads_row = funnel_first_row + 2
    funnel_last_row = funnel_first_row + len(current_funnel) - 1
    funnel_note_row = funnel_summary_row + 2

    data.merge_range(
        funnel_section_row,
        0,
        funnel_section_row,
        5,
        f"Funil acumulado — {funnel_lt_period}",
        section,
    )
    for col, text in enumerate(["Etapa", "Volume", "Taxa atual", "Bench interno", "Status", "Fonte"]):
        data.write(funnel_col_header_row, col, text, header)
    acc = accumulated_funnel
    if is_marketplace:
        accumulated_funnel_rows = [
            ("Impressões", acc["impressions"], None, None, "Base"),
            ("Cliques", acc["clicks"], acc["clicks"] / acc["impressions"] if acc["impressions"] else 0, bench_session_view, bench_label),
            ("Visitas", acc["leads"], acc["leads"] / acc["clicks"] if acc["clicks"] else 0, bench_view_add, bench_label),
            ("Compras", acc["mqls"], acc["mqls"] / acc["leads"] if acc["leads"] else 0, bench_add_viewcart, bench_label),
            ("Compras (plataforma)", acc["sqls"], acc["sqls"] / acc["mqls"] if acc["mqls"] else 0, bench_viewcart_checkout, bench_label),
            ("Compras faturadas", acc["sales"], acc["sales"] / acc["sqls"] if acc["sqls"] else 0, bench_shipping_payment, bench_label),
        ]
    elif is_inside_sales:
        if has_lead_quali:
            accumulated_funnel_rows = [
                ("Impressões", acc["impressions"], None, None, "Base"),
                ("Cliques", acc["clicks"], acc["clicks"] / acc["impressions"] if acc["impressions"] else 0, bench_session_view, bench_label),
                ("Leads", acc["leads"], acc["leads"] / acc["clicks"] if acc["clicks"] else 0, bench_view_add, bench_label),
                (extra_stage_label, acc["lead_quali"], acc["lead_quali"] / acc["leads"] if acc["leads"] else 0, bench_add_viewcart, bench_label),
                ("MQLs", acc["mqls"], acc["mqls"] / acc["lead_quali"] if acc["lead_quali"] else 0, bench_viewcart_checkout, bench_label),
                ("SQLs", acc["sqls"], acc["sqls"] / acc["mqls"] if acc["mqls"] else 0, bench_checkout_shipping, bench_label),
                ("Vendas", acc["sales"], acc["sales"] / acc["sqls"] if acc["sqls"] else 0, bench_shipping_payment, bench_label),
            ]
        else:
            accumulated_funnel_rows = [
                ("Impressões", acc["impressions"], None, None, "Base"),
                ("Cliques", acc["clicks"], acc["clicks"] / acc["impressions"] if acc["impressions"] else 0, bench_session_view, bench_label),
                ("Leads", acc["leads"], acc["leads"] / acc["clicks"] if acc["clicks"] else 0, bench_view_add, bench_label),
                ("MQLs", acc["mqls"], acc["mqls"] / acc["leads"] if acc["leads"] else 0, bench_add_viewcart, bench_label),
                ("SQLs", acc["sqls"], acc["sqls"] / acc["mqls"] if acc["mqls"] else 0, bench_viewcart_checkout, bench_label),
                ("Vendas", acc["sales"], acc["sales"] / acc["sqls"] if acc["sqls"] else 0, bench_shipping_payment, bench_label),
            ]
    else:
        accumulated_funnel_rows = current_funnel
    for idx, row in enumerate(accumulated_funnel_rows, funnel_first_row):
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
    summary_label = "Visitas → Compras" if is_marketplace else "Leads → Vendas" if is_inside_sales else "Sessão → Purchase"
    if is_inside_sales:
        summary_rate = acc["sales"] / acc["leads"] if acc["leads"] else 0
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
    data.write(funnel_summary_row, 5, funnel_lt_period, normal)
    source_mapping = config_data.get("source_mapping", {})
    data.merge_range(
        funnel_note_row,
        0,
        funnel_note_row + 2,
        8,
        (
            f"Fonte: Growth Pack {client}. O cenário financeiro usa Fee V4 "
            f"{source_mapping.get('fee', '')}, investimento "
            f"{source_mapping.get('media', '')} e faturamento "
            f"{source_mapping.get('revenue', '')}, apenas nos meses válidos."
        ),
        note,
    )

    bench_title_row = funnel_note_row + 4
    bench_header_row = bench_title_row + 1
    bench_data_start_row = bench_header_row + 1

    if is_marketplace:
        event_headers = ["Mês", "Impressões", "Cliques", "Visitas", "Compras", "Compras (plat.)", "Compras fat."]
        bench_last_col_name = "G"
    elif is_inside_sales:
        if has_lead_quali:
            event_headers = ["Mês", "Impressões", "Cliques", "Leads", extra_stage_label, "MQLs", "SQLs", "Vendas"]
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
    data.merge_range(
        bench_title_row,
        0,
        bench_title_row,
        ord(bench_last_col_name) - ord("A"),
        "Base mensal do bench — volumes de eventos",
        section,
    )
    for col, text in enumerate(event_headers):
        data.write(bench_header_row, col, text, header)
    for row_idx, row in enumerate(benchmark_months, bench_data_start_row):
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

    rate_title_excel_row = bench_data_start_row + len(benchmark_months) + 1
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
                f"Leads → {extra_stage_label}",
                f"{extra_stage_label} → MQLs",
                "MQLs → SQLs",
                "SQLs → Vendas",
                "Leads → Vendas",
            ]
        elif is_marketplace:
            rate_headers = [
                "Mês",
                "Impressões → Cliques",
                "Cliques → Visitas",
                "Visitas → Compras",
                "Pass-through",
                "Pass-through",
                "Visitas → Compras",
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
    final_rate_label = "Visitas → Compras" if is_marketplace else "Leads → Vendas" if is_inside_sales else "Sessão → Purchase"
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
        f"Premissas — Breakeven {'Marketplace' if is_marketplace else 'Inside Sales' if is_inside_sales else 'E-commerce'} {client}",
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
            ("Compras acumuladas" if is_marketplace else "SQLs acumulados", orders_total, "Meses com fee"),
            ("Compras faturadas" if is_marketplace else "Vendas acumuladas", sales_total, "Meses com fee"),
            ("Ticket médio", current_ticket, ticket_hist_desc),
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
            ("Ticket médio", current_ticket, ticket_hist_desc),
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
            # Fee (linha de cima -1) + Investimento (linha de cima). Refs estavam deslocadas
            # (=B6+B7) e o custo vinha só o fee → déficit subdimensionado → falso breakeven precoce.
            prem.write_formula(idx, 1, f"=B{idx - 1}+B{idx}", formula_currency, value)
        elif name == "Faturamento acumulado":
            prem.write_formula(
                idx,
                1,
                f"='Dados Fonte'!G{source_total_excel_row}",
                formula_currency,
                value,
            )
        elif name == "Ticket médio":
            # Faturamento (B10) ÷ Vendas (B13) — refs estavam deslocadas (B9/B12 = Custo/SQLs → R$159).
            prem.write_formula(idx, 1, div_formula("B10/B13"), formula_currency, value)
        elif name == "Resultado MC":
            # Faturamento (B10) × Margem (B15) — antes B9*B14 (Custo × Ticket).
            prem.write_formula(idx, 1, "=B10*B15", formula_currency, value)
        elif name == "Resultado líquido":
            # MC (B16) − Custo (B9) — antes B15-B8 (Margem − Investimento).
            prem.write_formula(idx, 1, "=B16-B9", formula_currency, value)
        else:
            prem.write_number(idx, 1, value, formula_currency)
        prem.write(idx, 2, description, normal)

    use_prem_funnel_controls = bool(is_inside_sales and config_data.get("scenario_stage_monthly_advance"))
    if use_prem_funnel_controls:
        stage_advances = config_data["scenario_stage_monthly_advance"]
        baseline_funnel_rates = config_data.get("baseline_funnel_rates") or {}
        prem.merge_range(
            "A18:D18",
            "Evolução mensal do funil — % composto por etapa (editável → atualiza todos os cenários)",
            section,
        )
        prem.write("A19", "Etapa do funil", header)
        prem.write("B19", "Pessimista %/mês", header)
        prem.write("C19", "Realista %/mês", header)
        prem.write("D19", "Otimista %/mês", header)
        for key, _sheet_row, _baseline_row, advance_row, stage_label in PREM_FUNNEL_CONTROL_STAGES:
            row_idx = advance_row - 1
            if is_marketplace:
                if key not in MARKETPLACE_STAGE_LABELS:
                    prem.set_row(row_idx, None, None, {"hidden": True})
                stage_label = MARKETPLACE_STAGE_LABELS.get(key, stage_label)
            prem.write(row_idx, 0, stage_label, label)
            prem.write_number(row_idx, 1, stage_advances["Pessimista"][key], input_percent)
            prem.write_number(row_idx, 2, stage_advances["Realista"][key], input_percent)
            prem.write_number(row_idx, 3, stage_advances["Otimista"][key], input_percent)
        stage_rate_ceilings = config_data.get("stage_rate_ceilings") or {}
        has_stage_ceilings = bool(stage_rate_ceilings)
        prem.merge_range(
            "A26:C26" if has_stage_ceilings else "A26:B26",
            "Taxas baseline — M1 da projeção (editável → ponto de partida do funil)",
            section,
        )
        prem.write("A27", "Etapa do funil", header)
        prem.write("B27", "Taxa baseline", header)
        if has_stage_ceilings:
            prem.write("C27", "Teto realista (máx)", header)
        for key, _sheet_row, baseline_row, _advance_row, stage_label in PREM_FUNNEL_CONTROL_STAGES:
            row_idx = baseline_row - 1
            if is_marketplace:
                if key not in MARKETPLACE_STAGE_LABELS:
                    prem.set_row(row_idx, None, None, {"hidden": True})
                stage_label = MARKETPLACE_STAGE_LABELS.get(key, stage_label)
            prem.write(row_idx, 0, stage_label, label)
            prem.write_number(row_idx, 1, baseline_funnel_rates.get(key, 0), input_percent)
            if has_stage_ceilings:
                prem.write_number(
                    row_idx, 2, stage_rate_ceilings.get(key, max_conversion_rate), input_percent
                )
        prem.data_validation(
            "B20:D24",
            {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 1},
        )
        prem.data_validation(
            "B28:B32",
            {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": max_conversion_rate},
        )
        if has_stage_ceilings:
            prem.data_validation(
                "C28:C32",
                {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": max_conversion_rate},
            )

    prem.merge_range(f"E3:{prem_proj_last_name}3", "Premissas futuras — células amarelas são editáveis", section)
    future_inputs = [
        ("Fee mensal", monthly_fee, input_currency),
        ("Mídia mensal (Flow competência)", monthly_media, input_currency),
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
            prem.write_formula(idx, 5, "=(ABS(B16)+F9)/F7", fmt, value)
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
            (16, f"Leads → {extra_stage_label}"),
            (17, f"{extra_stage_label} → MQLs"),
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
    elif is_marketplace:
        prem_rate_rows = [
            (14, "Impressões → Cliques"),
            (15, "Cliques → Visitas"),
            (16, "Visitas → Compras"),
            (17, "Pass-through (100%)"),
            (18, "Pass-through (100%)"),
        ]
        for row_idx, label_text in prem_rate_rows:
            prem.write(row_idx, 4, label_text, label)
        prem.write(19, 4, "Visitas → Compras", label)
    elif is_inside_sales:
        prem_rate_rows = [
            (14, "Impressões → Cliques"),
            (15, "Cliques → Leads"),
            (16, "Leads → MQLs"),
            (17, "MQLs → SQLs"),
            (18, "SQLs → Vendas"),
        ]
        for row_idx, label_text in prem_rate_rows:
            prem.write(row_idx, 4, label_text, label)
        prem.write(19, 4, "Leads → Vendas", label)
    else:
        prem.write("E15", "View item / sessão", label)
        prem.write("E16", "Add to cart / view item", label)
        prem.write("E17", "Purchase / add to cart", label)
        prem.write("E18", "Aprovação pedido → venda", label)
    stage_by_prem_row = {
        PREM_MONTHLY_RATE_ROWS[i]: PREM_FUNNEL_CONTROL_STAGES[i]
        for i in range(len(PREM_MONTHLY_RATE_ROWS))
    }
    for idx in range(projection_months):
        col = prem_proj_start_col + idx
        prem_col = xlsxwriter.utility.xl_col_to_name(col)
        previous_prem_col = xlsxwriter.utility.xl_col_to_name(col - 1) if idx > 0 else None
        revenue = projected_revenue[idx]
        prem.write_number(13, col, revenue, input_currency)
        if is_inside_sales and has_lead_quali:
            prem.write_number(14, col, view_rates[idx], input_percent)
            prem.write_number(15, col, cart_rates[idx], input_percent)
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
            prem.write_number(14, col, view_rates[idx], input_percent)
            prem.write_number(15, col, cart_rates[idx], input_percent)
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
        elif is_inside_sales and use_prem_funnel_controls:
            rate_series = [view_rates, cart_rates, lead_mql_rates, mql_sql_rates, sql_sale_rates]
            for series_idx, prem_row_0 in enumerate(PREM_MONTHLY_RATE_ROWS):
                _key, _srow, baseline_row, advance_row, _label = stage_by_prem_row[prem_row_0]
                rate_formula = compound_premissas_rate_formula(
                    prem_row_0=prem_row_0,
                    baseline_excel_row=baseline_row,
                    advance_excel_row=advance_row,
                    prev_col_name=previous_prem_col,
                    month_idx=idx,
                    max_rate=max_conversion_rate,
                    use_stage_ceilings=bool(config_data.get("stage_rate_ceilings")),
                )
                prem.write_formula(prem_row_0, col, rate_formula, input_percent, rate_series[series_idx][idx])
            prem.write_formula(
                19,
                col,
                f"={prem_col}17*{prem_col}18*{prem_col}19",
                formula_percent,
                lead_to_sale_rates[idx],
            )
        elif is_inside_sales:
            prem.write_number(14, col, view_rates[idx], input_percent)
            prem.write_number(15, col, cart_rates[idx], input_percent)
            prem.write_number(16, col, lead_mql_rates[idx], input_percent)
            prem.write_number(17, col, mql_sql_rates[idx], input_percent)
            prem.write_number(18, col, sql_sale_rates[idx], input_percent)
            prem.write_formula(
                19,
                col,
                f"={prem_col}15*{prem_col}16*{prem_col}17*{prem_col}18",
                formula_percent,
                lead_to_sale_rates[idx],
            )
        else:
            prem.write_number(14, col, view_rates[idx], input_percent)
            prem.write_number(15, col, cart_rates[idx], input_percent)
            prem.write_number(16, col, cart_to_purchase, input_percent)
            prem.write_number(17, col, approval_rates[idx], input_percent)
    if analysis_media_from_gp:
        media_label_row = 21 if is_inside_sales and not has_lead_quali else 19
        media_value_row = 20 if is_inside_sales and not has_lead_quali else 18
        prem.write(media_label_row, 4, "Investimento mídia (GP linha 5)", label)
        for idx in range(projection_months):
            prem.write_number(media_value_row, prem_proj_start_col + idx, projected_media[idx], input_currency)
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
    elif is_inside_sales and not has_lead_quali:
        prem.data_validation(
            f"F15:{prem_proj_last_name}19",
            {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": max_conversion_rate},
        )
    else:
        prem.data_validation(f"F15:{prem_proj_last_name}18", {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 1})
    prem_note_row = 34 if use_prem_funnel_controls else (
        23
        if use_unified_breakeven or (analysis_media_from_gp and is_inside_sales and not has_lead_quali)
        else (22 if analysis_media_from_gp else 20)
    )
    prem.merge_range(
        f"A{prem_note_row}:{prem_proj_last_name}{prem_note_row + 2}",
        (
            f"Como usar: altere somente as células amarelas. A projeção roda por {projection_months} meses "
            f"até o breakeven ({minimum_breakeven_label}) ou até o limite de {MAX_PROJECTION_MONTHS} meses. "
            + (
                "Controle central do funil: Premissas A18:D32 (% mensal por cenário + baseline M1 + teto por etapa C28:C32). "
                "Cada taxa satura no teto da sua etapa (não compõe ao infinito). "
                "Ao alterar, Pessimista/Realista/Otimista/Mídia V4 e Breakeven 7M recalculam. "
                if use_prem_funnel_controls
                else ""
            )
            + (
                "Investimento projetado = últimos meses do GP (linha 5, aba 6.0); F5 = Flow competência. "
                if analysis_media_from_gp
                else ""
            )
            + (
                "Leads → Vendas (linha 21) é calculada automaticamente a partir das taxas operacionais. "
                if is_inside_sales and has_lead_quali
                else (
                    "Visitas → Compras (linha 20) é calculada automaticamente a partir das taxas operacionais. "
                    if is_marketplace
                    else
                    "Leads → Vendas (linha 20) é calculada automaticamente a partir das taxas operacionais. "
                    if is_inside_sales
                    else (
                    "Sessão → Venda (linha 21) é calculada automaticamente a partir das taxas operacionais. "
                    if not is_inside_sales and use_unified_breakeven
                    else ""
                )
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
            extra_label=extra_stage_label,
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
            current_ticket=ticket_monthly,
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
        row_labels = breakeven_financial_row_labels(
            is_inside_sales, funnel_conversion_label, is_marketplace
        )
        if is_marketplace:
            # Esconde Taxa SQLs→Vendas / Vendas / Custo por Venda (duplicam Compras).
            for _hidden_row in (10, 11, 12):
                be.set_row(_hidden_row - 1, None, None, {"hidden": True})
        for row_num, text in row_labels.items():
            be.write(row_num - 1, 0, text, label)
    
        current_values = {
            2: current_cost,
            3: fee_total,
            4: media_total,
            5: sessions_total,
            6: inside_sales_cps if is_inside_sales else media_total / sessions_total if sessions_total else 0,
            7: orders_total / sessions_total,
            8: orders_total,
            9: media_total / orders_total if orders_total else 0,
            10: sales_total / orders_total if orders_total else 0,
            11: sales_total,
            12: media_total / sales_total if sales_total else 0,
            13: sales_total / leads_total if is_inside_sales and leads_total else (sales_total / sessions_total if sessions_total else 0),
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
        # IS com recorrência: linha 18 (faturamento histórico) precisa ser LTV = vendas × ticket × meses.
        # A fórmula padrão ='Premissas'!B10 usa receita bruta do GP, que subestima em 1/rec_months.
        _be_rec_early = int(config_data.get("tm_recurrence_months") or 1)
        if is_inside_sales and _be_rec_early > 1 and sales_total:
            _ltv_hist = sales_total * float(ticket_monthly or 0) * _be_rec_early
            current_values[18] = _ltv_hist
            current_values[21] = _ltv_hist * margin
            current_values[22] = _ltv_hist * margin
            current_values[27] = _ltv_hist * margin - current_cost
            current_values[28] = _ltv_hist * margin - current_cost
            current_values[29] = (_ltv_hist * margin) / current_cost if current_cost else 0
            current_values[30] = (_ltv_hist * margin) / current_cost if current_cost else 0
            current_formulas[18] = f"='Premissas'!B13*'Premissas'!B14*{_be_rec_early}"
        for row_num, value in current_values.items():
            fmt = formula_percent if row_num in (7, 10, 13, 16) else formula_int if row_num in (5, 8, 11) else formula_number if row_num in (20, 29, 30) else formula_currency
            if row_num == 13 and is_inside_sales:
                be.write_number(row_num - 1, 1, value, fmt)
                continue
            if row_num == 6 and is_inside_sales:
                be.write_number(row_num - 1, 1, inside_sales_cps, formula_currency)
                continue
            be.write_formula(row_num - 1, 1, current_formulas[row_num], fmt, value)
        be.write_formula(32, 1, '=IF(B28>=0,"Já breakevado","Déficit a recuperar")', status_bad, "Déficit a recuperar")
    
        # Inside sales com recorrência: receita (linha 18) é LTV (= venda × ticket × meses).
        # As vendas têm de descontar a recorrência, senão o motor legacy divide LTV pelo
        # ticket mensal e infla as vendas pelo fator de recorrência (~7×). Alinha ao funil
        # Realista (mesma contagem de vendas). e-commerce e clientes sem recorrência intactos.
        be_recurrence = int(config_data.get("tm_recurrence_months") or 1)
        be_ltv_sales = is_inside_sales and be_recurrence > 1

        def be_proj_sales(p: dict) -> float:
            # Espelha a fórmula da linha 11: receita ÷ (ticket fixo $B$15 × recorrência).
            # Usa o ticket mensal corrente (constante), não o ticket do motor (cresce 1%/mês).
            if be_ltv_sales and current_ticket:
                return p["revenue"] / (current_ticket * be_recurrence)
            return p["sales"]

        for idx, proj in enumerate(projections):
            col = 4 + idx
            month_col = xlsxwriter.utility.xl_col_to_name(col)
            prem_col = xlsxwriter.utility.xl_col_to_name(5 + idx)
            previous_col = xlsxwriter.utility.xl_col_to_name(col - 1)
            proj_sales = be_proj_sales(proj)
            monthly_values = {
                2: proj["monthly_cost"],
                3: monthly_fee,
                4: proj["monthly_media"],
                5: proj["sessions"],
                6: inside_sales_month_cps(idx) if is_inside_sales else proj["cps"],
                7: proj["orders"] / proj["sessions"],
                8: proj["orders"],
                9: proj["cpp"],
                10: proj["approval"],
                11: proj_sales,
                12: proj["monthly_media"] / proj_sales if proj_sales else proj["cpv"],
                13: lead_to_sale_rates[idx] if is_inside_sales else proj["final_conversion"],
                15: current_ticket if be_ltv_sales else proj["ticket"],
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
            if is_inside_sales:
                impressions_formula = f"=ROUND({month_col}4/{month_col}6,0)"
                # CPS de projeção = baseline recente (mesmo das abas de cenário), não o CPS
                # acumulado (B6). Fixo em E6 para as impressões baterem com a aba Realista
                # (cenário mínimo). Sem isso, a Breakeven 7M usava CPS diferente → funil não fechava.
                cps_formula = None if idx == 0 else "=$E$6"
            else:
                impressions_formula = f"{month_col}11/{month_col}13"
                cps_formula = div_formula(f"{month_col}4/{month_col}5")
            formulas = {
                2: f"={month_col}3+{month_col}4",
                3: "='Premissas'!F4",
                4: None if analysis_media_from_gp else "='Premissas'!F5",
                5: impressions_formula,
                6: cps_formula,
                7: div_formula(f"{month_col}8/{month_col}5"),
                8: div_formula(f"{month_col}11/{month_col}10"),
                9: div_formula(f"{month_col}4/{month_col}8"),
                10: f"='Premissas'!{prem_col}19" if is_inside_sales else f"='Premissas'!{prem_col}18",
                11: (
                    div_formula(f"{month_col}18/({month_col}15*{be_recurrence})")
                    if be_ltv_sales
                    else div_formula(f"{month_col}18/{month_col}15")
                ),
                12: div_formula(f"{month_col}4/{month_col}11"),
                13: (
                    f"={inside_sales_lead_to_sale_expr(prem_col, has_lead_quali)}"
                    if is_inside_sales
                    else f"='Premissas'!{prem_col}15*'Premissas'!{prem_col}16*'Premissas'!{prem_col}17"
                ),
                15: "=$B$15" if be_ltv_sales else ("=B15" if idx == 0 else f"={previous_col}15*1.01"),
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
                formula = formulas[row_num]
                if formula is None:
                    be.write_number(
                        row_num - 1,
                        col,
                        value,
                        input_currency if row_num == 4 else fmt,
                    )
                else:
                    be.write_formula(row_num - 1, col, formula, fmt, value)
    
        # Col. C ("Cenário mínimo") = agregado real do funil projetado (Realista), não mais
        # o requisito de breakeven forçado. Cache alinhado às fórmulas =SUM(...) para o preview
        # e a validação refletirem o que o Sheets recalcula. Linha 32 segue sendo o requisito.
        agg_sales = sum(be_proj_sales(p) for p in projections)
        agg_revenue = sum(p["revenue"] for p in projections)
        agg_media = sum(p["monthly_media"] for p in projections)
        agg_mc = agg_revenue * margin
        aggregate_values = {
            2: future_cost,
            3: projection_months * monthly_fee,
            4: agg_media,
            5: sum(p["sessions"] for p in projections),
            6: agg_media / sum(p["sessions"] for p in projections),
            7: sum(p["orders"] for p in projections) / sum(p["sessions"] for p in projections),
            8: sum(p["orders"] for p in projections),
            9: agg_media / sum(p["orders"] for p in projections),
            10: agg_sales / sum(p["orders"] for p in projections),
            11: agg_sales,
            12: agg_media / agg_sales if agg_sales else 0,
            13: (
                agg_sales
                / sum(
                    be_proj_sales(p) / lead_to_sale_rates[i]
                    for i, p in enumerate(projections)
                    if lead_to_sale_rates[i]
                )
                if is_inside_sales
                else agg_sales / sum(p["sessions"] for p in projections)
            ),
            15: agg_revenue / agg_sales if agg_sales else 0,
            16: margin,
            18: agg_revenue,
            19: agg_revenue,
            20: agg_revenue / agg_media if agg_media else 0,
            21: agg_mc,
            22: agg_mc,
            24: future_cost,
            25: future_cost,
            27: agg_mc - future_cost,
            28: round(current_result + (agg_mc - future_cost), 2),
            29: agg_mc / future_cost if future_cost else 0,
            30: (current_mc + agg_mc) / (current_cost + future_cost),
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
        integrated_rows = integrated_funnel_row_labels(
            is_inside_sales, final_funnel_rate_label, has_lead_quali, extra_stage_label, is_marketplace
        )
        if is_marketplace:
            for _hidden_row in MARKETPLACE_INTEGRATED_HIDE_ROWS:
                be.set_row(_hidden_row - 1, None, None, {"hidden": True})
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
                acc = accumulated_funnel
                current_integrated = {
                    37: acc["impressions"],
                    38: acc["clicks"] / acc["impressions"] if acc["impressions"] else 0,
                    39: acc["clicks"],
                    40: acc["leads"] / acc["clicks"] if acc["clicks"] else 0,
                    41: acc["leads"],
                    42: acc["mqls"] / acc["leads"] if acc["leads"] else 0,
                    43: acc["mqls"],
                    44: acc["sqls"] / acc["mqls"] if acc["mqls"] else 0,
                    45: acc["sqls"],
                    48: acc["sales"] / acc["sqls"] if acc["sqls"] else 0,
                    53: acc["sales"],
                    54: acc["sales"] / acc["leads"] if acc["leads"] else 0,
                    55: acc["media"] / acc["impressions"] if acc["impressions"] else 0,
                    56: acc["media"] / acc["sqls"] if acc["sqls"] else 0,
                    57: acc["media"] / acc["sales"] if acc["sales"] else 0,
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
                funnel_volumes = build_inside_sales_funnel_forward(
                    proj["monthly_media"],
                    inside_sales_month_cps(idx),
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
                        38: (f"='Premissas'!{prem_col}15", minimum_full_rates["session_view"][idx]),
                        40: (f"='Premissas'!{prem_col}16", minimum_full_rates["view_add"][idx]),
                        42: (f"='Premissas'!{prem_col}17", minimum_full_rates["add_view_cart"][idx]),
                        44: (f"='Premissas'!{prem_col}18", minimum_full_rates["viewcart_checkout"][idx]),
                        48: (f"='Premissas'!{prem_col}19", minimum_full_rates["shipping_payment"][idx]),
                    }
                    volume_map = {
                        37: (f"={col_name}5", sessions),
                        39: (f"=ROUND({col_name}37*{col_name}38,0)", view_item),
                        41: (f"=ROUND({col_name}39*{col_name}40,0)", add_cart),
                        43: (f"=ROUND({col_name}41*{col_name}42,0)", view_cart),
                        45: (f"=ROUND({col_name}43*{col_name}44,0)", checkout),
                        # Vendas fecham o funil (SQLs × taxa SQLs→Vendas), não copiam o topo.
                        53: (f"=ROUND({col_name}45*{col_name}48,0)", sales),
                        54: (
                            f"={inside_sales_lead_to_sale_expr(prem_col, False)}",
                            sales / add_cart if add_cart else 0,
                        ),
                        55: (div_formula(f"{col_name}4/{col_name}37"), proj["monthly_media"] / sessions if sessions else 0),
                        56: (div_formula(f"{col_name}4/{col_name}45"), proj["monthly_media"] / checkout if checkout else 0),
                        57: (div_formula(f"{col_name}4/{col_name}53"), proj["monthly_media"] / sales if sales else 0),
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
                if isinstance(value, tuple):
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
    
    scenario_worksheets = []
    for scenario_name in scenario_sheet_order:
        if scenario_name in scenario_configs:
            scenario_worksheets.append(
                write_scenario_sheet(scenario_name, scenario_configs[scenario_name])
            )

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
    summary_label_fc = "Visitas → Compras" if is_marketplace else "Leads → Vendas" if is_inside_sales else "Sessão → Purchase"
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
            lead_to_sale_formula = inside_sales_lead_to_sale_expr(prem_col, False)
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
            f"Leads → {extra_stage_label}",
            f"{extra_stage_label} → MQLs",
            "MQLs → SQLs",
            "SQLs → Vendas",
        ]
        rate_prem_rows = [15, 16, 17, 18, 19, 20]
        note_start_row = 23
    elif is_inside_sales:
        rate_rows = [
            "Impressões → Cliques",
            "Cliques → Leads",
            "Leads → MQLs",
            "MQLs → SQLs",
            "SQLs → Vendas",
        ]
        rate_prem_rows = [15, 16, 17, 18, 19]
        note_start_row = 22
    else:
        rate_rows = ["Sessão → View item", "View item → Add to cart", "Add to cart → Purchase"]
        rate_prem_rows = [15, 16, 17]
        note_start_row = 21
    for idx, stage in enumerate(rate_rows, 16):
        funnel.write(idx, 6, stage, label)
    rate_series_by_prem_row = {
        15: view_rates,
        16: cart_rates,
        17: lead_lead_quali_rates if is_inside_sales and has_lead_quali else lead_mql_rates if is_inside_sales else lead_to_sale_rates,
        18: lead_quali_mql_rates if is_inside_sales and has_lead_quali else mql_sql_rates if is_inside_sales else None,
        19: mql_sql_rates if is_inside_sales and has_lead_quali else sql_sale_rates if is_inside_sales else None,
        20: sql_sale_rates if is_inside_sales and has_lead_quali else None,
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
        ("Ticket médio", current_ticket, projection_ticket, "LTV projeção nas premissas futuras" if config_data.get("tm_recurrence_months") else "Crescimento leve de 1% ao mês"),
    ]
    imp_meta = config_data.get("impression_traceability") or {}
    if is_inside_sales and imp_meta:
        m1_impressions = projections[0]["sessions"] if projections else 0
        comparison.append(
            (
                "Impressões",
                imp_meta.get("funnel_accumulated", sessions_total),
                m1_impressions,
                (
                    f"Acum. funil {imp_meta.get('funnel_accumulated', 0):,.0f} · "
                    f"M1 {m1_impressions:,.0f} = Flow ÷ CPI mediano "
                    f"(≠ mediana mensal {imp_meta.get('funnel_median_monthly', 0):,.0f})"
                ),
            )
        )
    comparison.extend(
        [
        (
            "Custo por impressão" if is_inside_sales else "Custo por sessão",
            media_total / sessions_total if sessions_total else 0,
            imp_meta.get("projection_cps_median", projection_months * monthly_media / sum(p["sessions"] for p in projections))
            if is_inside_sales and imp_meta
            else projection_months * monthly_media / sum(p["sessions"] for p in projections),
            "Histórico acum. vs CPI mediano da projeção (Premissas G34)"
            if is_inside_sales and imp_meta
            else "Exige eficiência e tráfego não pago",
        ),
        ("Resultado líquido", current_result, 0, f"Projeto zerado no {minimum_breakeven_label}"),
        ]
    )
    for ridx, (indicator, current, minimum, reading) in enumerate(comparison, 12):
        summary.merge_range(ridx, 1, ridx, 2, indicator, label)
        fmt = (
            normal_percent
            if "Conversão" in indicator
            else normal
            if "Impressões" in indicator
            else normal_currency
        )
        summary.merge_range(ridx, 3, ridx, 4, current, fmt)
        summary.merge_range(ridx, 5, ridx, 6, minimum, fmt)
        summary.merge_range(ridx, 7, ridx, 9, reading, normal)

    summary.merge_range("B20:J20", "Evolução financeira", section)
    chart = workbook.add_chart({"type": "line"})
    chart_result_row = 28
    if use_unified_breakeven:
        from breakeven_unified_sheet import BEU

        chart_result_row = BEU["result_acc"]
    chart.add_series(
        {
            "name": "Resultado líquido acumulado",
            "categories": f"='Premissas'!$F$13:${prem_proj_last_name}$13",
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

    summary.merge_range("B42:J42", "Comparativo dos cenários", section)
    for col, text in enumerate(
        [
            "Cenário",
            f"Receita {scenario_visible_months}M",
            f"Mídia {scenario_visible_months}M",
            "Saldo final",
            "Mês de breakeven",
        ],
        1,
    ):
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
    for scenario_name in scenario_sheet_order:
        if scenario_name not in scenario_configs:
            continue
        config = scenario_configs[scenario_name]
        plan = scenario_financial_plans[scenario_name]
        plan_slice = plan[:scenario_visible_months]
        scenario_revenue_total = sum(config["revenue"][:scenario_visible_months])
        scenario_summary.append(
            (
                scenario_name,
                scenario_revenue_total,
                sum(row["media"] for row in plan_slice),
                plan_slice[-1]["cumulative_result"] if plan_slice else 0,
                breakeven_month_from_rows(plan_slice),
            )
        )
    for idx, (name, revenue, media, balance, month) in enumerate(scenario_summary, 43):
        summary.merge_range(idx, 1, idx, 2, name, label)
        if name == "Cenário mínimo (Breakeven)":
            be_revenue_row = 25 if use_unified_breakeven else 18
            be_media_row = 5 if use_unified_breakeven else 4
            be_result_row = 28
            if use_unified_breakeven:
                from breakeven_unified_sheet import BEU

                be_result_row = BEU["result_acc"]
            be_result_last_col = f"{be_proj_last_name}{be_result_row}"
            summary.merge_range(idx, 3, idx, 4, "", formula_currency)
            summary.write_formula(idx, 3, f"='Breakeven 7M'!C{be_revenue_row}", formula_currency, revenue)
            summary.merge_range(idx, 5, idx, 6, "", formula_currency)
            summary.write_formula(idx, 5, f"='Breakeven 7M'!C{be_media_row}", formula_currency, media)
            summary.merge_range(idx, 7, idx, 8, "", formula_currency)
            summary.write_formula(idx, 7, f"='Breakeven 7M'!{be_result_last_col}", formula_currency, balance)
        else:
            sheet = name
            summary.merge_range(idx, 3, idx, 4, "", formula_currency)
            summary.write_formula(idx, 3, f"='{sheet}'!{scen_total_col_name}6", formula_currency, revenue)
            summary.merge_range(idx, 5, idx, 6, "", formula_currency)
            summary.write_formula(idx, 5, f"='{sheet}'!{scen_total_col_name}4", formula_currency, media)
            summary.merge_range(idx, 7, idx, 8, "", formula_currency)
            summary.write_formula(idx, 7, f"='{sheet}'!{scen_total_col_name}11", formula_currency, balance)
        summary.write(
            idx,
            9,
            month,
            status_ok if month != "Não breakeva" else status_bad,
        )

    # Ordem das abas
    summary.activate()
    summary.set_first_sheet()
    workbook.worksheets_objs = [summary, be, *scenario_worksheets, funnel, prem, data]

    workbook.close()
    print(output)


if __name__ == "__main__":
    main()
