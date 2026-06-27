"""Projeção financeira compartilhada — Breakeven, cenários e Resumo Executivo."""
from __future__ import annotations

from datetime import date
from statistics import median
from typing import Any

PROJECTION_END_YEAR = 2030
PROJECTION_END_MONTH = 12

MONTH_PT = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}


def format_brl(value: float) -> str:
    return f"R$ {value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def select_projection_baseline_months(
    months: list[dict[str, Any]],
    *,
    baseline_window: int = 3,
    skip_last: bool = True,
) -> list[dict[str, Any]]:
    """Meses usados na mediana de taxas/CPI para projeção.

    - skip_last=True (default): remove o último mês antes de janelaar (para quando o mês
      corrente parcial ainda está no pool).
    - skip_last=False: todos os meses já são fechados (ex.: exclude_reference_month=True
      já removeu o mês parcial) — pegar os últimos N diretamente.
    - Histórico ≤ janela: usa todos os meses disponíveis.
    """
    if not months:
        return []
    if skip_last:
        pool = months[:-1] if len(months) > baseline_window else list(months)
    else:
        pool = list(months)
    if len(pool) >= baseline_window:
        return pool[-baseline_window:]
    return list(pool)


def select_cpi_baseline_months(
    investment_months: list[dict[str, Any]],
    *,
    traffic_key: str = "impressions",
    baseline_window: int = 3,
) -> list[dict[str, Any]]:
    """Meses com mídia + impressões/sessões — inclui pré-funil (ex.: Abr com mídia, sem vendas)."""
    pool = [
        m
        for m in investment_months
        if float(m.get("media", 0) or 0) > 0 and float(m.get(traffic_key, 0) or 0) > 0
    ]
    return select_projection_baseline_months(pool, baseline_window=baseline_window)


def build_impression_traceability(
    *,
    funnel_months: list[dict[str, Any]],
    investment_months: list[dict[str, Any]],
    funnel_lt_period: str,
    projection_media: float,
    projection_cps: float,
    traffic_key: str = "impressions",
    cpi_baseline_labels: list[str] | None = None,
) -> dict[str, Any]:
    """Metadados para evitar confundir mediana/CPI histórico com volume M1 projetado."""
    funnel_volumes = [
        float(m.get(traffic_key, 0) or 0)
        for m in funnel_months
        if float(m.get(traffic_key, 0) or 0) > 0
    ]
    investment_volumes = [
        float(m.get(traffic_key, 0) or 0)
        for m in investment_months
        if float(m.get(traffic_key, 0) or 0) > 0
    ]
    funnel_accumulated = round(sum(funnel_volumes), 0)
    funnel_median = round(median(funnel_volumes), 0) if funnel_volumes else 0.0
    investment_accumulated = round(sum(investment_volumes), 0)
    projection_m1 = round(projection_media / projection_cps, 0) if projection_cps > 0 else 0.0
    traffic_label = "impressões" if traffic_key == "impressions" else "sessões"
    cpi_window = (
        f"mediana {len(cpi_baseline_labels)}M ({' · '.join(cpi_baseline_labels)})"
        if cpi_baseline_labels
        else "mediana CPI"
    )
    return {
        "funnel_accumulated": funnel_accumulated,
        "funnel_median_monthly": funnel_median,
        "investment_accumulated": investment_accumulated,
        "projection_m1_volume": projection_m1,
        "projection_media_flow": round(projection_media, 2),
        "projection_cps_median": round(projection_cps, 8),
        "cpi_baseline_labels": cpi_baseline_labels or [],
        "projection_formula": f"mídia Flow ÷ CPI mediano = {format_brl(projection_media)} ÷ R$ {projection_cps:.4f}",
        "projection_note": (
            f"Histórico funil ({funnel_lt_period}): acum. {funnel_accumulated:,.0f} {traffic_label} · "
            f"mediana mensal {funnel_median:,.0f}. "
            f"CPI {cpi_window} = R$ {projection_cps:.4f}/impressão. "
            f"M1 projetadas {projection_m1:,.0f} = {format_brl(projection_media)} ÷ CPI mediano "
            f"(referência Flow — cenários IS usam mediana de volume {funnel_median:,.0f} imp)."
        ),
    }


def effective_media_for_month(
    idx: int,
    *,
    planned_media: float,
    base_monthly_media: float,
    previous_monthly_result: float | None,
    media_lever_after_monthly_breakeven: bool,
) -> float:
    if (
        media_lever_after_monthly_breakeven
        and idx > 0
        and previous_monthly_result is not None
        and previous_monthly_result >= -0.01
    ):
        return base_monthly_media * (1 + 0.05 * idx)
    return planned_media


def compute_financial_projections(
    *,
    revenue_series: list[float],
    media_series: list[float],
    ticket_series: list[float] | None,
    monthly_fee: float,
    base_monthly_media: float,
    margin: float,
    current_result: float,
    projection_months: int,
    media_lever_after_monthly_breakeven: bool = False,
    current_ticket: float = 1.0,
) -> list[dict]:
    """Motor financeiro único: MC, resultado mensal/acumulado, ROAS, vendas."""
    rows: list[dict] = []
    cumulative = current_result
    for idx in range(projection_months):
        revenue = revenue_series[idx]
        planned_media = media_series[idx]
        ticket = (
            ticket_series[idx]
            if ticket_series and idx < len(ticket_series)
            else current_ticket * (1.01**idx)
        )
        previous_monthly = rows[idx - 1]["monthly_result"] if idx > 0 else None
        media = effective_media_for_month(
            idx,
            planned_media=planned_media,
            base_monthly_media=base_monthly_media,
            previous_monthly_result=previous_monthly,
            media_lever_after_monthly_breakeven=media_lever_after_monthly_breakeven,
        )
        cost = monthly_fee + media
        mc = revenue * margin
        monthly_result = mc - cost
        cumulative = round(cumulative + monthly_result, 2)
        sales = revenue / ticket if ticket else 0
        rows.append(
            {
                "revenue": revenue,
                "ticket": ticket,
                "sales": sales,
                "media": media,
                "planned_media": planned_media,
                "monthly_cost": cost,
                "monthly_mc": mc,
                "monthly_result": monthly_result,
                "cumulative_result": cumulative,
                "roas": revenue / media if media else 0,
            }
        )
    return rows


def projection_start_month_offset(reference: date) -> int:
    """Meses à frente do mês de referência para a 1ª coluna projetada.

    Sempre o mês seguinte ao da geração (ex.: 22/jun/2026 → Jul/26).
    A menção ao dia 15/16 na spec é só o corte operacional do mês corrente;
    a projeção começa no próximo mês calendário em ambos os casos.
    """
    return 1


def projection_month_label(year: int, month: int) -> str:
    return f"{MONTH_PT[month]}/{year % 100:02d}"


def projection_month_count(
    reference: date | None = None,
    *,
    end_year: int = PROJECTION_END_YEAR,
    end_month: int = PROJECTION_END_MONTH,
) -> int:
    """Meses projetados do 1º mês após a referência até end_month/end_year (inclusive)."""
    ref = reference or date.today()
    offset = projection_start_month_offset(ref)
    start_year = ref.year
    start_month = ref.month + offset
    while start_month > 12:
        start_month -= 12
        start_year += 1
    if start_year > end_year or (start_year == end_year and start_month > end_month):
        return 1
    return (end_year - start_year) * 12 + (end_month - start_month + 1)


def projection_month_headers(
    count: int,
    reference: date | None = None,
) -> list[str]:
    ref = reference or date.today()
    offset = projection_start_month_offset(ref)
    year = ref.year
    month = ref.month + offset
    while month > 12:
        month -= 12
        year += 1
    headers: list[str] = []
    for _ in range(count):
        headers.append(projection_month_label(year, month))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return headers


def breakeven_month_from_rows(rows: list[dict]) -> str:
    for idx, row in enumerate(rows, 1):
        if row["cumulative_result"] >= -0.01:
            return f"Mês {idx}"
    return "Não breakeva"


def first_monthly_breakeven(rows: list[dict]) -> str | None:
    for idx, row in enumerate(rows, 1):
        if row["monthly_result"] >= -0.01:
            return f"Mês {idx}"
    return None
