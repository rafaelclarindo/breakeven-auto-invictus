#!/usr/bin/env python3
"""Monta config e-commerce a partir do Growth Pack.

Metodologia idêntica ao inside sales (build_growthpack_inside_sales_config.py):
  - Baseline M1 = mediana dos últimos 3 meses por etapa
  - Tetos = max(mediana 3M, baseline M1) × 1,10, cap 95%
  - CPS de projeção = mediana dos últimos 3 meses (Investimento/Sessões)

O que muda é o funil:
  E-commerce: Sessões → View item → Add to cart → Checkout → Purchase
  Inside sales: Impressões → Cliques → Leads → MQL → SQL → Vendas

Perfis suportados:
  - bublu: GP All Bling, datetime L2, sessões L17, pedidos L39, vendas L41, receita L42
  - alumtech: GP Oxxy Motos 3.0 marketplace, datetime L2, visitas L15, compras L20, receita L22
"""
from __future__ import annotations

import argparse
import json
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any

from growthpack_sheets_reader import (
    extract_spreadsheet_id,
    find_acompanhamento_mensal_sheet,
    load_google_credentials,
    open_growthpack_worksheet,
)
from breakeven_projection import (
    PROJECTION_END_YEAR,
    build_impression_traceability,
    projection_month_count,
    select_cpi_baseline_months,
    select_projection_baseline_months,
)
from strategy_review_fields import MRR_SOURCE, resolve_mrr_from_manifest

MAX_CONVERSION_RATE = 0.95
MIN_COST_PER_SESSION = 0.01
PROJECTION_BASELINE_MONTHS = 3
STAGE_CEILING_HEADROOM = 1.10

MONTH_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}
MONTH_NAME_PT = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}

# 5 etapas rastreadas e projetadas (paralelo exato ao IS builder).
# Usam diretamente os nomes que o generate_breakeven.py espera nos cenários.
# Etapas intermediárias não listadas aqui ficam em 1.0 (add_view_cart,
# checkout_shipping, payment_order) — ver scenario_from_stage_advances.
FUNNEL_STAGE_KEYS = (
    "session_view",       # Sessões → View item
    "view_add",           # View item → Add to cart
    "viewcart_checkout",  # Add to cart → Begin checkout
    "shipping_payment",   # Begin checkout → Purchase
    "order_sale",         # Purchase → Sale (D2C: quase sempre 1.0)
)

# Num/Den default para GP com GA4 completo.
# Perfis com GP simplificado definem `stage_rate_num_den_overrides`
# (None = pass-through fixo em 1.0, sem projeção).
STAGE_RATE_NUM_DEN: dict[str, tuple[str, str]] = {
    "session_view": ("view_item", "sessions"),
    "view_add": ("add_to_cart", "view_item"),
    "viewcart_checkout": ("begin_checkout", "add_to_cart"),
    "shipping_payment": ("purchase", "begin_checkout"),
    "order_sale": ("purchase", "purchase"),  # 1.0 sempre para D2C
}

# E-commerce: taxas GA4 respondem mais devagar que IS (conversões são mais estáveis)
SCENARIO_STAGE_MONTHLY_ADVANCE: dict[str, dict[str, float]] = {
    "Otimista": {
        "session_view": 0.05,
        "view_add": 0.03,
        "viewcart_checkout": 0.03,
        "shipping_payment": 0.02,
        "order_sale": 0.01,
    },
    "Realista": {
        "session_view": 0.03,
        "view_add": 0.02,
        "viewcart_checkout": 0.02,
        "shipping_payment": 0.015,
        "order_sale": 0.005,
    },
    "Pessimista": {
        "session_view": 0.015,
        "view_add": 0.01,
        "viewcart_checkout": 0.01,
        "shipping_payment": 0.01,
        "order_sale": 0.0,
    },
}

STAGE_RATE_CEILINGS_FALLBACK: dict[str, float] = {
    "session_view": 0.80,
    "view_add": 0.20,
    "viewcart_checkout": 0.70,
    "shipping_payment": 0.80,
    "order_sale": 0.95,
}

# Campos mínimos para mês válido (todos os perfis devem ter esses campos)
FUNNEL_REQUIRED = ("media", "sessions", "purchase", "revenue")

# ---------------------------------------------------------------------------
# Perfis de GP e-commerce
# ---------------------------------------------------------------------------
# Cada perfil define:
#   rows         : mapeamento campo → linha do GP
#   pass_through : campos não no GP, derivados de outro campo (value = source key)
#   stage_rate_num_den_overrides: substitui o STAGE_RATE_NUM_DEN global por etapa;
#                  None = etapa fixa em 1.0 (sem projeção, sem teto calculado)
#   date_mode    : "datetime_row" | "year_month_text"
#   media_row    : para gate.md
#   revenue_row  : para gate.md
#   funnel_mapping / funnel_note: documentação
# ---------------------------------------------------------------------------
GP_PROFILES: dict[str, dict[str, Any]] = {
    "bublu": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 9,
            "sessions": 17,
            "add_to_cart": 39,   # "Pedidos All Bling" — equivalente a add-to-cart
            "purchase": 41,      # "Vendas All Bling"
            "revenue": 42,       # "Faturamento All Bling"
        },
        # view_item e begin_checkout não têm linha própria: derivados por pass_through
        "pass_through": {
            "view_item": "sessions",    # sem rastreamento view_item → igual sessões
            "begin_checkout": "add_to_cart",
            "add_payment_info": "purchase",
        },
        # Sobrescreve num/den para as 2 etapas com dados reais no GP
        "stage_rate_num_den_overrides": {
            "session_view": None,                                  # sem view_item real → 1.0
            "view_add": ("add_to_cart", "sessions"),               # pedidos/sessões
            "viewcart_checkout": None,                             # sem checkout real → 1.0
            "shipping_payment": ("purchase", "add_to_cart"),       # vendas/pedidos
            "order_sale": None,                                    # D2C → 1.0
        },
        "media_row": 9,
        "revenue_row": 42,
        "funnel_mapping": (
            "Investimento linha 9 · Sessões linha 17 · "
            "Pedidos linha 39 (≈ add-to-cart) · "
            "Vendas linha 41 · Faturamento All Bling linha 42"
        ),
        "funnel_note": (
            "GP Bublu simplificado: 2 taxas reais (pedidos/sessões e vendas/pedidos). "
            "Demais etapas GA4 sem rastreamento → pass-through 1,0."
        ),
    },
    "alumtech": {
        "sheet": "auto",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 6,
            "sessions": 15,       # Visitas plataforma
            "add_to_cart": 20,    # Compras plataforma (≈ pedidos)
            "purchase": 20,       # Marketplace: compra = pedido (sem checkout separado)
            "revenue": 22,        # Receita faturada plataforma
        },
        "pass_through": {
            "view_item": "sessions",
            "begin_checkout": "add_to_cart",
            "add_payment_info": "purchase",
        },
        "stage_rate_num_den_overrides": {
            "session_view": None,
            "view_add": ("add_to_cart", "sessions"),
            "viewcart_checkout": None,
            "shipping_payment": None,
            "order_sale": None,
        },
        "media_row": 6,
        "revenue_row": 22,
        "funnel_mapping": (
            "Investimento linha 6 · Visitas linha 15 · "
            "Compras plataforma linha 20 · Receita plataforma linha 22"
        ),
        "funnel_note": (
            "GP marketplace Oxxy Motos — 1 taxa real (compras/visitas). "
            "Checkout e purchase colapsados na linha 20 → pass-through 1,0."
        ),
    },
    "dalpack": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 9,
            "sessions": 17,
            "add_to_cart": 25,   # Pedidos (consolidado Bling)
            "purchase": 27,      # Vendas
            "revenue": 28,       # Faturamento
        },
        "pass_through": {
            "view_item": "sessions",
            "begin_checkout": "add_to_cart",
            "add_payment_info": "purchase",
        },
        "stage_rate_num_den_overrides": {
            "session_view": None,
            "view_add": ("add_to_cart", "sessions"),
            "viewcart_checkout": None,
            "shipping_payment": ("purchase", "add_to_cart"),
            "order_sale": None,
        },
        "media_row": 9,
        "revenue_row": 28,
        "funnel_mapping": (
            "Investimento linha 9 · Sessões Gerais linha 17 · "
            "Pedidos linha 25 · Vendas linha 27 · Faturamento linha 28"
        ),
        "funnel_note": (
            "GP Dalpack simplificado (6.0 Acompanhamento Mensal): 2 taxas reais "
            "(pedidos/sessões e vendas/pedidos). Etapas GA4 intermediárias sem linha "
            "própria → pass-through 1,0."
        ),
    },
    # Adicionar novos perfis e-commerce aqui seguindo o padrão acima.
    # Exemplo para GP com GA4 completo (Sessões L5, View item L6, Add cart L7, Checkout L8, Purchase L9):
    # "exemplo_ga4": {
    #     "sheet": "6.0 Acompanhamento Mensal",
    #     "date_mode": "datetime_row",
    #     "rows": {
    #         "date": 2, "media": 4,
    #         "sessions": 5, "view_item": 6, "add_to_cart": 7,
    #         "begin_checkout": 8, "purchase": 9, "revenue": 10,
    #     },
    #     "pass_through": {},
    #     "stage_rate_num_den_overrides": {},  # vazio = usa STAGE_RATE_NUM_DEN global
    #     "media_row": 4, "revenue_row": 10,
    #     "funnel_mapping": "...", "funnel_note": "...",
    # },
}


# ---------------------------------------------------------------------------
# Helpers (idênticos ao IS builder)
# ---------------------------------------------------------------------------

def norm_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.strip().lower()


def parse_num(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        return 0.0
    text = str(value).strip()
    if not text or text.startswith("#"):
        return 0.0
    text = text.replace("R$", "").replace("\xa0", " ").strip()
    if "," in text and text.count(",") == 1:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def div(a: float, b: float) -> float:
    return a / b if b else 0.0


def cap_rate(value: float) -> float:
    return min(MAX_CONVERSION_RATE, value)


def recent_funnel_months(months: list[dict[str, Any]], count: int = PROJECTION_BASELINE_MONTHS) -> list[dict[str, Any]]:
    if not months:
        return []
    return months[-count:] if len(months) >= count else list(months)


def median_funnel_volume(months: list[dict[str, Any]], key: str) -> float:
    samples = [float(month.get(key, 0) or 0) for month in months if float(month.get(key, 0) or 0) > 0]
    return round(median(samples), 2) if samples else 0.0


def build_baseline_funnel_volumes_ecommerce(months: list[dict[str, Any]]) -> dict[str, float]:
    """Medianas 3M — ponto de partida M1 (chaves bridge compatíveis com col. E do gerador)."""
    sessions = median_funnel_volume(months, "sessions")
    view_item = median_funnel_volume(months, "view_item")
    add_to_cart = median_funnel_volume(months, "add_to_cart")
    purchase = median_funnel_volume(months, "purchase")
    return {
        "sessions": sessions,
        "view_item": view_item,
        "add_to_cart": add_to_cart,
        "purchase": purchase,
        "impressions": sessions,
        "clicks": view_item,
        "leads": add_to_cart,
        "mqls": median_funnel_volume(months, "view_cart") or add_to_cart,
        "sqls": median_funnel_volume(months, "begin_checkout") or add_to_cart,
        "sales": purchase,
    }


def median_stage_rate(months: list[dict[str, Any]], numerator_key: str, denominator_key: str) -> float:
    """Mediana da taxa de uma etapa — robusta a outliers (Black Friday, pico de campanha)."""
    samples = [
        div(m[numerator_key], m[denominator_key])
        for m in months
        if m.get(denominator_key, 0) > 0
    ]
    return median(samples) if samples else 0.0


def stage_ceilings_from_history(
    rate_months: list[dict[str, Any]],
    baseline_rates: dict[str, float],
    num_den: dict[str, tuple[str, str]],
    headroom: float = STAGE_CEILING_HEADROOM,
) -> dict[str, float]:
    """Teto por etapa = max(mediana 3M, baseline M1) × folga, cap 95%.

    Mesma lógica do IS builder. `num_den` contém apenas as etapas com dados reais
    (excluindo pass-through). Etapas ausentes do num_den recebem ceiling = 1.0.
    """
    ceilings: dict[str, float] = {}
    for key in FUNNEL_STAGE_KEYS:
        if key not in num_den:
            # Etapa pass-through (taxa fixa 1.0 — sem ceiling calculado)
            ceilings[key] = 1.0
            continue
        num, den = num_den[key]
        median_rate = median_stage_rate(rate_months, num, den)
        baseline = baseline_rates.get(key, 0.0)
        base = max(median_rate, baseline)
        if base > 0:
            ceiling = base * headroom
        else:
            ceiling = STAGE_RATE_CEILINGS_FALLBACK.get(key, MAX_CONVERSION_RATE)
        ceilings[key] = round(min(MAX_CONVERSION_RATE, ceiling), 6)
    return ceilings


def gradual(start: float, end: float, months: int = 7) -> list[float]:
    if months <= 1:
        return [cap_rate(end)]
    return [cap_rate(start + (end - start) * i / (months - 1)) for i in range(months)]


def gradual_linear(start: float, end: float, months: int = 7) -> list[float]:
    if months <= 1:
        return [end]
    return [start + (end - start) * i / (months - 1) for i in range(months)]


def month_label(dt: datetime) -> str:
    return f"{MONTH_PT[dt.month]}/{dt.year % 100:02d}"


def label_from_year_month(year: int, month_num: int) -> str:
    return f"{MONTH_PT[month_num]}/{year % 100:02d}"


def coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, (int, float)):
        serial = float(value)
        if 30_000 <= serial <= 60_000:
            return datetime(1899, 12, 30) + timedelta(days=serial)
        return None
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def label_sort_key(label: str) -> tuple[int, int]:
    month_part, year_part = label.split("/")
    year = 2000 + int(year_part) if len(year_part) == 2 else int(year_part)
    month_rev = {abbr.lower(): num for num, abbr in MONTH_PT.items()}
    return year, month_rev.get(month_part.lower()[:3], 0)


def filter_months_from(months: list[dict[str, Any]], from_label: str) -> list[dict[str, Any]]:
    cutoff = label_sort_key(from_label)
    return [m for m in months if label_sort_key(m["label"]) >= cutoff]


# ---------------------------------------------------------------------------
# Leitura do GP (profile-driven)
# ---------------------------------------------------------------------------

def parse_month_item(ws, profile: dict[str, Any], col: int) -> dict[str, Any] | None:
    rows = profile["rows"]
    pass_through = profile.get("pass_through", {})

    if profile["date_mode"] == "datetime_row":
        dt = coerce_datetime(ws.cell(rows["date"], col).value)
        if not dt:
            return None
        label = month_label(dt)
    else:
        year = parse_num(ws.cell(rows.get("year", 1), col).value)
        month_raw = norm_text(ws.cell(rows.get("month_name", 4), col).value)
        month_num = MONTH_NAME_PT.get(month_raw)
        if not (year and month_num):
            return None
        label = label_from_year_month(int(year), int(month_num))

    item: dict[str, Any] = {"label": label}
    for field, row in rows.items():
        if field in ("date", "year", "month_name"):
            continue
        item[field] = parse_num(ws.cell(row, col).value)

    # Campos derivados por pass-through (etapas GA4 sem linha própria no GP)
    for field, source in pass_through.items():
        item[field] = item.get(source, 0.0)

    return item


def read_funnel_months(ws, profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Meses com campos obrigatórios preenchidos (media + purchase + revenue + sessions)."""
    months = []
    for col in range(2, ws.max_column + 1):
        item = parse_month_item(ws, profile, col)
        if item and all(item.get(k, 0) > 0 for k in FUNNEL_REQUIRED):
            months.append(item)
    return months


def read_investment_months(ws, profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Todos os meses com investimento > 0 — inclui pré-funil."""
    months = []
    for col in range(2, ws.max_column + 1):
        item = parse_month_item(ws, profile, col)
        if item and item.get("media", 0) > 0:
            months.append(item)
    return months


def resolve_growthpack_sheet_name(project_folder: Path, profile: dict[str, Any]) -> str:
    requested = profile.get("sheet") or "6.0 Acompanhamento Mensal"
    if requested != "auto":
        return requested
    manifest_path = project_folder / "source" / "manifest-entry.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    spreadsheet_id = extract_spreadsheet_id(manifest.get("growthpack_updated_link"))
    if not spreadsheet_id:
        raise ValueError(f"Link do Growth Pack ausente em {manifest_path}.")
    creds = load_google_credentials()
    return find_acompanhamento_mensal_sheet(creds, spreadsheet_id)


def resolve_stage_num_den(profile: dict[str, Any]) -> dict[str, tuple[str, str]]:
    """Retorna o mapeamento num/den efetivo, excluindo etapas pass-through (None)."""
    overrides = profile.get("stage_rate_num_den_overrides", {})
    if not overrides:
        # GA4 completo: usa todos os defaults
        return dict(STAGE_RATE_NUM_DEN)
    result: dict[str, tuple[str, str]] = {}
    for key in FUNNEL_STAGE_KEYS:
        if key in overrides:
            value = overrides[key]
            if value is not None:
                result[key] = value
            # None → etapa pass-through, não entra no dict
        else:
            result[key] = STAGE_RATE_NUM_DEN[key]
    return result


def format_stage_advances(advances: dict[str, float]) -> str:
    labels = {
        "session_view": "Sessão→View",
        "view_add": "View→Add",
        "viewcart_checkout": "Add→Checkout",
        "shipping_payment": "Checkout→Purchase",
        "order_sale": "Purchase→Sale",
    }
    return "; ".join(f"{labels[k]} {advances[k] * 100:g}%/mês" for k in FUNNEL_STAGE_KEYS)


# ---------------------------------------------------------------------------
# Geração do config
# ---------------------------------------------------------------------------

def revenue_from_funnel(
    media: float,
    *,
    session_view: float,
    view_add: float,
    viewcart_checkout: float,
    shipping_payment: float,
    order_sale: float,
    ticket: float,
    cps: float,
) -> float:
    """Receita projetada a partir do funil e-commerce forward."""
    sessions = media / cps if cps else 0.0
    view_item = sessions * session_view
    add_cart = view_item * view_add
    checkout = add_cart * viewcart_checkout
    purchase = checkout * shipping_payment
    sale = purchase * order_sale
    return round(sale * ticket, 2)


def build_config(
    *,
    project_folder: Path,
    profile_name: str,
    lt_months: int = 0,
    seasonal_context: str = "",
    output: Path | None = None,
    reference_date: date | None = None,
    gp_source: str = "online",
    from_label: str = "",
) -> Path:
    profile = GP_PROFILES[profile_name]
    manifest = json.loads((project_folder / "source" / "manifest-entry.json").read_text(encoding="utf-8"))
    sheet_name = resolve_growthpack_sheet_name(project_folder, profile)
    ws, gp_source_used = open_growthpack_worksheet(project_folder, sheet_name, source=gp_source)

    monthly_fee = parse_num(manifest["fee"])
    monthly_media = parse_num(manifest["media_planned"])
    margin = parse_num(manifest["margin_pct"]) / 100

    funnel_months = read_funnel_months(ws, profile)
    if not funnel_months:
        raise ValueError(f"Nenhum mês com funil completo em {sheet_name!r} (perfil {profile_name}).")

    investment_months = read_investment_months(ws, profile)
    if not investment_months:
        raise ValueError(f"Nenhum mês com investimento em {sheet_name!r} (perfil {profile_name}).")

    if from_label:
        funnel_months = filter_months_from(funnel_months, from_label)
        investment_months = filter_months_from(investment_months, from_label)
        if not investment_months:
            raise ValueError(f"Nenhum mês após {from_label} em {sheet_name!r}.")

    if lt_months > 0:
        funnel_months = funnel_months[-lt_months:]
        first_label = funnel_months[0]["label"]
        investment_months = [m for m in investment_months if label_sort_key(m["label"]) >= label_sort_key(first_label)] or funnel_months

    months = funnel_months
    current = months[-1]
    previous = months[-2] if len(months) >= 2 else current

    # MRR (opt-in, quase sempre off para e-commerce D2C)
    tm_recurrence_months, tm_recurrence_raw = resolve_mrr_from_manifest(manifest)

    # Ticket médio — mediana de receita/purchase no histórico
    ticket_samples = [
        div(m["revenue"], m["purchase"])
        for m in investment_months
        if m.get("purchase", 0) > 0 and m.get("revenue", 0) > 0
    ] or [div(current["revenue"], current["purchase"])]
    ticket_monthly = round(median(ticket_samples), 2) if ticket_samples else round(div(current["revenue"], current["purchase"]), 2)
    projection_ticket = ticket_monthly * tm_recurrence_months if tm_recurrence_months else ticket_monthly

    # CPS = Investimento/Sessões (não impressões — e-commerce)
    current_cps = div(current["media"], current["sessions"])
    min_cps = max(MIN_COST_PER_SESSION, current_cps * 0.85)

    # Janela 3M para projeção (baseline, tetos, CPS)
    ref = reference_date or date.today()
    proj_months = projection_month_count(ref, end_year=PROJECTION_END_YEAR)

    # Janela para mediana de taxas/CPS (histórico curto → todos os meses fechados)
    projection_baseline_months = select_projection_baseline_months(
        months,
        baseline_window=PROJECTION_BASELINE_MONTHS,
    )
    projection_baseline_labels = [m["label"] for m in projection_baseline_months]
    baseline_window_label = (
        f"mediana {len(projection_baseline_months)}M ({' · '.join(projection_baseline_labels)})"
        if projection_baseline_labels
        else f"mediana {PROJECTION_BASELINE_MONTHS}M"
    )
    cpi_baseline_months = select_cpi_baseline_months(
        investment_months,
        traffic_key="sessions",
        baseline_window=PROJECTION_BASELINE_MONTHS,
    )
    cpi_baseline_labels = [month["label"] for month in cpi_baseline_months]
    cpi_window_label = (
        f"mediana {len(cpi_baseline_months)}M ({' · '.join(cpi_baseline_labels)})"
        if cpi_baseline_labels
        else f"mediana {PROJECTION_BASELINE_MONTHS}M"
    )

    # CPS de projeção = MEDIANA dos últimos 3M com sessões (inclui pré-funil se houver mídia+sessões)
    baseline_cps_samples = [
        div(m["media"], m["sessions"])
        for m in cpi_baseline_months
        if m.get("sessions", 0) > 0
    ]
    cps_samples_all = [div(m["media"], m["sessions"]) for m in months if m.get("sessions", 0) > 0]
    median_cps = median(cps_samples_all) if cps_samples_all else current_cps
    projection_cps = median(baseline_cps_samples) if baseline_cps_samples else median_cps

    gp_media_projection = [round(monthly_media, 2)] * proj_months
    gp_cps_projection = [round(projection_cps, 8)] * proj_months

    # Num/den efetivos para este perfil (sem as etapas pass-through)
    active_num_den = resolve_stage_num_den(profile)

    # Baseline M1 = MEDIANA dos últimos 3M por etapa (não média).
    # Taxas DERIVADAS dos volumes medianos (razão das medianas), NÃO mediana das razões mensais.
    # Mediana de razões ≠ razão de medianas: usar a primeira fazia o funil não fechar (volume ×
    # taxa ≠ próximo volume). median_funnel_volume é a mesma base de build_baseline_funnel_volumes
    # → o funil fecha por construção. Decisão Rafael 2026-06-26.
    baseline_rates: dict[str, float] = {}
    for key in FUNNEL_STAGE_KEYS:
        if key in active_num_den:
            num, den = active_num_den[key]
            _raw = div(
                median_funnel_volume(projection_baseline_months, num),
                median_funnel_volume(projection_baseline_months, den),
            )
            baseline_rates[key] = _raw if _raw > 1.0 else cap_rate(_raw)  # >1 = amplificação orgânica
        else:
            baseline_rates[key] = 1.0  # pass-through

    # Tetos de saturação: max(mediana 3M, baseline M1) × 1,10
    stage_ceilings = stage_ceilings_from_history(projection_baseline_months, baseline_rates, active_num_den)

    accumulated_revenue = sum(m["revenue"] for m in investment_months)
    accumulated_media = sum(m["media"] for m in investment_months)
    pre_funnel_count = len(investment_months) - len(funnel_months)
    funnel_lt_period = f"{funnel_months[0]['label']} a {funnel_months[-1]['label']}"
    impression_traceability = build_impression_traceability(
        funnel_months=funnel_months,
        investment_months=investment_months,
        funnel_lt_period=funnel_lt_period,
        projection_media=round(monthly_media, 2),
        projection_cps=projection_cps,
        traffic_key="sessions",
        cpi_baseline_labels=cpi_baseline_labels,
    )

    # --- Funções de projeção compostas (mesmo padrão IS) ---

    def compound_rate_series(start_val: float, monthly_advance_pct: float, ceiling: float = MAX_CONVERSION_RATE) -> list[float]:
        cap = min(MAX_CONVERSION_RATE, ceiling)
        values = [min(cap, start_val)]
        cur = values[0]
        for _ in range(1, proj_months):
            cur = min(cap, cur * (1 + monthly_advance_pct))
            values.append(cur)
        return values

    def rate_series(rate_key: str, monthly_advance_pct: float) -> list[float]:
        if baseline_rates[rate_key] >= 1.0 or rate_key not in active_num_den:
            return [1.0] * proj_months  # pass-through fixo
        return compound_rate_series(
            baseline_rates[rate_key],
            monthly_advance_pct,
            ceiling=stage_ceilings[rate_key],
        )

    def scenario_ticket(idx: int) -> float:
        if tm_recurrence_months:
            return round(ticket_monthly, 2)
        return round(ticket_monthly * (1 + 0.005 * idx), 2)

    def scenario_from_stage_advances(stage_advances: dict[str, float], color: str) -> dict:
        rates = {key: rate_series(key, stage_advances[key]) for key in FUNNEL_STAGE_KEYS}
        media_series = list(gp_media_projection)
        tickets = [scenario_ticket(idx) for idx in range(proj_months)]
        revenue = [
            revenue_from_funnel(
                media_series[idx],
                session_view=rates["session_view"][idx],
                view_add=rates["view_add"][idx],
                viewcart_checkout=rates["viewcart_checkout"][idx],
                shipping_payment=rates["shipping_payment"][idx],
                order_sale=rates["order_sale"][idx],
                ticket=tickets[idx] * (tm_recurrence_months or 1),
                cps=gp_cps_projection[idx],
            )
            for idx in range(proj_months)
        ]
        return {
            "media": media_series,
            "revenue": revenue,
            "ticket": tickets,
            # Mapeamento para as chaves internas do generate_breakeven.py (e-commerce)
            "session_view": rates["session_view"],
            "view_add": rates["view_add"],
            "add_view_cart": [1.0] * proj_months,       # pass-through (view_cart ≈ add_to_cart)
            "viewcart_checkout": rates["viewcart_checkout"],
            "checkout_shipping": [1.0] * proj_months,   # pass-through (shipping ≈ checkout)
            "shipping_payment": rates["shipping_payment"],
            "payment_order": [1.0] * proj_months,       # pass-through
            "order_sale": rates["order_sale"],
            "tab_color": color,
        }

    def scenario_media_v4(stage_advances: dict[str, float], color: str) -> dict:
        rates = {key: rate_series(key, stage_advances[key]) for key in FUNNEL_STAGE_KEYS}
        media_series = [round(v, 2) for v in gradual_linear(current["media"], monthly_media, proj_months)]
        tickets = [scenario_ticket(idx) for idx in range(proj_months)]
        revenue = [
            revenue_from_funnel(
                media_series[idx],
                session_view=rates["session_view"][idx],
                view_add=rates["view_add"][idx],
                viewcart_checkout=rates["viewcart_checkout"][idx],
                shipping_payment=rates["shipping_payment"][idx],
                order_sale=rates["order_sale"][idx],
                ticket=tickets[idx] * (tm_recurrence_months or 1),
                cps=gp_cps_projection[idx],
            )
            for idx in range(proj_months)
        ]
        sc = scenario_from_stage_advances(stage_advances, color)
        sc["media"] = media_series
        sc["revenue"] = revenue
        sc["ticket"] = tickets
        sc["tab_color"] = color
        sc["editable_media"] = True
        sc["media_ramp"] = {
            "from": round(current["media"], 2),
            "to": round(monthly_media, 2),
            "months": proj_months,
            "mode": "linear",
            "monthly_step": round((monthly_media - current["media"]) / max(1, proj_months - 1), 2),
            "note": (
                f"Rampa linear até {PROJECTION_END_YEAR}: M1 = investimento {current['label']} (GP); "
                f"último mês = mídia Flow (SR)."
            ),
        }
        return sc

    realista_advances = SCENARIO_STAGE_MONTHLY_ADVANCE["Realista"]
    realista_scenario = scenario_from_stage_advances(realista_advances, "#5B9BD5")
    realista_rates = {key: rate_series(key, realista_advances[key]) for key in FUNNEL_STAGE_KEYS}
    breakeven_competence = (monthly_fee + monthly_media) / margin
    baseline_funnel_volumes = build_baseline_funnel_volumes_ecommerce(projection_baseline_months)
    seasonal = seasonal_context.strip()

    # current_funnel usa as chaves internas do gerador (e-commerce)
    def funnel_dict(m: dict[str, Any]) -> dict[str, Any]:
        return {
            "sessions": m["sessions"],
            "page_view": m["sessions"],
            "view_item": m.get("view_item", m["sessions"]),
            "add_to_cart": m.get("add_to_cart", m["purchase"]),
            "view_cart": m.get("add_to_cart", m["purchase"]),
            "begin_checkout": m.get("begin_checkout", m.get("add_to_cart", m["purchase"])),
            "add_shipping_info": m.get("begin_checkout", m.get("add_to_cart", m["purchase"])),
            "add_payment_info": m.get("add_payment_info", m["purchase"]),
            "orders": m.get("add_to_cart", m["purchase"]),
            "sales": m["purchase"],
            "purchase": m["purchase"],
            "revenue": m["revenue"],
            "media": m["media"],
        }

    source_months = [
        [m["label"], monthly_fee, m["media"], m["sessions"], m.get("add_to_cart", m["purchase"]), m["purchase"], m["revenue"]]
        for m in investment_months
    ]

    def benchmark_row(m: dict[str, Any]) -> list[Any]:
        """9 colunas GA4 exigidas por generate_breakeven.py (após label)."""
        fd = funnel_dict(m)
        return [
            m["label"],
            fd["sessions"],
            fd["view_item"],
            fd["add_to_cart"],
            fd["view_cart"],
            fd["begin_checkout"],
            fd["add_shipping_info"],
            fd["add_payment_info"],
            fd["purchase"],
        ]

    benchmark_months = [benchmark_row(m) for m in funnel_months]

    # Stages com dados reais (para documentação)
    active_stages_label = ", ".join(
        k for k in FUNNEL_STAGE_KEYS if k in active_num_den
    ) or "nenhuma (funil sem dados intermediários)"

    config = {
        "client": manifest["name"],
        "project_model": "E-commerce D2C",
        "gp_profile": profile_name,
        "projection_rules": {
            "max_conversion_rate": MAX_CONVERSION_RATE,
            "min_cost_per_impression": min_cps,
            "media_lever_after_monthly_breakeven": False,
        },
        "media_projection_mode": "growthpack_monthly",
        "gp_cps_projection": [round(v, 8) for v in gp_cps_projection],
        "gp_media_projection": gp_media_projection,
        "projection_end_year": PROJECTION_END_YEAR,
        "projection_month_count": proj_months,
        "projection_reference_date": ref.isoformat(),
        "projection_media_flow": round(monthly_media, 2),
        "projection_cps_baseline": round(projection_cps, 8),
        "projection_cps_median": round(median_cps, 8),
        "impression_traceability": impression_traceability,
        "projection_baseline_months": PROJECTION_BASELINE_MONTHS,
        "projection_baseline_labels": projection_baseline_labels,
        "projection_cpi_baseline_labels": cpi_baseline_labels,
        "funnel_rate_baseline": "median_last_3",
        "funnel_rate_baseline_label": baseline_window_label,
        "current_period": f"{current['label']} fechado",
        "lt_period": f"{investment_months[0]['label']} a {investment_months[-1]['label']}",
        "funnel_lt_period": f"{funnel_months[0]['label']} a {funnel_months[-1]['label']}",
        "investment_months_count": len(investment_months),
        "funnel_months_count": len(funnel_months),
        "margin": margin,
        "monthly_fee": monthly_fee,
        "monthly_media": monthly_media,
        "ticket_monthly": round(ticket_monthly, 2),
        "projection_ticket": round(projection_ticket, 2),
        "baseline_funnel_rates": {k: round(v, 8) for k, v in baseline_rates.items()},
        "baseline_funnel_volumes": baseline_funnel_volumes,
        "projection_volume_mode": "baseline_median_volumes",
        "projection_baseline_sales_avg": baseline_funnel_volumes["purchase"],
        "stage_rate_ceilings": {k: stage_ceilings[k] for k in FUNNEL_STAGE_KEYS},
        "stage_rate_ceilings_basis": f"max(mediana últimos 3M, baseline M1) × {STAGE_CEILING_HEADROOM:g} (cap {MAX_CONVERSION_RATE:g})",
        "scenario_stage_monthly_advance": SCENARIO_STAGE_MONTHLY_ADVANCE,
        "scenario_rate_advance_mode": "compound_monthly_by_stage_saturating",
        "source_mapping": {
            "fee": f"Strategy Review / Flow — fee R$ {monthly_fee:,.2f}",
            "media": f"Growth Pack > {sheet_name} > linha {profile['media_row']} Investimento",
            "revenue": f"Growth Pack > {sheet_name} > linha {profile['revenue_row']} Receita",
            "funnel": profile["funnel_mapping"],
        },
        "source_months": source_months,
        "benchmark_months": benchmark_months,
        "current_funnel": funnel_dict(current),
        "previous_month_funnel": funnel_dict(previous),
        "previous_month_label": previous["label"],
        "last_month_funnel_label": current["label"],
        "minimum_scenario": {
            "revenue": list(realista_scenario["revenue"]),
            "media": list(gp_media_projection),
            "session_view": realista_rates["session_view"],
            "view_add": realista_rates["view_add"],
            "add_view_cart": [1.0] * proj_months,
            "viewcart_checkout": realista_rates["viewcart_checkout"],
            "shipping_payment": realista_rates["shipping_payment"],
            "add_cart_purchase": compound_rate_series(
                cap_rate(div(current["purchase"], current.get("add_to_cart", current["purchase"]))),
                realista_advances["shipping_payment"],
            ),
            "approval_target": 1.0,
            "order_sale": realista_rates["order_sale"],
        },
        "scenarios": {
            "Pessimista": scenario_from_stage_advances(SCENARIO_STAGE_MONTHLY_ADVANCE["Pessimista"], "#C55A11"),
            "Realista": realista_scenario,
            "Otimista": scenario_from_stage_advances(SCENARIO_STAGE_MONTHLY_ADVANCE["Otimista"], "#70AD47"),
            "Mídia V4": scenario_media_v4(SCENARIO_STAGE_MONTHLY_ADVANCE["Realista"], "#7030A0"),
        },
        "scenario_sheet_order": ["Pessimista", "Realista", "Otimista", "Mídia V4"],
        "contract_from_label": from_label or None,
        "context": {
            "product": f"{manifest['name']} — e-commerce D2C",
            "phase": f"Strategy Review — Growth Pack e-commerce (perfil {profile_name})",
            "main_risk": f"Faturamento abaixo do breakeven da competência (R$ {breakeven_competence:,.2f}).",
            "seasonal": seasonal or None,
            "diagnosis": [
                *(
                    [f"Histórico contado a partir de {from_label} (início operacional)."]
                    if from_label else []
                ),
                f"Investimento GP: {len(investment_months)} meses ({investment_months[0]['label']}–{investment_months[-1]['label']}).",
                f"Funil completo: {len(funnel_months)} meses ({funnel_months[0]['label']}–{funnel_months[-1]['label']}).",
                *(
                    [f"Inclui {pre_funnel_count} meses pré-funil no investimento acumulado."]
                    if pre_funnel_count > 0 else []
                ),
                f"Faturamento acumulado (GP): R$ {accumulated_revenue:,.2f}.",
                f"Investimento acumulado (GP): R$ {accumulated_media:,.2f}.",
                f"Breakeven competência: R$ {breakeven_competence:,.2f} (fee R$ {monthly_fee:,.0f} + mídia Flow R$ {monthly_media:,.0f} / margem {margin:.0%}).",
                f"CPS de projeção: {cpi_window_label} R$ {projection_cps:.4f}/sessão. Taxas funil: {baseline_window_label}.",
                impression_traceability["projection_note"],
                f"Etapas com dados reais no GP (perfil {profile_name}): {active_stages_label}. Demais etapas = pass-through 1,0.",
                f"Taxas funil: baseline mediana {PROJECTION_BASELINE_MONTHS}M + evolução mensal composta — "
                f"Pessimista ({format_stage_advances(SCENARIO_STAGE_MONTHLY_ADVANCE['Pessimista'])}); "
                f"Realista ({format_stage_advances(SCENARIO_STAGE_MONTHLY_ADVANCE['Realista'])}); "
                f"Otimista ({format_stage_advances(SCENARIO_STAGE_MONTHLY_ADVANCE['Otimista'])}).",
                f"Último mês ({current['label']}): investimento R$ {current['media']:,.0f}, "
                f"sessões {current['sessions']:.0f}, purchase {current['purchase']:.0f}, "
                f"faturamento R$ {current['revenue']:,.2f}.",
                profile["funnel_note"],
            ],
            "actions": [
                "Melhorar taxa sessions→add_to_cart (CTR de produto/landing)",
                "Melhorar checkout → purchase (abandonos de carrinho, UX checkout)",
                "Validar tracking GA4 nas etapas intermediárias",
                "Alinhar campanhas ao calendário sazonal (SR col. P)",
            ],
        },
    }

    if seasonal:
        config["strategy_review_context"] = seasonal
    if tm_recurrence_months:
        config["tm_recurrence_months"] = tm_recurrence_months
        config["tm_recurrence_raw"] = tm_recurrence_raw
        config["tm_recurrence_source"] = MRR_SOURCE
        config["mrr_months"] = tm_recurrence_months
        config["mrr_raw"] = tm_recurrence_raw
        config["mrr_source"] = MRR_SOURCE

    out_path = output or project_folder / "config.json"
    out_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    gate = project_folder / "gate.md"
    gate.write_text(
        "\n".join([
            f"# Gate — {manifest['name']}",
            "",
            f"- Projeto: {manifest['name']}",
            "- Escopo: **E-commerce D2C** (funil Sessões→Purchase)",
            f"- Perfil GP: `{profile_name}`",
            f"- Growth Pack ({gp_source_used}): [{manifest['name']}]({manifest.get('growthpack_updated_link', '')})",
            f"- Investimento GP: {config['lt_period']} ({len(investment_months)} meses)",
            f"- Funil completo: {config['funnel_lt_period']} ({len(funnel_months)} meses)",
            f"- Faturamento acumulado: R$ {accumulated_revenue:,.2f}",
            f"- Investimento acumulado (GP): R$ {accumulated_media:,.2f}",
            f"- Projeção: {proj_months} meses até {PROJECTION_END_YEAR} · mídia Flow R$ {monthly_media:,.0f}/mês",
            f"- CPS projeção (mediana 3M): R$ {projection_cps:.4f}/sessão",
            f"- Fee competência: R$ {monthly_fee:,.2f}",
            f"- Mídia competência (Flow): R$ {monthly_media:,.2f}",
            f"- Margem: {margin:.0%}",
            f"- Breakeven competência: R$ {breakeven_competence:,.2f}",
            f"- Ticket GP (mediana): R$ {ticket_monthly:,.2f}",
            *(
                [f"- MRR (SR col. L): {tm_recurrence_raw} → LTV = ticket × {tm_recurrence_months} meses"]
                if tm_recurrence_months else ["- MRR: sem recorrência (SR col. L vazia)"]
            ),
            f"- Etapas rastreadas no GP: {active_stages_label}",
            "",
        ]),
        encoding="utf-8",
    )
    print(out_path)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera config e-commerce a partir do Growth Pack.")
    parser.add_argument("--project-folder", type=Path, required=True)
    parser.add_argument("--profile", required=True, choices=list(GP_PROFILES.keys()), help="Layout do GP")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--reference-date", type=lambda s: date.fromisoformat(s), default=None)
    parser.add_argument("--gp-source", choices=["online", "local", "auto"], default="online")
    parser.add_argument("--from-label", default="", help="Início do histórico (ex.: Jan/26)")
    parser.add_argument("--seasonal-context-file", type=Path, default=None)
    args = parser.parse_args()

    seasonal = ""
    if args.seasonal_context_file and args.seasonal_context_file.exists():
        seasonal = args.seasonal_context_file.read_text(encoding="utf-8").strip()

    manifest = json.loads((args.project_folder / "source" / "manifest-entry.json").read_text(encoding="utf-8"))
    lt_months = int(manifest.get("lt_months", 0) or 0)

    build_config(
        project_folder=args.project_folder,
        profile_name=args.profile,
        lt_months=lt_months,
        seasonal_context=seasonal,
        output=args.output,
        reference_date=args.reference_date,
        gp_source=args.gp_source,
        from_label=args.from_label,
    )


if __name__ == "__main__":
    main()
