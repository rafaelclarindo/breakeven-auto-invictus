"""Projeção financeira compartilhada — Breakeven, cenários e Resumo Executivo."""
from __future__ import annotations

from datetime import date

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

    - Dia da geração <= 15: começa no mês seguinte.
    - Dia da geração >= 16: começa no mês subsequente (pula o mês imediato).
    """
    return 1 if reference.day <= 15 else 2


def projection_month_label(year: int, month: int) -> str:
    return f"{MONTH_PT[month]}/{year % 100:02d}"


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
