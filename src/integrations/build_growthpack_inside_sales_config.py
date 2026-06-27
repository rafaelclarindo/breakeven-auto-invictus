#!/usr/bin/env python3
"""Monta config inside sales a partir do Growth Pack (layout 6.0 Acompanhamento Mensal).

Perfis suportados:
  - primeset / msys: datetime linha 2, funil linhas 7–17 (sem lead quali)
  - cdsi: ano linha 1 + mês texto linha 4, funil linhas 8–15 (Centro do Silicone)
"""
from __future__ import annotations

import argparse
import json
import re
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

MAX_CONVERSION_RATE = 0.95
MIN_COST_PER_IMPRESSION = 0.01
PROJECTION_BASELINE_MONTHS = 3
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
MONTH_NAME_PT = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "março": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
FUNNEL_REQUIRED = ("media", "impressions", "clicks", "leads", "mqls", "sqls", "sales", "revenue")
OPERATIONAL_FUNNEL_REQUIRED = ("media", "impressions", "clicks", "leads", "mqls", "sqls")
FUNNEL_STAGE_KEYS = (
    "impression_click",
    "click_lead",
    "lead_mql",
    "mql_sql",
    "sql_sale",
)
SCENARIO_STAGE_MONTHLY_ADVANCE: dict[str, dict[str, float]] = {
    "Otimista": {
        "impression_click": 0.07,
        "click_lead": 0.05,
        "lead_mql": 0.03,
        "mql_sql": 0.03,
        "sql_sale": 0.02,
    },
    "Realista": {
        "impression_click": 0.05,
        "click_lead": 0.03,
        "lead_mql": 0.02,
        "mql_sql": 0.02,
        "sql_sale": 0.01,
    },
    "Pessimista": {
        "impression_click": 0.03,
        "click_lead": 0.02,
        "lead_mql": 0.01,
        "mql_sql": 0.01,
        "sql_sale": 0.005,
    },
}
# Percentuais = crescimento mês a mês composto **por etapa** (saturação no teto por etapa).
# Teto realista por etapa do funil — substitui o cap único de 95% na projeção composta.
# Funil de verdade satura: cada taxa melhora mês a mês mas desacelera ao se aproximar
# do teto da sua etapa.
#
# BASE DO TETO (decisão Rafael 2026-06-24): a **projeção** (baseline M1 + tetos) usa SEMPRE os
# **últimos 3 meses** fechados do GrowthPack; o resto da análise (acumulado, bench, Dados Fonte,
# "Feito até o momento") continua usando TODO o período do contrato.
# Teto = mediana dos últimos 3 meses × folga (1,1) — mediana (não melhor mês) p/ não ancorar num
# outlier (Black Friday, oferta pontual). Como o baseline M1 (média dos 3) pode superar a mediana,
# o teto nunca cai abaixo do ponto de partida:  teto = max(mediana_3M, baseline_M1) × folga, cap 95%.
# Calculado em `stage_ceilings_from_history`. Editável nas Premissas C28:C32 (Sheets).
STAGE_CEILING_HEADROOM = 1.10  # folga sobre a mediana dos últimos 3 meses (ou o atual, se maior)
# Numerador/denominador de cada etapa para extrair a taxa do funil mensal.
STAGE_RATE_NUM_DEN: dict[str, tuple[str, str]] = {
    "impression_click": ("clicks", "impressions"),
    "click_lead": ("leads", "clicks"),
    "lead_mql": ("mqls", "leads"),
    "mql_sql": ("sqls", "mqls"),
    "sql_sale": ("sales", "sqls"),
}
# Fallback quando não há histórico de funil suficiente (mantém comportamento seguro).
STAGE_RATE_CEILINGS_FALLBACK: dict[str, float] = {
    "impression_click": 0.07,
    "click_lead": 0.05,
    "lead_mql": 0.40,
    "mql_sql": 0.70,
    "sql_sale": 0.70,
}
PRE_REVENUE_SQL_SALE_FALLBACK = 0.15
from strategy_review_fields import MRR_SOURCE, resolve_mrr_from_manifest


def format_stage_advances(advances: dict[str, float]) -> str:
    labels = {
        "impression_click": "Imp→Clique",
        "click_lead": "Clique→Lead",
        "lead_mql": "Lead→MQL",
        "mql_sql": "MQL→SQL",
        "sql_sale": "SQL→Venda",
    }
    return "; ".join(f"{labels[key]} {advances[key] * 100:g}%/mês" for key in FUNNEL_STAGE_KEYS)


GP_PROFILES: dict[str, dict[str, Any]] = {
    "primeset": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 5,
            "impressions": 7,
            "clicks": 8,
            "leads": 9,
            "ploomes_leads": 10,
            "mqls": 13,
            "sqls": 15,
            "sales": 16,
            "revenue": 17,
        },
        "media_row": 5,
        "revenue_row": 17,
        "funnel_mapping": (
            "Impressões linha 7, Cliques linha 8, Leads linha 9, "
            "MQL linha 13, SQL linha 15, Vendas linha 16 "
            "(linha 10 Ploomes informativa — fora do funil)"
        ),
        "funnel_note": "Linha 10 (Leads no Ploomes): informativa — **não** usar como lead quali",
    },
    "msys": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "year_month_text",
        "rows": {
            "year": 1,
            "month_name": 4,
            "media": 5,
            "impressions": 7,
            "clicks": 10,
            "leads": 11,
            "mqls": 14,
            "sqls": 15,
            "sales": 16,
            "revenue": 17,
        },
        "media_row": 5,
        "revenue_row": 17,
        "funnel_mapping": (
            "Impressões linha 7, Cliques linha 10, Leads linha 11, "
            "MQL linha 14, SQL linha 15, Vendas linha 16 "
            "(aba consolidada 6.0 — não usar sub-abas IMOB/VISTORIAS isoladas)"
        ),
        "funnel_note": "Funil nativo GP consolidado: sem lead quali — Leads→MQL direto",
    },
    "cdsi": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "year_month_text",
        "rows": {
            "year": 1,
            "month_name": 4,
            "media": 5,
            "impressions": 8,
            "clicks": 10,
            "leads": 11,
            "mqls": 12,
            "sqls": 13,
            "sales": 14,
            "revenue": 15,
        },
        "media_row": 5,
        "revenue_row": 15,
        "funnel_mapping": (
            "Impressões linha 8, Cliques linha 10, Leads linha 11, "
            "MQL linha 12, SQL linha 13, Vendas linha 14"
        ),
        "funnel_note": "Funil nativo GP: sem lead quali — Leads→MQL direto",
    },
    "sigo": {
        "sheet": "auto",
        "date_mode": "year_month_text",
        "rows": {
            "year": 1,
            "month_name": 4,
            "media": 7,
            "impressions": 8,
            "clicks": 9,
            "leads": 10,
            "mqls": 11,
            "sqls": 12,
            "sales": 15,
            "revenue": 16,
        },
        "media_row": 7,
        "revenue_row": 16,
        "funnel_mapping": (
            "Investimento (mídia) linha 7, Impressões linha 8, Cliques linha 9, "
            "Leads linha 10, MQL linha 11, SQL linha 12, Novos Clientes linha 15, "
            "Mensalidade + Implementação linha 16 (RM/RR linhas 13–14 informativas)"
        ),
        "funnel_note": "Funil nativo GP SIGO (aba 6.0): sem lead quali — Leads→MQL direto",
    },
    "vicentini": {
        "sheet": "auto",
        "date_mode": "year_month_text",
        "rows": {
            "year": 1,
            "month_name": 4,
            "media": 5,
            "impressions": 7,
            "clicks": 8,
            "leads": 9,
            "mqls": 10,
            "sqls": 11,
            "sales": 12,
            "revenue": 13,
        },
        "media_row": 5,
        "revenue_row": 13,
        "funnel_mapping": (
            "Investimento linha 5, Impressões linha 7, Cliques linha 8, "
            "Leads linha 9, MQL linha 10, SQL linha 11, Vendas linha 12, "
            "Receita Faturada linha 13 (aba 6.0 Acompanhamento Mensal)"
        ),
        "funnel_note": "Funil nativo GP Vicentini: sem lead quali — Leads→MQL direto",
        "baseline_mode": "operational",
    },
    "malbork": {
        "sheet": "auto",
        "date_mode": "year_month_text",
        "rows": {
            "year": 1,
            "month_name": 4,
            "date_fallback": 2,
            "media": 5,
            "impressions": 29,
            "clicks": 8,
            "leads": 9,
            "mqls": 10,
            "sqls": 11,
            "sales": 12,
            "revenue": 13,
        },
        "media_row": 5,
        "revenue_row": 13,
        "ticket_row": 6,
        "normalize_manual_funnel": True,
        "funnel_mapping": (
            "Investimento linha 5, Impressões linha 29, Cliques linha 8, "
            "Leads linha 9, MQL/SQL manual linhas 10–11, Vendas linha 12, "
            "Receita Faturada linha 13, Ticket Médio linha 6 "
            "(datas col 14+ via linha 2 datetime)"
        ),
        "funnel_note": "Funil GP Malbork: MQL/SQL manual vazios no passado → inferidos de Leads; col 14+ usa data linha 2",
    },
    "visoflex": {
        "sheet": "auto",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 7,
            "impressions": 11,
            "clicks": 12,
            "leads": 14,
            "mqls": 15,
            "sqls": 16,
            "sales": 17,
            "revenue": 18,
        },
        "media_row": 7,
        "revenue_row": 18,
        "funnel_mapping": (
            "Investimento linha 7, Impressões linha 11, Cliques linha 12, "
            "Leads linha 14, MQL linha 15, SQL linha 16, Vendas linha 17 "
            "(GP 4.0 — aba 2.2 Acompanhamento Mensal)"
        ),
        "funnel_note": "Funil nativo GP 4.0 Visoflex: sem lead quali — Leads→MQL direto",
        "baseline_mode": "operational",
    },
    "alumtech": {
        # Aba CORRETA (a partir de Fevereiro/26) — meses em colunas B..F (Fev,Mar,Abr,Mai,Jun).
        # A aba "6.0 Acompanhamento Mensal" (auto) trazia histórico antigo Mai/25–Mar/26 errado.
        "sheet": "Acompanhamento Mensal Geral (a partir de Fevereiro",
        "date_mode": "datetime_row",
        "marketplace": True,  # 3º funil: Impressões→Cliques→Visitas→Compras Ads→Faturado Ads
        "exclude_reference_month": True,  # Junho (mês corrente) é parcial — não conta
        # Maio teve ads pausada (0 compras) → não pode ser período atual (quebra funil inverso).
        # Fica no pool de baseline via inject_last_closed_in_baseline (Mai entra como M3 da mediana).
        # baseline = Mar · Abr · Mai
        "rows": {
            "date": 2,          # 2026-02-01 … (datetime)
            "media": 7,         # Investimento (realizado)
            "impressions": 11,  # Impressões (ads)
            "clicks": 13,       # Cliques (ads)
            "leads": 15,        # Visitas (M) — total paid + orgânico
            "mqls": 16,         # Compras Ads (M)
            "sqls": 16,         # Compras Ads (pass-through mqls→sqls)
            "sales": 16,        # Compras Ads
            "revenue": 17,      # Faturado Ads (M)
        },
        "media_row": 7,
        "revenue_row": 17,
        "ticket_row": 10,
        "normalize_manual_funnel": False,
        # impression_click = Cliques/Impressões (CTR pago)
        # click_lead     = Visitas/Cliques  → pode ser > 1 (amplificação orgânica)
        #                  o builder detecta automaticamente e trata como multiplicador fixo
        # lead_mql       = Compras Ads/Visitas  (taxa de conversão real)
        # mql_sql        = 1.0  (pass-through: mqls=sqls=L16)
        # sql_sale       = 1.0  (pass-through: sqls=sales=L16)
        # CPS = Investimento/Impressões
        "funnel_mapping": (
            "Investimento L7 · Impressões L11 · Cliques L13 · "
            "Visitas L15 (orgânico+pago) · Compras Ads L16 · Faturado Ads L17 · Ticket L10"
        ),
        "funnel_note": (
            "GP marketplace Oxxy Motos, aba 'Acompanhamento Mensal Geral (a partir de Fevereiro)'. "
            "Funil de ATRIBUIÇÃO ADS: Imp→Cli→Visitas→Compras Ads→Faturado Ads. "
            "click_lead = Visitas/Cliques: multiplicador orgânico fixo. "
            "lead_mql = Compras Ads/Visitas: taxa de conversão real (~3%). "
            "Mai/26 teve mídia pausada (Compras Ads=0) → excluído do funil; baseline = Fev/Mar/Abr."
        ),
    },
    "binario": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "marketplace": True,
        "exclude_reference_month": True,
        "rows": {
            "date": 3,
            "media": 6,
            "impressions": 11,
            "clicks": 13,
            "leads": 15,
            "mqls": 19,
            "sqls": 19,
            "sales": 19,
            "revenue": 21,
        },
        "media_row": 6,
        "revenue_row": 21,
        "ticket_row": 10,
        "normalize_manual_funnel": False,
        "funnel_mapping": (
            "Investimento L6 · Impressões L11 · Cliques L13 · "
            "Visitas L15 · Compras plataforma L19 · Receita plataforma L21 · Ticket L10"
        ),
        "funnel_note": (
            "GP 3.0 Binário Marketplace — aba 6.0 Acompanhamento Mensal (gid 617612824). "
            "Funil plataforma: Imp→Cli→Visitas→Compras→Receita plataforma. "
            "Histórico Ago/25–Jan/26; Fev/26 parcial excluído; margem operacional GP 10% (SR 20%)."
        ),
    },
    "promax": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 3,
            "media": 8,
            "impressions": 12,
            "clicks": 14,
            "leads": 16,
            "mqls": 17,
            "sqls": 18,
            "sales": 19,
            "revenue": 20,
        },
        "media_row": 8,
        "revenue_row": 20,
        "normalize_manual_funnel": True,
        "exclude_reference_month": True,
        "baseline_mode": "operational",
        "operational_required": ("media", "impressions", "clicks", "leads"),
        "funnel_mapping": (
            "Investimento L8, Impressões L12, Cliques Totais L14, Leads L16, "
            "MQL L17, SQL L18, Vendas L19, Receita Faturada L20, Ticket L6 "
            "(GP 3.0 Promarcas/Yanmar — 6.0 Acompanhamento Mensal; Fee L5)"
        ),
        "funnel_note": (
            "GP 3.0 Promax Supertroca Yanmar — 6.0 Acompanhamento Mensal (gid 617612824). "
            "Jan/26–Mai/26 operacional; leads desde Mar/26; 0 vendas/receita; Jun/26 parcial excluído."
        ),
    },
    "fibralink": {
        "sheet": "Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 3,
            "media": 5,
            "impressions": 7,
            "clicks": 8,
            "leads": 9,
            "mqls": 11,
            "sqls": 11,
            "sales": 12,
            "revenue": 14,
        },
        "media_row": 5,
        "revenue_row": 14,
        "ticket_row": 6,
        "normalize_manual_funnel": True,
        "exclude_reference_month": True,
        "funnel_mapping": (
            "Investimento L5, Impressões L7, Cliques Totais L8, Leads L9, "
            "Oportunidades L11 (→ MQL/SQL pass-through), Vendas L12, Faturamento L14, Ticket L6 "
            "(GP FibraLink — aba Acompanhamento Mensal; MQL L10 vazio)"
        ),
        "funnel_note": (
            "GP FibraLink — Acompanhamento Mensal (gid 776105258). "
            "Funil Leads→Oportunidades→Vendas; histórico Ago/24–Mai/26; Jun/26 parcial excluído."
        ),
    },
    "gondolas": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 3,
            "media": 7,
            "impressions": 8,
            "clicks": 9,
            "leads": 10,
            "mqls": 11,
            "sqls": 12,
            "sales": 14,
            "revenue": 16,
        },
        "media_row": 7,
        "revenue_row": 16,
        "ticket_row": 17,
        "normalize_manual_funnel": True,
        "exclude_reference_month": True,
        "baseline_mode": "operational",
        "operational_required": ("media", "impressions", "clicks", "leads"),
        "funnel_mapping": (
            "Mídia L7, Impressões L8, Cliques Totais L9, Leads L10, MQL L11, SQL L12, "
            "Em negociação L13 (skip), Novos Clientes L14, Faturamento L16, Ticket L17 "
            "(GP 5.0 Grupo SA — 6.0 Acompanhamento Mensal; Fee L6 · Invest total L5)"
        ),
        "funnel_note": (
            "GP 5.0 SA Gôndolas — 6.0 Acompanhamento Mensal (gid 47048281). "
            "Set/25–Mai/26; orçamento L15 fora do funil; Jun/26 parcial excluído."
        ),
    },
    "suprimedico": {
        "sheet": "auto",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 9,
            "impressions": 61,
            "clicks": 62,
            "leads": 82,
            "mqls": 83,
            "sqls": 84,
            "sales": 86,
            "revenue": 87,
        },
        "media_row": 9,
        "revenue_row": 87,
        "ticket_row": 80,
        "funnel_mapping": (
            "Investimento linha 9, Impressões Gerais linha 61, Cliques Totais linha 62, "
            "Leads linha 82, MQL linha 83, SQL linha 84, Vendas linha 86, "
            "Faturamento CRM linha 87 (bloco Campanhas de Inside Sales / V4 Company)"
        ),
        "funnel_note": "Funil nativo GP Suprimédico — Campanhas de Inside Sales (L79+); contrato V4 desde Out/25",
    },
    "centroauditivo": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "year_month_text",
        "rows": {
            "year": 1,
            "month_name": 4,
            "media": 6,
            "impressions": 8,
            "clicks": 9,
            "leads": 10,
            "mqls": 12,
            "sqls": 13,
            "sales": 14,
            "revenue": 15,
        },
        "media_row": 6,
        "revenue_row": 15,
        "ticket_row": 7,
        "funnel_mapping": (
            "Investimento linha 6, Impressões linha 8, Cliques linha 9, "
            "Leads linha 10, MQL linha 12, SQL linha 13, Vendas linha 14, "
            "Receita Faturada linha 15, Ticket Médio linha 7 (Fee mensal linha 5 — fora do funil)"
        ),
        "funnel_note": (
            "GP Centro Auditivo Macaé — receita L15 pode vir como datetime no Sheets; "
            "parse_num recupera o serial (= ticket × vendas). Mês sem MQL/SQL/vendas/receita = zero."
        ),
    },
    "ipo": {
        "sheet": "Acomp. Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 5,
            "media": 26,
            "impressions": [10, 16, 22],
            "clicks": [9, 15],
            "leads": 27,
            "mqls": 33,
            "sqls": 34,
            "sales": 35,
            "revenue": 45,
        },
        "media_row": 26,
        "revenue_row": 45,
        "ticket_row": 48,
        "baseline_mode": "operational",
        "exclude_reference_month": True,
        "estimated_ticket_when_sales": 6000.0,
        "funnel_mapping": (
            "GP IPO multi-plataforma — aba Acomp. Mensal. "
            "Invest. Total L26, Impressões Meta+Google+LinkedIn L10+L16+L22, "
            "Cliques Meta+Google L9+L15, Leads L27, MQL/SQL/Vendas manual L33–35, "
            "Receita L45 (vazia no GP → vendas × ticket estimado R$ 6.000 do BEP legado)"
        ),
        "funnel_note": (
            "Funil manual IPO — receita amarela não preenchida; ticket estimado só quando vendas > 0. "
            "Mai/26 sem MQL/SQL manual → fora do bench operacional."
        ),
    },
    "bmb": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 5,
            "impressions": 7,
            "clicks": 8,
            "leads": 9,
            "mqls": 10,
            "sqls": 11,
            "sales": 12,
            "revenue": 13,
        },
        "media_row": 5,
        "revenue_row": 13,
        "ticket_row": 6,
        "exclude_reference_month": True,
        "baseline_mode": "operational",
        "funnel_mapping": (
            "Investimento L5, Impressões L7, Cliques Totais L8, Leads L9, "
            "MQL L10, SQL L11, Vendas L12, Receita Faturada L13, Ticket L6"
        ),
        "funnel_note": (
            "GP BMB Tecidos — layout col. A (6.0 Acompanhamento Mensal). "
            "Jan–Mai/26 com funil operacional parcial; Abr/26 único mês com venda+receita."
        ),
    },
    "greenway": {
        "sheet": "2.2 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 5,
            "impressions": 6,
            "clicks": 7,
            "leads": 8,
            "mqls": 9,
            "sqls": 12,
            "sales": 13,
            "revenue": 14,
        },
        "media_row": 5,
        "revenue_row": 14,
        "ticket_row": 15,
        "exclude_reference_month": True,
        "baseline_mode": "operational",
        "funnel_mapping": (
            "Investimento L5, Impressões L6, Cliques Totais L7, Leads L8, "
            "MQL L9, SQL L12, Vendas L13, Receita Faturada L14, Ticket L15"
        ),
        "funnel_note": (
            "GP Green Way Insulation — aba 2.2 Acompanhamento Mensal (GP 4.0 INSIDE SALES). "
            "Vendas desde Nov/25; Jun/26 parcial excluído."
        ),
    },
    "simpleeducation": {
        "sheet": "2.2 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 5,
            "impressions": 6,
            "clicks": 7,
            "leads": 8,
            "mqls": 9,
            "sqls": 10,
            "sales": 11,
            "revenue": 12,
        },
        "media_row": 5,
        "revenue_row": 12,
        "ticket_row": 13,
        "normalize_manual_funnel": True,
        "exclude_reference_month": True,
        "baseline_mode": "operational",
        "funnel_mapping": (
            "Investimento L5, Impressões L6, Cliques Totais L7, Leads L8, "
            "MQL L9, SQL L10, Vendas L11, Receita Faturada L12, Ticket Médio L13 "
            "(aba 2.2 Acompanhamento Mensal — GP 4.0 INSIDE SALES)"
        ),
        "funnel_note": (
            "GP Simple Education — layout 2.2 (SQL L10, não L12 como Green Way). "
            "Receita L12 frequentemente zerada; vendas esporádicas Sep–Dez/25."
        ),
    },
    "elevate": {
        "sheet": "2.2 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 5,
            "impressions": 6,
            "clicks": 7,
            "leads": 8,
            "mqls": 9,
            "sqls": 10,
            "sales": 11,
            "revenue": 12,
        },
        "media_row": 5,
        "revenue_row": 12,
        "ticket_row": 13,
        "exclude_reference_month": True,
        "baseline_mode": "operational",
        "funnel_mapping": (
            "Investimento L5, Impressões L6, Cliques Totais L7, Leads L8, "
            "MQL L9, SQL L10, Vendas L11, Receita Faturada L12, Ticket L13"
        ),
        "funnel_note": (
            "GP Elevate Incorporadora — aba 2.2 Acompanhamento Mensal (GP 4.0 IS). "
            "Contrato a partir Jan/26; dados reais a partir Abr/26. Jun/26 parcial excluído."
        ),
    },
    "florestec": {
        "sheet": "2.2 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 6,
            "impressions": 11,
            "clicks": 12,
            "leads": 13,
            "mqls": 14,
            "sqls": 15,
            "sales": 18,
            "revenue": 19,
        },
        "media_row": 6,
        "revenue_row": 19,
        "ticket_row": 20,
        "exclude_reference_month": True,
        "funnel_mapping": (
            "Investimento L6, Impressões L11, Cliques L12, Leads L13, "
            "MQL L14, SQL L15, Vendas L18, Receita L19, Ticket L20"
        ),
        "funnel_note": (
            "GP 4.0 IS Florestec — aba 2.2 Acompanhamento Mensal. "
            "Jul/25–Jun/26 (12 meses). Jul–Ago/25 sem MQL numérico (whatsapp tracking). "
            "Set/25 sem vendas. Dados completos Out/25–Abr/26."
        ),
    },
    "globalsonic": {
        "sheet": "2.2 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 6,
            "impressions": 8,
            "clicks": 9,
            "leads": 10,
            "mqls": 11,
            "sqls": 12,
            "sales": 13,
            "revenue": 14,
        },
        "media_row": 6,
        "revenue_row": 14,
        "ticket_row": 7,
        "funnel_mapping": (
            "Investimento L6, Impressões L8, Cliques Totais L9, Leads L10, "
            "MQL L11, SQL L12, Vendas L13, Receita Faturada L14, Ticket Médio L7"
        ),
        "funnel_note": (
            "GP 4.0 IS Global Sonic — aba 2.2 Acompanhamento Mensal. "
            "Dados Mai/25–Jun/26 (14 meses). Jun/26 parcial excluído."
        ),
    },
    "escola": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 5,
            "impressions": 7,
            "clicks": 8,
            "leads": 9,
            "mqls": 10,
            "sqls": 11,
            "sales": 12,
            "revenue": 13,
        },
        "media_row": 5,
        "revenue_row": 13,
        "ticket_row": 6,
        "funnel_mapping": (
            "Investimento L5, Ticket L6, Impressões L7, Cliques L8, Leads L9, "
            "MQL L10, SQL L11, Vendas L12, Receita L13"
        ),
        "funnel_note": (
            "GP 3.0 IS Escola Grêmio Sinop — 6.0 Acompanhamento Mensal. "
            "MQL/SQL manuais (frequentemente 0 mesmo com vendas)."
        ),
    },
    "sotobi": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 5,
            "impressions": 7,
            "clicks": 8,
            "leads": 9,
            "mqls": 10,
            "sqls": 11,
            "sales": 12,
            "revenue": 13,
        },
        "media_row": 5,
        "revenue_row": 13,
        "ticket_row": 6,
        "exclude_reference_month": True,
        "funnel_mapping": (
            "Investimento L5, Ticket L6, Impressões L7, Cliques L8, Leads L9, "
            "MQL L10, SQL L11, Vendas L12, Receita L13 (bd Leads / vendas V4)"
        ),
        "funnel_note": (
            "GP 3.0 IS SOTOBI (Atlântica Máquinas layout) — 6.0 Acompanhamento Mensal. "
            "Funil completo com receita; Jun/26 parcial excluído."
        ),
    },
    "ambientair": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 9,
            "impressions": 14,
            "clicks": 15,
            "leads": 17,
            "mqls": 18,
            "sqls": 19,
            "sales": 22,
            "revenue": 23,
        },
        "media_row": 9,
        "revenue_row": 23,
        "ticket_row": 24,
        "normalize_manual_funnel": True,
        "exclude_reference_month": True,
        "baseline_mode": "operational",
        "baseline_sales_months_only": True,
        "funnel_mapping": (
            "Investimento L9 (Investido), Impressões L14, Cliques Totais L15, Leads L17, "
            "MQL Manual L18, SQL Manual L19, Vendas Manual L22, Receita Manual L23, Ticket L24"
        ),
        "funnel_note": (
            "GP 4.0 IS Ambient Air — 6.0 Acompanhamento Mensal. "
            "MQL/SQL manual esparso → inferidos de leads quando vazios; Jun/26 parcial excluído. "
            "Baseline projeção = mediana 3M só em meses com vendas (Nov/25–Fev/26)."
        ),
    },
    "excelgroup": {
        "sheet": "2.2 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 8,
            "impressions": 13,
            "clicks": 14,
            "leads": 15,
            "mqls": 16,
            "sqls": 17,
            "sales": 18,
            "revenue": 19,
        },
        "media_row": 8,
        "revenue_row": 19,
        "ticket_row": 20,
        "normalize_manual_funnel": True,
        "exclude_reference_month": True,
        "baseline_mode": "operational",
        "operational_required": ("media", "impressions", "clicks"),
        "funnel_mapping": (
            "Investido L8, Impressões L13, Cliques Totais L14, Leads L15, "
            "MQL L16, SQL L17, Vendas L18, Receita Faturada L19, Ticket L20 "
            "(aba 2.2 — GP 4.0 Excel Group; Fee L5 · Plano mídia L6)"
        ),
        "funnel_note": (
            "GP 4.0 IS Excel Group — 2.2 Acompanhamento Mensal (layout estendido Fee/Plano/Margem). "
            "0 vendas no histórico; leads desde Mai/26; Jun/26 parcial excluído."
        ),
    },
    "novomilenio": {
        "sheet": "2.2 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 3,
            "media": 5,
            "impressions": 6,
            "clicks": 7,
            "leads": 8,
            "mqls": 9,
            "sqls": 10,
            "sales": 11,
            "revenue": 12,
        },
        "media_row": 5,
        "revenue_row": 12,
        "ticket_row": 13,
        "exclude_reference_month": True,
        "funnel_mapping": (
            "Investimento L5, Impressões L6, Cliques Totais L7, Leads L8, "
            "MQL L9, SQL L10, Vendas L11, Receita Faturada L12, Ticket Médio L13 "
            "(GP 3.0 Novo Milênio — 2.2 Acompanhamento Mensal)"
        ),
        "funnel_note": (
            "GP 3.0 Novo Milênio Uniformes — 2.2 Acompanhamento Mensal. "
            "Funil completo com receita; Abr/26 sem vendas; Jun/26 parcial excluído."
        ),
    },
    "portico": {
        "sheet": "2.2 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 3,
            "media": 5,
            "impressions": 6,
            "clicks": 7,
            "leads": 9,
            "mqls": 10,
            "sqls": 11,
            "sales": 12,
            "revenue": 13,
        },
        "media_row": 5,
        "revenue_row": 13,
        "normalize_manual_funnel": True,
        "exclude_reference_month": True,
        "baseline_mode": "operational",
        "operational_required": ("media", "impressions", "clicks", "leads"),
        "funnel_mapping": (
            "Investimento L5, Impressões L6, Cliques Totais L7, Sessões L8 (skip), "
            "Leads L9, MQL L10, SQL L11, Vendas L12, Receita L13, Ticket L14 "
            "(GP 3.0 Porti Fachadas — 2.2 Acompanhamento Mensal)"
        ),
        "funnel_note": (
            "GP 3.0 Portico/Porti Fachadas — 2.2 Acompanhamento Mensal com linha Sessões L8. "
            "0 vendas no histórico; MQL desde Mar/26; Jun/26 parcial excluído."
        ),
    },
    "igablumenau": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 3,
            "media": 9,
            "impressions": 11,
            "clicks": 14,
            "leads": 15,
            "mqls": 16,
            "sqls": 17,
            "sales": 18,
            "revenue": 20,
        },
        "media_row": 9,
        "revenue_row": 20,
        "exclude_reference_month": True,
        "normalize_manual_funnel": True,
        "funnel_mapping": (
            "Investido L9, Impressões L11, Cliques Totais L14, Leads L15, "
            "MQL Manual L16, SQL Manual L17, Vendas Manual L18, "
            "Receita Total Manual L20, Ticket L22 "
            "(GP 3.0 IGA Blumenau — 6.0 Acompanhamento Mensal; Fee L6 · Plano L7 · Margem L8)"
        ),
        "funnel_note": (
            "GP 3.0 IGA Blumenau — 6.0 Acompanhamento Mensal (link gid 617612824). "
            "Histórico Jan/25–Mai/26; receita L20 total (não L21 curso longo); Jun/26 parcial excluído."
        ),
    },
    "oncimport": {
        "sheet": "2.2 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 3,
            "media": 7,
            "impressions": 9,
            "clicks": 10,
            "leads": 11,
            "mqls": 12,
            "sqls": 13,
            "sales": 14,
            "revenue": 15,
        },
        "media_row": 7,
        "revenue_row": 15,
        "normalize_manual_funnel": True,
        "exclude_reference_month": True,
        "baseline_mode": "operational",
        "operational_required": ("media", "impressions", "clicks"),
        "funnel_mapping": (
            "Investimento L7, Impressões L9, Cliques Totais L10, Leads L11, "
            "MQL L12, SQL L13, Vendas L14, Receita Faturada L15, Ticket L8 "
            "(GP 4.0 ONCO Import — 2.2 Acompanhamento Mensal; Meta L5 · Plano mídia L6)"
        ),
        "funnel_note": (
            "GP 4.0 ONCO Import — 2.2 Acompanhamento Mensal (gid 617612824). "
            "Fev/26–Mai/26 operacional com mídia; 1 venda Abr/26 R$ 9k; Jun/26 parcial excluído."
        ),
    },
    "psm": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 5,
            "impressions": 7,
            "clicks": 8,
            "leads": 10,
            "mqls": 12,
            "sqls": 13,
            "sales": 14,
            "revenue": 15,
        },
        "media_row": 5,
        "revenue_row": 15,
        "ticket_row": 6,
        "baseline_mode": "operational",
        "operational_required": ("media", "impressions", "clicks", "leads", "mqls"),
        "funnel_mapping": (
            "Investimento L5, Ticket L6, Impressões L7, Cliques L8, "
            "L9=CTR(skip), Leads L10, L11=CPL(skip), MQL L12, SQL L13, "
            "Vendas L14, Receita L15"
        ),
        "funnel_note": (
            "GP 3.0 IS PSM — 6.0 Acompanhamento Mensal. "
            "0 vendas em todo o histórico (Dez/25–Jun/26). SQL sempre 0. "
            "Baseline operacional usa MQL como estágio terminal. Ticket indefinido."
        ),
    },
    "wfeng": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 5,
            "impressions": 8,
            "clicks": 9,
            "leads": 10,
            "mqls": 11,
            "sqls": 12,
            "sales": 13,
            "revenue": 14,
        },
        "media_row": 5,
        "revenue_row": 14,
        "ticket_row": 6,
        "baseline_mode": "operational",
        "funnel_mapping": (
            "Investimento L5, Ticket L6, L7=Sessoes(skip), "
            "Impressões L8, Cliques L9, Leads L10, MQL L11, SQL L12, "
            "Vendas L13, Receita L14"
        ),
        "funnel_note": (
            "GP IS WF Engenharia — 6.0 Acompanhamento Mensal. "
            "Dados reais a partir Set/25 (placeholder Jan/24–Jul/24 ignorado). "
            "0 vendas registradas até Jun/26."
        ),
    },
    "auddas": {
        "sheet": "6.0 Acompanhamento Mensal",
        "date_mode": "datetime_row",
        "rows": {
            "date": 2,
            "media": 8,
            "impressions": 15,
            "clicks": 16,
            "leads": 17,
            "mqls": 18,
            "sqls": 19,
            "sales": 999,
            "revenue": 999,
        },
        "media_row": 8,
        "revenue_row": 22,
        "baseline_mode": "operational",
        "exclude_reference_month": True,
        "secondary_overlay": {
            "sheet": "Tabela mensal Inside Sales ",
            "rows": {
                "header_month": 3,
                "sales": 17,
                "revenue": 22,
                "ticket": 8,
            },
        },
        "funnel_mapping": (
            "Investimento L8, Impressões L15, Cliques L16, Leads L17, "
            "MQL L18, SAL→SQL L19 (aba 6.0 Geral); "
            "Vendas L17 + Faturamento Direto L22 (aba Tabela mensual Inside Sales, histórico CRM)"
        ),
        "funnel_note": (
            "GP Auddas — funil de mídia na 6.0 (SAL = SQL); vendas/receita CRM na Tabela mensual IS "
            "(até Mai/24 no GP). Meses recentes sem fechamento CRM → modo operacional + ticket inferido."
        ),
    },
}


def norm_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.strip().lower()


def parse_num(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        # Célula NUMÉRICA do funil formatada como data (ex.: Visitas no GP Alumtech: o valor
        # real 39812 vira "2008-12-30"). O número de série Excel é o valor verdadeiro — recupera
        # em vez de descartar como 0. A linha de DATA usa coerce_datetime à parte, então isto só
        # afeta campos numéricos (impressões, cliques, visitas, compras, faturado…).
        serial = (value - datetime(1899, 12, 30)).days
        return float(serial) if serial > 0 else 0.0
    if isinstance(value, date):
        serial = (value - date(1899, 12, 30)).days
        return float(serial) if serial > 0 else 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    if text.startswith("#"):
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


def mean_funnel_rate(
    months: list[dict[str, Any]],
    numerator_key: str,
    denominator_key: str,
) -> float:
    samples = [
        cap_rate(div(month[numerator_key], month[denominator_key]))
        for month in months
        if month[denominator_key] > 0
    ]
    return cap_rate(sum(samples) / len(samples)) if samples else 0.0


def median_stage_rate(
    months: list[dict[str, Any]],
    numerator_key: str,
    denominator_key: str,
) -> float:
    """Mediana histórica da etapa (robusta a outliers como Black Friday)."""
    samples = [
        div(month[numerator_key], month[denominator_key])
        for month in months
        if month.get(denominator_key, 0) > 0
    ]
    return median(samples) if samples else 0.0


def stage_ceilings_from_history(
    rate_months: list[dict[str, Any]],
    baseline_rates: dict[str, float],
    headroom: float = STAGE_CEILING_HEADROOM,
) -> dict[str, float]:
    """Teto por etapa = max(mediana dos últimos 3 meses, baseline M1) × folga, cap 95%.

    `rate_months` deve ser a janela da projeção (últimos 3 meses), não todo o histórico —
    a projeção parte do desempenho recente. Usa a **mediana** (não o melhor mês) para não
    ancorar num pico pontual. O `max` com o baseline garante que o teto nunca caia abaixo do
    nível atual de onde a projeção parte. Sem histórico, cai no fallback seguro.
    """
    ceilings: dict[str, float] = {}
    for key in FUNNEL_STAGE_KEYS:
        num, den = STAGE_RATE_NUM_DEN[key]
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
    return [cap_rate(start + (end - start) * idx / (months - 1)) for idx in range(months)]


def gradual_linear(start: float, end: float, months: int = 7) -> list[float]:
    if months <= 1:
        return [end]
    return [start + (end - start) * idx / (months - 1) for idx in range(months)]


def month_label(dt: datetime) -> str:
    return f"{MONTH_PT[dt.month]}/{dt.year % 100:02d}"


def label_from_year_month(year: int, month_num: int) -> str:
    return f"{MONTH_PT[month_num]}/{year % 100:02d}"


def median_funnel_volume(months: list[dict[str, Any]], key: str) -> float:
    """Mediana mensal de uma métrica do funil na janela baseline (ex.: 3M)."""
    samples = [
        float(month.get(key, 0) or 0)
        for month in months
        if float(month.get(key, 0) or 0) > 0
    ]
    return round(median(samples), 2) if samples else 0.0


def build_baseline_funnel_volumes(months: list[dict[str, Any]]) -> dict[str, float]:
    """Quantidades medianas por etapa — ponto de partida M1 da projeção."""
    return {
        "impressions": median_funnel_volume(months, "impressions"),
        "clicks": median_funnel_volume(months, "clicks"),
        "leads": median_funnel_volume(months, "leads"),
        "mqls": median_funnel_volume(months, "mqls"),
        "sqls": median_funnel_volume(months, "sqls"),
        "sales": median_funnel_volume(months, "sales"),
    }


def filter_sales_months(months: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Meses com vendas > 0 — usado quando o baseline de projeção ignora meses zerados."""
    return [month for month in months if float(month.get("sales", 0) or 0) > 0]


def project_funnel_volumes_from_baseline(
    baseline_volumes: dict[str, float],
    *,
    impression_click: float,
    click_lead: float,
    lead_mql: float,
    mql_sql: float,
    sql_sale: float,
    month_idx: int = 0,
) -> dict[str, float]:
    """Projeção: M1 = medianas exatas; M2+ = impressões baseline × taxas compostas do mês."""
    if month_idx == 0:
        return dict(baseline_volumes)
    impressions = baseline_volumes["impressions"]
    clicks = impressions * impression_click
    leads = clicks * click_lead
    mqls = leads * lead_mql
    sqls = mqls * mql_sql
    sales = sqls * sql_sale
    return {
        "impressions": impressions,
        "clicks": clicks,
        "leads": leads,
        "mqls": mqls,
        "sqls": sqls,
        "sales": sales,
    }


def revenue_from_funnel(
    media: float,
    *,
    impression_click: float,
    click_lead: float,
    lead_mql: float,
    mql_sql: float,
    sql_sale: float,
    ticket: float,
    cps: float,
    baseline_volumes: dict[str, float] | None = None,
    month_idx: int = 0,
) -> float:
    if baseline_volumes:
        volumes = project_funnel_volumes_from_baseline(
            baseline_volumes,
            impression_click=impression_click,
            click_lead=click_lead,
            lead_mql=lead_mql,
            mql_sql=mql_sql,
            sql_sale=sql_sale,
            month_idx=month_idx,
        )
        return round(volumes["sales"] * ticket, 2)
    impressions = media / cps if cps else 0.0
    clicks = impressions * impression_click
    leads = clicks * click_lead
    mqls = leads * lead_mql
    sqls = mqls * mql_sql
    sales = sqls * sql_sale
    return round(sales * ticket, 2)


def gp_projection_trail(funnel_months: list[dict[str, Any]], count: int = 7) -> list[dict[str, Any]]:
    """Meses GP para projeção: M1 = mês anterior, M2 = mês atual, depois trail histórico."""
    if not funnel_months:
        return []
    ordered: list[dict[str, Any]] = []
    if len(funnel_months) >= 2:
        ordered.append(funnel_months[-2])
        ordered.append(funnel_months[-1])
    else:
        ordered.append(funnel_months[-1])
    for month in reversed(funnel_months[:-2]):
        if len(ordered) >= count:
            break
        ordered.append(month)
    while len(ordered) < count:
        ordered.append(ordered[-1])
    return ordered[:count]


def gp_projection_media(funnel_months: list[dict[str, Any]], count: int = 7) -> list[float]:
    return [round(month["media"], 2) for month in gp_projection_trail(funnel_months, count)]


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
        if not text:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def normalize_funnel_item(item: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Preenche MQL/SQL quando o GP usa campos manual vazios (ex.: Malbork)."""
    if not profile.get("normalize_manual_funnel"):
        return item
    patched = dict(item)
    if patched["leads"] > 0 and patched["mqls"] <= 0:
        patched["mqls"] = patched["leads"]
    if patched["mqls"] > 0 and patched["sqls"] <= 0:
        patched["sqls"] = patched["mqls"]
    return patched


def _metric_from_rows(ws, row_spec: int | list[int], col: int) -> float:
    if isinstance(row_spec, list):
        return sum(parse_num(ws.cell(row, col).value) for row in row_spec)
    return parse_num(ws.cell(row_spec, col).value)


def parse_month_item(ws, profile: dict[str, Any], col: int) -> dict[str, Any] | None:
    rows = profile["rows"]
    if profile["date_mode"] == "datetime_row":
        dt = coerce_datetime(ws.cell(rows["date"], col).value)
        if not dt:
            return None
        label = month_label(dt)
    else:
        year = parse_num(ws.cell(rows["year"], col).value)
        month_raw = norm_text(ws.cell(rows["month_name"], col).value)
        month_num = MONTH_NAME_PT.get(month_raw)
        if year and month_num:
            label = label_from_year_month(int(year), month_num)
        else:
            fallback_row = rows.get("date_fallback")
            dt = coerce_datetime(ws.cell(fallback_row, col).value) if fallback_row else None
            if not dt:
                return None
            label = month_label(dt)

    item = normalize_funnel_item(
        {
            "label": label,
            "media": _metric_from_rows(ws, rows["media"], col),
            "impressions": _metric_from_rows(ws, rows["impressions"], col),
            "clicks": _metric_from_rows(ws, rows["clicks"], col),
            "leads": _metric_from_rows(ws, rows["leads"], col),
            "mqls": _metric_from_rows(ws, rows["mqls"], col),
            "sqls": _metric_from_rows(ws, rows["sqls"], col),
            "sales": _metric_from_rows(ws, rows["sales"], col),
            "revenue": _metric_from_rows(ws, rows["revenue"], col),
        },
        profile,
    )
    est_ticket = profile.get("estimated_ticket_when_sales")
    if est_ticket and item["sales"] > 0 and item["revenue"] <= 0:
        item["revenue"] = round(item["sales"] * float(est_ticket), 2)
    return item


def read_investment_months(ws, profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Todos os meses com investimento > 0 — inclui pré-funil (ex.: Jan–Mai/25 sem MQL)."""
    months: list[dict[str, Any]] = []
    for col in range(2, ws.max_column + 1):
        item = parse_month_item(ws, profile, col)
        if item and item["media"] > 0:
            months.append(item)
    return months


def label_sort_key(label: str) -> tuple[int, int]:
    """Ordena rótulos Mmm/YY (ex.: Jan/26)."""
    month_part, year_part = label.split("/")
    year = 2000 + int(year_part) if len(year_part) == 2 else int(year_part)
    month_rev = {abbr.lower(): num for num, abbr in MONTH_PT.items()}
    month_num = month_rev.get(month_part.lower()[:3], 0)
    return year, month_num


def filter_months_from(months: list[dict[str, Any]], from_label: str) -> list[dict[str, Any]]:
    cutoff = label_sort_key(from_label)
    return [month for month in months if label_sort_key(month["label"]) >= cutoff]


def _sheet_cell(values: list[list[Any]], row: int, col: int) -> Any:
    ri, ci = row - 1, col - 1
    if ri < len(values) and ci < len(values[ri]):
        return values[ri][ci]
    return None


def read_secondary_overlay(project_folder: Path, overlay: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Lê vendas/receita de aba secundária (ex.: Tabela mensual Inside Sales)."""
    manifest_path = project_folder / "source" / "manifest-entry.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    spreadsheet_id = extract_spreadsheet_id(manifest.get("growthpack_updated_link"))
    if not spreadsheet_id:
        raise ValueError(f"Link do Growth Pack ausente em {manifest_path}")

    from googleapiclient.discovery import build

    creds = load_google_credentials()
    sheets = build("sheets", "v4", credentials=creds)
    sheet_name = overlay["sheet"]
    rows = overlay["rows"]
    values = (
        sheets.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"'{sheet_name}'!A1:AZ35")
        .execute()
        .get("values", [])
    )
    if not values:
        return {}

    max_col = max(len(row) for row in values)
    out: dict[str, dict[str, float]] = {}
    for col in range(2, max_col + 1):
        header = norm_text(_sheet_cell(values, rows["header_month"], col))
        year_match = re.search(r"(\d{4})", header)
        month_match = re.search(r"mes\s*(\d{1,2})", header)
        if not year_match or not month_match:
            continue
        label = label_from_year_month(int(year_match.group(1)), int(month_match.group(1)))
        sales = parse_num(_sheet_cell(values, rows["sales"], col))
        revenue = parse_num(_sheet_cell(values, rows["revenue"], col))
        ticket = parse_num(_sheet_cell(values, rows.get("ticket", 0), col)) if rows.get("ticket") else 0.0
        if sales <= 0 and revenue <= 0:
            continue
        payload: dict[str, float] = {"sales": sales, "revenue": revenue}
        if ticket > 0:
            payload["ticket"] = ticket
        out[label] = payload
    return out


def apply_secondary_overlay(
    months: list[dict[str, Any]], overlay_data: dict[str, dict[str, float]]
) -> list[dict[str, Any]]:
    if not overlay_data:
        return months
    patched: list[dict[str, Any]] = []
    for month in months:
        item = dict(month)
        extra = overlay_data.get(month["label"])
        if extra:
            if extra.get("sales", 0) > 0:
                item["sales"] = extra["sales"]
            if extra.get("revenue", 0) > 0:
                item["revenue"] = extra["revenue"]
        patched.append(item)
    return patched


def read_operational_funnel_months(ws, profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Meses com funil operacional (topo + MQL + SQL) — sem exigir vendas/receita."""
    required = tuple(profile.get("operational_required") or OPERATIONAL_FUNNEL_REQUIRED)
    months: list[dict[str, Any]] = []
    for col in range(2, ws.max_column + 1):
        item = parse_month_item(ws, profile, col)
        if item and all(item[key] > 0 for key in required):
            months.append(item)
    return months


def read_funnel_months(ws, profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Meses com funil completo + faturamento — bench e projeção de taxas."""
    months: list[dict[str, Any]] = []
    for col in range(2, ws.max_column + 1):
        item = parse_month_item(ws, profile, col)
        if item and all(item[key] > 0 for key in FUNNEL_REQUIRED):
            months.append(item)
    return months


def read_months(ws, profile: dict[str, Any]) -> list[dict[str, Any]]:
    return read_funnel_months(ws, profile)


def resolve_growthpack_sheet_name(project_folder: Path, profile: dict[str, Any]) -> str:
    requested = profile.get("sheet") or "6.0 Acompanhamento Mensal"
    if requested != "auto":
        return requested
    manifest_path = project_folder / "source" / "manifest-entry.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    spreadsheet_id = extract_spreadsheet_id(manifest.get("growthpack_updated_link"))
    if not spreadsheet_id:
        raise ValueError(
            f"Link do Growth Pack ausente em {manifest_path} "
            "(necessário para localizar aba Acompanhamento Mensal)."
        )
    creds = load_google_credentials()
    return find_acompanhamento_mensal_sheet(creds, spreadsheet_id)


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
    ws, gp_source_used = open_growthpack_worksheet(
        project_folder, sheet_name, source=gp_source
    )

    monthly_fee = parse_num(manifest["fee"])
    monthly_media = parse_num(manifest["media_planned"])
    margin = parse_num(manifest["margin_pct"]) / 100

    funnel_months = read_funnel_months(ws, profile)
    operational_months_all = (
        read_operational_funnel_months(ws, profile)
        if profile.get("baseline_mode") == "operational"
        else []
    )
    overlay_cfg = profile.get("secondary_overlay")
    overlay_data: dict[str, dict[str, float]] = {}
    if overlay_cfg:
        overlay_data = read_secondary_overlay(project_folder, overlay_cfg)
        funnel_months = apply_secondary_overlay(funnel_months, overlay_data)
        operational_months_all = apply_secondary_overlay(operational_months_all, overlay_data)
    if not funnel_months and operational_months_all:
        funnel_months = operational_months_all

    investment_months = read_investment_months(ws, profile)
    if overlay_cfg:
        investment_months = apply_secondary_overlay(investment_months, overlay_data)
    if not investment_months:
        raise ValueError(
            f"Nenhum mês com investimento em {sheet_name!r} (perfil {profile_name})."
        )
    if not funnel_months and not operational_months_all:
        raise ValueError(
            f"Nenhum mês com funil completo em {sheet_name!r} (perfil {profile_name})."
        )
    if not funnel_months:
        funnel_months = operational_months_all

    # Mês corrente incompleto: o mês == reference_date ainda está rodando (dados parciais).
    # Excluir evita usá-lo como competência ou inflar/distorcer o acumulado. Opt-in por perfil.
    if profile.get("exclude_reference_month"):
        ref_for_filter = reference_date or date.today()
        ref_label = label_from_year_month(ref_for_filter.year, ref_for_filter.month)
        funnel_months = [m for m in funnel_months if m["label"] != ref_label]
        investment_months = [m for m in investment_months if m["label"] != ref_label]
        operational_months_all = [
            m for m in operational_months_all if m["label"] != ref_label
        ]
        # Último mês fechado (ref - 1) como competência, mesmo sem conversões de ads (mídia
        # pausada → Compras Ads=0). Sem isto, a ferramenta usaria o último mês COM funil como
        # "atual" e perderia o anterior do baseline. Pega de investment_months (tem mídia>0).
        if profile.get("force_last_closed_as_current"):
            last_closed_dt = date(ref_for_filter.year, ref_for_filter.month, 1) - timedelta(days=1)
            last_closed_label = label_from_year_month(last_closed_dt.year, last_closed_dt.month)
            have = {m["label"] for m in funnel_months}
            if last_closed_label not in have:
                extra = next(
                    (m for m in investment_months if m["label"] == last_closed_label), None
                )
                if extra is not None:
                    funnel_months = funnel_months + [extra]

    if from_label:
        funnel_months = filter_months_from(funnel_months, from_label)
        investment_months = filter_months_from(investment_months, from_label)
        if not investment_months:
            raise ValueError(f"Nenhum mês após {from_label} em {sheet_name!r}.")

    operational_months = (
        filter_months_from(operational_months_all, from_label)
        if profile.get("baseline_mode") == "operational" and from_label
        else operational_months_all
        if profile.get("baseline_mode") == "operational"
        else funnel_months
    )

    if lt_months > 0:
        funnel_months = funnel_months[-lt_months:]
        first_label = funnel_months[0]["label"]
        investment_months = [m for m in investment_months if m["label"] >= first_label] or funnel_months
        if operational_months:
            operational_months = filter_months_from(operational_months, first_label)

    months = funnel_months
    current = months[-1]
    tm_recurrence_months, tm_recurrence_raw = resolve_mrr_from_manifest(manifest)
    gp_billing_samples = [
        div(month["revenue"], month["sales"])
        for month in investment_months
        if month["sales"] > 0 and month["revenue"] > 0
    ] or [
        div(month["revenue"], month["sales"]) for month in months if month["sales"] > 0
    ]
    gp_billing_ticket_median = (
        round(median(gp_billing_samples), 2)
        if gp_billing_samples
        else round(div(current["revenue"], current["sales"]), 2)
    )
    ticket_row = profile.get("ticket_row")
    if ticket_row:
        ticket_samples = [
            parse_num(ws.cell(ticket_row, col).value)
            for col in range(2, ws.max_column + 1)
            if parse_num(ws.cell(ticket_row, col).value) > 0
        ]
        if ticket_samples:
            gp_billing_ticket_median = round(median(ticket_samples), 2)
    if overlay_cfg and overlay_data:
        overlay_tickets = [
            value["ticket"]
            for value in overlay_data.values()
            if value.get("ticket", 0) > 0
        ]
        if overlay_tickets:
            gp_billing_ticket_median = round(median(overlay_tickets), 2)
    ticket_monthly = gp_billing_ticket_median
    projection_ticket = (
        ticket_monthly * tm_recurrence_months if tm_recurrence_months else ticket_monthly
    )

    current_cps = div(current["media"], current["impressions"])
    min_cps = max(MIN_COST_PER_IMPRESSION, current_cps * 0.85)
    accumulated_revenue = sum(m["revenue"] for m in investment_months)
    accumulated_media = sum(m["media"] for m in investment_months)
    ref = reference_date or date.today()
    proj_months = projection_month_count(ref, end_year=PROJECTION_END_YEAR)
    gp_projection_months = gp_projection_trail(funnel_months, min(7, proj_months))
    media_samples = [m["media"] for m in funnel_months if m["media"] > 0]
    cps_samples = [
        div(m["media"], m["impressions"])
        for m in funnel_months
        if m["impressions"] > 0
    ]
    median_media = round(median(media_samples), 2) if media_samples else round(current["media"], 2)
    median_cps = median(cps_samples) if cps_samples else current_cps
    rate_months_pool = list(operational_months if operational_months else funnel_months)
    # Quando o mês de referência já foi excluído (exclude_reference_month), o último mês
    # fechado pode estar ausente do pool de taxas (ex.: Compras=0 → não entra em funnel_months).
    # Injeta-o via investment_months para a janela de baseline respeitar os 3 meses fechados.
    if profile.get("exclude_reference_month"):
        _last_closed_dt = date(ref.year, ref.month, 1) - timedelta(days=1)
        _last_closed_label = label_from_year_month(_last_closed_dt.year, _last_closed_dt.month)
        if _last_closed_label not in {m["label"] for m in rate_months_pool}:
            _extra = next((m for m in investment_months if m["label"] == _last_closed_label), None)
            if _extra is not None:
                rate_months_pool = rate_months_pool + [_extra]
    if profile.get("baseline_sales_months_only"):
        rate_months_pool = filter_sales_months(rate_months_pool)
    projection_baseline_months = select_projection_baseline_months(
        rate_months_pool,
        baseline_window=PROJECTION_BASELINE_MONTHS,
        skip_last=not bool(profile.get("exclude_reference_month")),
    )
    projection_baseline_labels = [month["label"] for month in projection_baseline_months]
    cpi_investment_pool = investment_months
    if profile.get("baseline_sales_months_only"):
        cpi_investment_pool = filter_sales_months(investment_months)
    cpi_baseline_months = select_cpi_baseline_months(
        cpi_investment_pool,
        traffic_key="impressions",
        baseline_window=PROJECTION_BASELINE_MONTHS,
    )
    cpi_baseline_labels = [month["label"] for month in cpi_baseline_months]
    baseline_cps_samples = [
        div(month["media"], month["impressions"])
        for month in cpi_baseline_months
        if month["impressions"] > 0
    ]
    # CPS de projeção = MEDIANA dos últimos 3 meses (não média nem acumulado): consistente com
    # as taxas (mesma janela 3M) e robusto a outlier. Decisão Rafael 2026-06-24.
    projection_cps = (
        median(baseline_cps_samples)
        if baseline_cps_samples
        else median_cps
    )
    projection_media = round(monthly_media, 2)
    gp_media_projection = [projection_media] * proj_months
    gp_cps_projection = [round(projection_cps, 8)] * proj_months
    gp_media_history = [{"label": m["label"], "media": round(m["media"], 2)} for m in investment_months]
    pre_funnel_count = len(investment_months) - len(funnel_months)
    funnel_lt_period = f"{funnel_months[0]['label']} a {funnel_months[-1]['label']}"
    impression_traceability = build_impression_traceability(
        funnel_months=funnel_months,
        investment_months=investment_months,
        funnel_lt_period=funnel_lt_period,
        projection_media=projection_media,
        projection_cps=projection_cps,
        traffic_key="impressions",
        cpi_baseline_labels=cpi_baseline_labels,
    )
    baseline_window_label = (
        f"mediana {len(projection_baseline_months)}M ({' · '.join(projection_baseline_labels)})"
        if projection_baseline_labels
        else f"mediana {PROJECTION_BASELINE_MONTHS}M"
    )
    if profile.get("baseline_sales_months_only") and projection_baseline_labels:
        baseline_window_label = (
            f"mediana {len(projection_baseline_months)}M com vendas "
            f"({' · '.join(projection_baseline_labels)})"
        )
    cpi_window_label = (
        f"mediana {len(cpi_baseline_months)}M ({' · '.join(cpi_baseline_labels)})"
        if cpi_baseline_labels
        else f"mediana {PROJECTION_BASELINE_MONTHS}M"
    )

    def median_funnel_rate(numerator_key: str, denominator_key: str) -> float:
        samples = [
            cap_rate(div(month[numerator_key], month[denominator_key]))
            for month in funnel_months
            if month[denominator_key] > 0
        ]
        return cap_rate(median(samples)) if samples else 0.0

    # Volumes medianos por etapa (ponto de partida M1 / Coluna Mediana). median_funnel_volume
    # ignora zeros, então um mês com ads pausada (vendas=0) não derruba a mediana das demais etapas.
    baseline_funnel_volumes = build_baseline_funnel_volumes(projection_baseline_months)

    # Baseline M1 = MEDIANA dos últimos 3 meses (não média): a média é inflada por outliers
    # (ex.: um mês de pico puxa o ponto de partida acima do nível recente real). Mesma lógica
    # anti-outlier dos tetos. Decisão Rafael 2026-06-24.
    #
    # Taxas DERIVADAS dos volumes medianos (razão das medianas), NÃO mediana das razões mensais.
    # Mediana de razões ≠ razão de medianas: usar a primeira fazia o funil não fechar
    # (ex.: 180.129 imp × 2,41% ≠ 1.683 cliques). Derivar do volume garante que cada etapa feche
    # exatamente: volume_etapa × taxa = volume_próxima_etapa. Decisão Rafael 2026-06-26.
    _prows = profile.get("rows", {})
    _rate_row_pairs = [
        ("impression_click", "clicks", "impressions"),
        ("click_lead", "leads", "clicks"),
        ("lead_mql", "mqls", "leads"),
        ("mql_sql", "sqls", "mqls"),
        ("sql_sale", "sales", "sqls"),
    ]

    def _derived_baseline_rate(num_key: str, den_key: str) -> float:
        raw = div(baseline_funnel_volumes.get(num_key, 0.0), baseline_funnel_volumes.get(den_key, 0.0))
        # >1.0 = amplificação orgânica legítima (ex.: Visitas > Cliques em marketplace) → sem cap 0.95.
        return raw if raw > 1.0 else cap_rate(raw)

    baseline_rates = {_rk: _derived_baseline_rate(_nk, _dk) for _rk, _nk, _dk in _rate_row_pairs}
    # Pass-through (numerador e denominador na MESMA linha do GP, ex.: alumtech leads=sqls=sales=L20)
    # → 1.0 exato. Amplificação orgânica (taxa derivada > 1.0) → multiplicador fixo (ceiling = baseline).
    _passthrough_rate_keys: set[str] = set()
    for _rk, _nk, _dk in _rate_row_pairs:
        if _prows.get(_nk) is not None and _prows.get(_nk) == _prows.get(_dk):
            baseline_rates[_rk] = 1.0
            _passthrough_rate_keys.add(_rk)
        elif baseline_rates[_rk] > 1.0:
            _passthrough_rate_keys.add(_rk)
    # Tetos de saturação ancorados na mediana dos ÚLTIMOS 3 MESES × folga (decisão Rafael 2026-06-24).
    # Projeção parte do desempenho recente; bench/acumulado seguem com todo o histórico.
    stage_ceilings = stage_ceilings_from_history(projection_baseline_months, baseline_rates)
    for _rk in _passthrough_rate_keys:
        # pass-through → 1.0; amplificação orgânica → baseline (multiplicador fixo)
        stage_ceilings[_rk] = baseline_rates[_rk]
    sales_baseline_months = [
        month for month in rate_months_pool if month.get("sales", 0) > 0
    ][-PROJECTION_BASELINE_MONTHS:]
    baseline_sales_avg = (
        baseline_funnel_volumes["sales"]
        if baseline_funnel_volumes["sales"] > 0
        else (
            median([month["sales"] for month in sales_baseline_months])
            if sales_baseline_months
            else (
                sum(month["sales"] for month in projection_baseline_months) / len(projection_baseline_months)
                if projection_baseline_months
                else current["sales"]
            )
        )
    )
    if baseline_rates["sql_sale"] <= 0 and profile.get("baseline_mode") == "operational":
        baseline_rates["sql_sale"] = PRE_REVENUE_SQL_SALE_FALLBACK
    if ticket_monthly <= 0 and profile.get("baseline_mode") == "operational":
        breakeven_pre_revenue = (monthly_fee + monthly_media) / margin
        assumed_sales = max(1.0, float(baseline_sales_avg) if baseline_sales_avg else 1.0)
        ticket_monthly = round(
            breakeven_pre_revenue / (tm_recurrence_months or 1) / assumed_sales,
            2,
        )
        projection_ticket = (
            ticket_monthly * tm_recurrence_months if tm_recurrence_months else ticket_monthly
        )
    recurrence_revenue_factor = tm_recurrence_months or 1

    def compound_rate_series(
        start_val: float,
        monthly_advance_pct: float,
        ceiling: float = MAX_CONVERSION_RATE,
    ) -> list[float]:
        # ceiling é o cap autoritativo por etapa (já incorpora MAX_CONVERSION_RATE para rates
        # reais via stage_ceilings_from_history; pass-through tem ceiling=1.0 explícito).
        cap = ceiling
        values = [min(cap, start_val)]
        current = values[0]
        for _ in range(1, proj_months):
            current = min(cap, current * (1 + monthly_advance_pct))
            values.append(current)
        return values

    def rate_series(rate_key: str, monthly_advance_pct: float) -> list[float]:
        """Cada mês: taxa = min(teto_etapa, taxa_mês_anterior × (1 + advance)).

        A saturação no teto por etapa substitui o cap único de 95%: evita que as
        taxas componham indefinidamente por 54 meses e estourem o funil.
        """
        return compound_rate_series(
            baseline_rates[rate_key],
            monthly_advance_pct,
            ceiling=stage_ceilings[rate_key],
        )

    def scenario_rate_series(stage_advances: dict[str, float]) -> dict[str, list[float]]:
        return {
            key: rate_series(key, stage_advances[key]) for key in FUNNEL_STAGE_KEYS
        }

    def scenario_ticket(idx: int) -> float:
        if tm_recurrence_months:
            return round(ticket_monthly, 2)
        return round(ticket_monthly * (1 + 0.005 * idx), 2)

    def scenario_revenue_from_media(
        media_series: list[float],
        *,
        imp_click: list[float],
        click_lead: list[float],
        lead_mql: list[float],
        mql_sql: list[float],
        sql_sale: list[float],
    ) -> list[float]:
        tickets = [scenario_ticket(idx) for idx in range(proj_months)]
        return [
            revenue_from_funnel(
                media_series[idx],
                impression_click=imp_click[idx],
                click_lead=click_lead[idx],
                lead_mql=lead_mql[idx],
                mql_sql=mql_sql[idx],
                sql_sale=sql_sale[idx],
                ticket=tickets[idx] * recurrence_revenue_factor,
                cps=gp_cps_projection[idx],
                baseline_volumes=baseline_funnel_volumes,
                month_idx=idx,
            )
            for idx in range(proj_months)
        ]

    breakeven_competence = (monthly_fee + monthly_media) / margin
    current_revenue = current["revenue"]
    sheet = sheet_name
    media_row = profile["media_row"]
    revenue_row = profile["revenue_row"]

    source_months = [
        [m["label"], monthly_fee, m["media"], m["impressions"], m["sqls"], m["sales"], m["revenue"]]
        for m in investment_months
    ]
    benchmark_months = [
        [
            m["label"],
            m["impressions"],
            m["clicks"],
            m["leads"],
            m["mqls"],
            m["sqls"],
            m["sqls"],
            m["sales"],
            m["sales"],
        ]
        for m in funnel_months
    ]
    current_funnel = {
        "sessions": current["impressions"],
        "page_view": current["impressions"],
        "view_item": current["clicks"],
        "add_to_cart": current["leads"],
        "view_cart": current["mqls"],
        "begin_checkout": current["sqls"],
        "add_shipping_info": current["sqls"],
        "add_payment_info": current["sales"],
        "orders": current["sqls"],
        "sales": current["sales"],
        "purchase": current["sales"],
        "revenue": current["revenue"],
        "media": current["media"],
    }
    previous = months[-2] if len(months) >= 2 else current
    # exclude_reference_month: col C = último mês fechado REAL (ref - 1, ex.: Mai/26 com ads
    # pausada ou 0 vendas), não o penúltimo do funil completo. O filtro FUNNEL_REQUIRED exige
    # vendas>0, então sem isto a coluna "último mês GP" pularia Mai/26 e mostraria Abr/26 —
    # confundindo a leitura do mês anterior. Vale para todos os modelos (IS, e-commerce, marketplace).
    col_c_use_previous_month = False
    if profile.get("exclude_reference_month"):
        _true_last_dt = date(ref.year, ref.month, 1) - timedelta(days=1)
        _true_last_label = label_from_year_month(_true_last_dt.year, _true_last_dt.month)
        _true_last = next((m for m in investment_months if m["label"] == _true_last_label), None)
        if _true_last and _true_last["label"] != current["label"]:
            previous = _true_last
            # current_funnel ficou no último mês COM vendas (mais antigo); a Col C deve usar
            # previous_month_funnel (o fechado real, ref-1). Sinaliza ao gerador para não
            # sobrescrever Col C com current_funnel (comportamento padrão IS/e-commerce).
            col_c_use_previous_month = True
    previous_month_funnel = {
        "sessions": previous["impressions"],
        "page_view": previous["impressions"],
        "view_item": previous["clicks"],
        "add_to_cart": previous["leads"],
        "view_cart": previous["mqls"],
        "begin_checkout": previous["sqls"],
        "add_shipping_info": previous["sqls"],
        "add_payment_info": previous["sales"],
        "orders": previous["sqls"],
        "sales": previous["sales"],
        "purchase": previous["sales"],
        "revenue": previous["revenue"],
        "media": previous["media"],
    }
    previous_month_label = previous["label"]

    def scenario_from_stage_advances(stage_advances: dict[str, float], color: str) -> dict:
        rates = scenario_rate_series(stage_advances)
        media_series = list(gp_media_projection)
        tickets = [scenario_ticket(idx) for idx in range(proj_months)]
        revenue = scenario_revenue_from_media(
            media_series,
            imp_click=rates["impression_click"],
            click_lead=rates["click_lead"],
            lead_mql=rates["lead_mql"],
            mql_sql=rates["mql_sql"],
            sql_sale=rates["sql_sale"],
        )
        return {
            "media": media_series,
            "revenue": revenue,
            "ticket": tickets,
            "session_view": rates["impression_click"],
            "view_add": rates["click_lead"],
            "view_cart_share": [
                rates["impression_click"][i] * rates["click_lead"][i] * rates["lead_mql"][i]
                for i in range(proj_months)
            ],
            "add_view_cart": rates["lead_mql"],
            "viewcart_checkout": rates["mql_sql"],
            "checkout_shipping": [1.0] * proj_months,
            "shipping_payment": rates["sql_sale"],
            "payment_order": [1.0] * proj_months,
            "order_sale": [1.0] * proj_months,
            "tab_color": color,
        }

    def scenario_media_v4(stage_advances: dict[str, float], color: str) -> dict:
        rates = scenario_rate_series(stage_advances)
        media_series = [round(value, 2) for value in gradual_linear(current["media"], monthly_media, proj_months)]
        tickets = [scenario_ticket(idx) for idx in range(proj_months)]
        revenue = scenario_revenue_from_media(
            media_series,
            imp_click=rates["impression_click"],
            click_lead=rates["click_lead"],
            lead_mql=rates["lead_mql"],
            mql_sql=rates["mql_sql"],
            sql_sale=rates["sql_sale"],
        )
        return {
            "media": media_series,
            "revenue": revenue,
            "ticket": tickets,
            "session_view": rates["impression_click"],
            "view_add": rates["click_lead"],
            "view_cart_share": [
                rates["impression_click"][i] * rates["click_lead"][i] * rates["lead_mql"][i]
                for i in range(proj_months)
            ],
            "add_view_cart": rates["lead_mql"],
            "viewcart_checkout": rates["mql_sql"],
            "checkout_shipping": [1.0] * proj_months,
            "shipping_payment": rates["sql_sale"],
            "payment_order": [1.0] * proj_months,
            "order_sale": [1.0] * proj_months,
            "tab_color": color,
            "editable_media": True,
            "media_ramp": {
                "from": round(current["media"], 2),
                "to": round(monthly_media, 2),
                "months": proj_months,
                "mode": "linear",
                "monthly_step": round((monthly_media - current["media"]) / max(1, proj_months - 1), 2),
                "note": (
                    f"Rampa linear até {PROJECTION_END_YEAR}: M1 = investimento {current['label']} (GP); "
                    f"último mês = mídia Flow (SR)."
                ),
            },
        }

    realista_advances = SCENARIO_STAGE_MONTHLY_ADVANCE["Realista"]
    realista_rates = scenario_rate_series(realista_advances)
    realista_scenario = scenario_from_stage_advances(realista_advances, "#5B9BD5")
    seasonal = seasonal_context.strip()

    config = {
        "client": manifest["name"],
        "project_model": "Marketplace" if profile.get("marketplace") else "Inside Sales",
        "funnel_has_lead_quali": False,
        "gp_profile": profile_name,
        "projection_rules": {
            "max_conversion_rate": MAX_CONVERSION_RATE,
            "min_cost_per_impression": min_cps,
            "media_lever_after_monthly_breakeven": False,
        },
        "media_projection_mode": "growthpack_monthly",
        "gp_media_monthly": gp_media_history,
        "gp_media_projection": gp_media_projection,
        "gp_cps_projection": [round(value, 8) for value in gp_cps_projection],
        "gp_projection_labels": [f"Flow R$ {projection_media:,.0f}"] * proj_months,
        "gp_projection_trail_reference": [month["label"] for month in gp_projection_months],
        "projection_end_year": PROJECTION_END_YEAR,
        "projection_month_count": proj_months,
        "projection_reference_date": ref.isoformat(),
        "projection_media_baseline": "flow_plan",
        "projection_media_flow": projection_media,
        "projection_media_median": median_media,
        "projection_cps_median": round(median_cps, 8),
        "projection_baseline_months": PROJECTION_BASELINE_MONTHS,
        "projection_baseline_labels": projection_baseline_labels,
        "projection_cpi_baseline_labels": cpi_baseline_labels,
        "projection_cps_baseline": round(projection_cps, 8),
        "projection_baseline_sales_avg": round(baseline_sales_avg, 2),
        "baseline_funnel_volumes": baseline_funnel_volumes,
        "projection_volume_mode": "baseline_median_volumes",
        "impression_traceability": impression_traceability,
        "current_period": f"{current['label']} fechado",
        "lt_period": f"{investment_months[0]['label']} a {investment_months[-1]['label']}",
        "funnel_lt_period": f"{funnel_months[0]['label']} a {funnel_months[-1]['label']}",
        "investment_months_count": len(investment_months),
        "funnel_months_count": len(funnel_months),
        "margin": margin,
        "monthly_fee": monthly_fee,
        "monthly_media": monthly_media,
        "ticket_monthly": round(ticket_monthly, 2),
        "gp_billing_ticket_median": round(gp_billing_ticket_median, 2),
        "projection_ticket": round(projection_ticket, 2),
        "baseline_funnel_rates": {key: round(value, 8) for key, value in baseline_rates.items()},
        "funnel_rate_baseline": "median_last_3",
        "funnel_rate_baseline_label": baseline_window_label,
        "funnel_rate_baseline_months": len(projection_baseline_months),
        "contract_from_label": from_label or None,
        "operational_months_count": len(operational_months) if operational_months else None,
        "last_month_funnel_label": current["label"],
        "source_mapping": {
            "fee": f"Strategy Review / Flow — fee R$ {monthly_fee:,.2f}; GP sem linha de fee mensal",
            "media": (
                f"Growth Pack > {sheet} > linha {media_row} Investimento (histórico mês a mês); "
                f"Flow R$ {monthly_media:,.0f} só na competência"
            ),
            "revenue": f"Growth Pack > {sheet} > linha {revenue_row} Receita Faturada",
            "funnel": profile["funnel_mapping"],
        },
        "source_months": source_months,
        "benchmark_months": benchmark_months,
        "current_funnel": current_funnel,
        "previous_month_funnel": previous_month_funnel,
        "previous_month_label": previous_month_label,
        "last_month_funnel_label": current["label"],
        "col_c_use_previous_month": col_c_use_previous_month,
        "minimum_scenario": {
            "revenue": list(realista_scenario["revenue"]),
            "media": list(gp_media_projection),
            "session_view": realista_rates["impression_click"],
            "view_add": realista_rates["click_lead"],
            "add_view_cart": realista_rates["lead_mql"],
            "viewcart_checkout": realista_rates["mql_sql"],
            "shipping_payment": realista_rates["sql_sale"],
            "sql_sale": realista_rates["sql_sale"],
            "add_cart_purchase": compound_rate_series(
                cap_rate(div(current["sales"], current["leads"])),
                realista_advances["sql_sale"],
            ),
            "approval_target": 1.0,
            "order_sale": [1.0] * proj_months,
        },
        "scenarios": {
            "Pessimista": scenario_from_stage_advances(
                SCENARIO_STAGE_MONTHLY_ADVANCE["Pessimista"],
                "#C55A11",
            ),
            "Realista": realista_scenario,
            "Otimista": scenario_from_stage_advances(
                SCENARIO_STAGE_MONTHLY_ADVANCE["Otimista"],
                "#70AD47",
            ),
            "Mídia V4": scenario_media_v4(
                SCENARIO_STAGE_MONTHLY_ADVANCE["Realista"],
                "#7030A0",
            ),
        },
        "scenario_sheet_order": ["Pessimista", "Realista", "Otimista", "Mídia V4"],
        "scenario_stage_monthly_advance": SCENARIO_STAGE_MONTHLY_ADVANCE,
        "stage_rate_ceilings": {key: stage_ceilings[key] for key in FUNNEL_STAGE_KEYS},
        "stage_rate_ceilings_basis": f"max(mediana últimos 3M, baseline M1) × {STAGE_CEILING_HEADROOM:g} (cap {MAX_CONVERSION_RATE:g})",
        "scenario_rate_advance_mode": "compound_monthly_by_stage_saturating",
        "context": {
            "product": f"{manifest['name']} — inside sales",
            "phase": f"Strategy Review — Growth Pack inside sales (perfil {profile_name})",
            "main_risk": (
                f"Receita faturada abaixo do breakeven da competência "
                f"(R$ {breakeven_competence:,.2f})."
            ),
            "seasonal": seasonal or None,
            "diagnosis": [
                *(
                    [f"Histórico contado a partir de {from_label} (início operacional do contrato)."]
                    if from_label
                    else []
                ),
                f"Investimento GP: {len(investment_months)} meses ({investment_months[0]['label']}–{investment_months[-1]['label']}).",
                f"Funil completo: {len(funnel_months)} meses ({funnel_months[0]['label']}–{funnel_months[-1]['label']}).",
                *(
                    [
                        f"Baseline projeção: mediana {PROJECTION_BASELINE_MONTHS}M apenas em meses com vendas "
                        f"({' · '.join(projection_baseline_labels)})."
                    ]
                    if profile.get("baseline_sales_months_only") and projection_baseline_months
                    else [
                        f"Baseline taxas/CPS: mediana {PROJECTION_BASELINE_MONTHS}M sobre "
                        f"{len(projection_baseline_months)} meses operacionais "
                        f"({' · '.join(projection_baseline_labels)})."
                    ]
                    if profile.get("baseline_mode") == "operational" and operational_months
                    else []
                ),
                *(
                    [
                        f"Inclui {pre_funnel_count} meses pré-funil no investimento acumulado "
                        f"(mídia contabilizada antes do tracking MQL→venda fechar)."
                    ]
                    if pre_funnel_count > 0
                    else []
                ),
                f"Faturamento acumulado (GP): R$ {accumulated_revenue:,.2f}.",
                f"Investimento acumulado (GP linha {media_row}): R$ {accumulated_media:,.2f}.",
                f"Breakeven da competência: R$ {breakeven_competence:,.2f} (fee R$ {monthly_fee:,.0f} + mídia Flow R$ {monthly_media:,.0f} / margem {margin:.0%}).",
                f"Projeção (análise): M1 = medianas de volume ({baseline_window_label}: "
                f"{baseline_funnel_volumes['impressions']:,.0f} imp · {baseline_funnel_volumes['sales']:.0f} vendas) "
                f"+ taxas medianas; M2+ cresce taxas por cenário. "
                f"CPI mediano (referência Flow): R$ {projection_cps:.4f}/impressão → "
                f"{impression_traceability['projection_m1_volume']:,.0f} imp se fosse só mídia÷CPI.",
                impression_traceability["projection_note"],
                f"Taxas funil: baseline mediana {PROJECTION_BASELINE_MONTHS}M + evolução mensal composta por etapa — "
                f"Pessimista ({format_stage_advances(SCENARIO_STAGE_MONTHLY_ADVANCE['Pessimista'])}); "
                f"Realista ({format_stage_advances(SCENARIO_STAGE_MONTHLY_ADVANCE['Realista'])}); "
                f"Otimista ({format_stage_advances(SCENARIO_STAGE_MONTHLY_ADVANCE['Otimista'])}).",
                f"Receita projetada (LTV) = faturamento mensal GP × {tm_recurrence_months or 1} "
                f"(vendas do funil × ticket GP mensal mediano R$ {ticket_monthly:,.2f}"
                + (f" × {tm_recurrence_months} meses SR)" if tm_recurrence_months else ")")
                + " — não composto sobre faturamento isolado do último mês.",
                f"Coluna mês anterior: funil {previous_month_label} ({previous['sales']:.0f} vendas); "
                f"LTV = faturamento GP R$ {previous['revenue']:,.2f} × {tm_recurrence_months or 1}.",
                f"Coluna meta breakeven (funil): vendas NECESSÁRIAS = breakeven mensal ÷ ticket GP — não confundir com realizado histórico; volumes reverso taxas média {PROJECTION_BASELINE_MONTHS}M.",
                f"Projeção até {PROJECTION_END_YEAR}: {proj_months} meses — M1 medianas 3M + evolução de taxas por cenário; mídia Flow na competência.",
                f"Aba Mídia V4: rampa investimento R$ {current['media']:,.0f} → R$ {monthly_media:,.0f} (Flow) + funil Realista por etapa; receita derivada do funil.",
                f"Último mês ({current['label']}): investimento R$ {current['media']:,.0f}, faturamento R$ {current_revenue:,.2f}, {current['sales']:.0f} vendas.",
                *(
                    [
                        f"MRR (SR col. L): {tm_recurrence_raw} → LTV = faturamento mensal GP × {tm_recurrence_months} "
                        f"(projeção ≈ R$ {projection_ticket:,.2f}/venda = ticket GP mediano R$ {ticket_monthly:,.2f} × {tm_recurrence_months}). "
                        "Vendas vêm do funil forward ancorado no mês anterior GP; histórico acumulado permanece real (GP)."
                    ]
                    if tm_recurrence_months
                    else []
                ),
                profile["funnel_note"],
            ],
            "actions": [
                "Recuperar taxa SQL→venda e volume de MQLs com cadência comercial",
                "Validar tracking Meta/Google vs CRM nas etapas Leads→MQL→SQL",
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
        "\n".join(
            [
                f"# Gate — {manifest['name']}",
                "",
                f"- Projeto: {manifest['name']}",
                "- Escopo: **Inside Sales** (funil 6 etapas — **sem lead quali**)",
                f"- Perfil GP: `{profile_name}`",
                f"- Growth Pack ({gp_source_used}): [{manifest['name']}]({manifest['growthpack_updated_link']})",
                f"- Investimento GP: {config['lt_period']} ({len(investment_months)} meses, incl. pré-funil)",
                f"- Funil completo: {config['funnel_lt_period']} ({len(funnel_months)} meses)",
                f"- Faturamento acumulado: R$ {accumulated_revenue:,.2f}",
                f"- Investimento acumulado (GP linha {media_row}): R$ {accumulated_media:,.2f}",
                f"- Projeção análise: {proj_months} meses até {PROJECTION_END_YEAR} · mídia Flow R$ {projection_media:,.0f}/mês",
                f"- Fee competência: R$ {monthly_fee:,.2f}",
                f"- Mídia competência (Flow — referência): R$ {monthly_media:,.2f}",
                f"- Margem: {margin:.0%}",
                f"- Breakeven competência: R$ {breakeven_competence:,.2f}",
                *(
                    [
                        f"- Ticket GP mensal (mediana): R$ {ticket_monthly:,.2f}",
                        f"- LTV projeção: faturamento mensal × {tm_recurrence_months} ≈ R$ {projection_ticket:,.2f}/venda",
                    ]
                    if tm_recurrence_months
                    else []
                ),
                f"- Taxas funil ({proj_months}M) — evolução mensal composta por etapa:",
                f"  · Pessimista: {format_stage_advances(SCENARIO_STAGE_MONTHLY_ADVANCE['Pessimista'])}",
                f"  · Realista: {format_stage_advances(SCENARIO_STAGE_MONTHLY_ADVANCE['Realista'])}",
                f"  · Otimista: {format_stage_advances(SCENARIO_STAGE_MONTHLY_ADVANCE['Otimista'])}",
                f"- Aba Mídia V4: mídia R$ {current['media']:,.0f} → R$ {monthly_media:,.0f} + funil Realista por etapa",
                f"- Vendas M1 projetadas (Realista): ~{baseline_sales_avg:.0f}/mês na base (média vendas {PROJECTION_BASELINE_MONTHS}M)",
                "- Funil breakeven: impressões → cliques → leads → MQL → SQL → vendas",
                f"- {profile['funnel_note']}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera config inside sales a partir do Growth Pack.")
    parser.add_argument("--project-folder", type=Path, required=True)
    parser.add_argument("--profile", choices=sorted(GP_PROFILES), default="primeset")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--lt-months", type=int, default=0)
    parser.add_argument("--seasonal-context", type=str, default="")
    parser.add_argument("--seasonal-context-file", type=Path, default=None)
    parser.add_argument("--reference-date", type=str, default=None, help="ISO YYYY-MM-DD (horizonte até 2030)")
    parser.add_argument(
        "--gp-source",
        choices=("online", "local", "auto"),
        default="online",
        help="Fonte do Growth Pack: online (Sheets API, padrão), local (.xlsx) ou auto",
    )
    parser.add_argument(
        "--from-label",
        type=str,
        default="",
        help="Conta histórico e projeção a partir deste mês GP (ex.: Jan/26)",
    )
    args = parser.parse_args()

    ref_date = (
        datetime.strptime(args.reference_date, "%Y-%m-%d").date()
        if args.reference_date
        else None
    )

    seasonal = args.seasonal_context
    if args.seasonal_context_file and args.seasonal_context_file.exists():
        seasonal = args.seasonal_context_file.read_text(encoding="utf-8").strip()

    out = build_config(
        project_folder=args.project_folder,
        profile_name=args.profile,
        lt_months=args.lt_months,
        seasonal_context=seasonal,
        output=args.output,
        reference_date=ref_date,
        gp_source=args.gp_source,
        from_label=args.from_label.strip(),
    )
    print(out)


if __name__ == "__main__":
    main()
