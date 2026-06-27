# Histórico de Sessões — Breakeven Auto (até 2026-06-24)

> Arquivado de `status.md` em 2026-06-25 para reduzir contexto ativo.
> Para consulta histórica apenas — não é contexto ativo.

---

## Mold Systems v6–v26 (2026-06-22/23)

v26 (correções definitivas):
- Defeito 1: saturação do funil com teto por etapa → `max(mediana 3M, baseline) × 1,1`
- Defeito 2: Breakeven 7M col. C legacy (motor legacy inflava vendas)
- Defeito 3: dependência circular `#REF!` no Google Sheets (previous_col não recalculado por iteração → fix `previous_col = xl_col_to_name(col-1)`)
- Defeito 4: coluna D breakeven competência 12× inflada (sem dividir pela recorrência)
- Defeito 5: Resumo "Ticket Mínimo" hardcoded errado → usa `projection_ticket`
- Defeito 6: aba Breakeven 7M 6 etapas não reconciliava (CPS acumulado vs baseline, linha 10 forçava 100%, funil de baixo copiava topo)
- Strategy Review: col mapeada nova ("Retrospectiva By AI"): sazonal O→P, GrowthPack M→N, breakeven antigo L→M
- `extra_stage_label` configurável (default "Lead quali")
- Entrega final MSYS v26: https://docs.google.com/spreadsheets/d/1u_JUUJ0awc8IUyycF1VSlj7OO_hO2yiVpojMtnzxTDg/edit?usp=drivesdk

v25: tabela Premissas funil × cenários (A18:D32), `compound_stage_rate_formula()`
v24–v22: avanços mensais por etapa distintos por cenário
v21: +7%/mês composto em todas as etapas
v20: projeção média 3M (Mar–Mai/26), não mediana 13M
v19: LTV = faturamento mensal GP × 12 (não vendas × TM × 12)
v18: horizonte Jul/26 → Dez/30 (54M), `PROJECTION_END_YEAR = 2030`
v17: mediana + Flow; v16: projeção para o breakeven; v15: fix CPS + gráfico
v14: fix #REF! Comparativo; v13–v10: LTV, col. D funil reverso
v6: mediana + funil último mês (Jun/26)

## Primeset v1–v10 (2026-06-23)

- v10 (final): Fee R$ 5.278,66; breakeven competência R$ 159.216; déficit ~−R$ 167.936
- Rampa Mídia V4: linear 7M, passo ~R$ 5.939/mês (24.363 → 60.000)
- v9: Aba Mídia V4 funil Realista (+7%)
- v8: Nova aba Mídia V4 (rampa)
- v7: taxas em todo o documento (5 etapas, Premissas + Breakeven 7M + Funil Completo)
- v6: avanços moderados Pessimista +3% / Realista +7% / Otimista +10% (cap 95%)
- v5: projeção usa linha 5 GP mês a mês; v4: acumulado col B; v3: cenários progressivos
- v2: histórico completo Mai/25–Jun/26; funil 6 etapas nativo GP
- Entrega final: https://docs.google.com/spreadsheets/d/131i6t_tLCQ3ar5o7d3xnZem9J9DhqTks8yg_1DU61gc/edit?usp=drivesdk

## O3NT v1–v2 (2026-06-23)

- E-commerce D2C; GP 3.0 aba 6.0; Fee R$ 5.000 · Mídia R$ 4.100 · Margem 40%
- v2: `projection_rules` (alavanca mídia, CPS mínimo 0,86), aba Breakeven unificada v16, sazonalidade SR col. O
- Entrega v2: https://docs.google.com/spreadsheets/d/1nXeozUN1n2xsFqKg2u_L5aBYUw6nqwiIxMtmkLay_8U/edit?usp=drivesdk

## Centro do Silicone v1 (2026-06-23)

- Builder genérico; perfil `cdsi`; histórico Jan/25–Jun/26; breakeven competência R$ 28.456,40
- Entrega: https://docs.google.com/spreadsheets/d/1MKOrxsf70zUlU6Ijm3Lb-rgfWSQIP0QRfKeK3X9imZI/edit?usp=drivesdk

## BUBLU v1 (2026-06-24)

- E-commerce D2C; builder `build_bublu_ecommerce_config.py`; Fee R$ 6.455 · Margem 28%
- Fix gerador: `minimum_full_rates` e-commerce (listas vazias quebravam geração)
- Não breakeva em 72M no Realista
- Entrega: https://docs.google.com/spreadsheets/d/1JlazG1Fn8LMf3-vvtPjlJJ_N8z6ZDgj-TuPyZhWYSUI/edit?usp=drivesdk

## Mold Systems v1 (2026-06-23)

- Perfil `msys`; aba `6.0 Acompanhamento Mensal` (ano/mês texto, funil L7–17)
- Histórico Jun/25–Jun/26; breakeven competência R$ 67.281,67

## Soma Soluções (2026-06-22) — desenvolvimento inicial

- v1–v11: evolução do motor inside sales a partir do template e-commerce
- v11 (entrega de referência): https://docs.google.com/spreadsheets/d/1PCcoCc9tvSqrBMHldiAwhfNk2G7wqBpnspu7fV1hEuM/edit?usp=drivesdk
- Padrão de nomenclatura estabelecido: `[Colli & CO] - [Cliente] - Breakeven Inside Sales|E-commerce - AI Auto`

## Leitura online GP (2026-06-24)

- `growthpack_sheets_reader.py` — Sheets API + Drive export em memória, sem download
- Builder IS usa `--gp-source online` por padrão
- Pré-requisito: Sheets API habilitada no GCP (atualmente `SERVICE_DISABLED`)

## Setup inicial QGI (2026-06-21/22)

- Projeto criado; vendor autobreakeven copiado
- Scripts: `build_strategy_review_manifest.py`, `prepare_strategy_review_projects.py`, `download_growthpacks.py`, `inspect_downloaded_growthpacks.py`
- 74 projetos SR: 49 ready, 11 needs-review, 14 blocked
