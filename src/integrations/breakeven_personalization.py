"""Textos da planilha personalizados por projeto (config + Growth Pack)."""
from __future__ import annotations

from breakeven_projection import format_brl, first_monthly_breakeven


def traffic_term(is_inside_sales: bool) -> str:
    return "impressões" if is_inside_sales else "sessões"


def breakeven_product_label(is_inside_sales: bool) -> str:
    return "Inside Sales" if is_inside_sales else "E-commerce"


def scenario_actual_column_label(config: dict) -> str:
    period = config.get("current_period", "período atual")
    month_hint = period.split()[0] if period else "atual"
    return f"Atual acumulado /\nfunil {month_hint}"


def build_strategic_reading(
    config: dict,
    *,
    is_inside_sales: bool,
    minimum_breakeven_label: str,
    financial_rows: list[dict],
) -> str:
    ctx = config.get("context", {})
    media_label = format_brl(config["monthly_media"])
    fee_label = format_brl(config["monthly_fee"])
    margin_pct = f"{config['margin']:.0%}"
    traffic = traffic_term(is_inside_sales)
    monthly_bep = first_monthly_breakeven(financial_rows)

    lines = ["Leitura estratégica", ""]

    diagnosis = ctx.get("diagnosis") or []
    if diagnosis:
        for item in diagnosis[:2]:
            lines.append(item)
    else:
        mapping = config.get("source_mapping", {})
        funnel_hint = mapping.get("funnel", "funil do Growth Pack")
        lines.append(
            f"Premissas derivadas do Growth Pack ({funnel_hint}). "
            f"Fee {fee_label}, mídia base {media_label}, margem {margin_pct}."
        )

    seasonal = ctx.get("seasonal") or config.get("strategy_review_context")
    if seasonal:
        lines.extend(["", "Contexto sazonal (Strategy Review):", str(seasonal).strip()])

    lines.append("")
    lever_note = ""
    rules = config.get("projection_rules") or {}
    if rules.get("media_lever_after_monthly_breakeven"):
        lever_note = (
            " A alavanca de mídia (+5% após resultado mensal positivo) "
            "atraso o breakeven acumulado em relação ao breakeven mensal."
        )
    lines.append(
        f"Breakeven acumulado projetado: {minimum_breakeven_label}."
        + (f" Breakeven mensal (competência): {monthly_bep}." if monthly_bep else "")
        + lever_note
    )
    lines.append(
        f"Com verba mensal base de {media_label}, o projeto precisa combinar melhora de conversão, "
        f"recuperação de tracking, CRM/recompra e tráfego orgânico para atingir as {traffic} "
        f"necessárias sem pressionar o custo de aquisição."
    )

    main_risk = ctx.get("main_risk")
    if main_risk:
        lines.extend(["", f"Principal risco: {main_risk}"])

    actions = ctx.get("actions") or []
    if actions:
        lines.extend(["", f"Próxima ação: {actions[0]}"])

    return "\n".join(lines)


def build_resumo_title(client: str, is_inside_sales: bool) -> str:
    return f"Breakeven {breakeven_product_label(is_inside_sales)} — {client}"
