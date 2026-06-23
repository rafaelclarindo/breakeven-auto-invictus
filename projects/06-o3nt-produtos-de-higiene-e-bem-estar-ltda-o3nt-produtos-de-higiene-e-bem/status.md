# Status — O3NT PRODUTOS DE HIGIENE E BEM ESTAR LTDA

**Atualizado:** 2026-06-23  
**Status:** `uploaded_v3_calendar_headers`  
**Ordem Strategy Review:** 6 · **Linha SR:** 70

## Entrega

- **Google Sheets:** https://docs.google.com/spreadsheets/d/1s_N2z3IwO4BbE0ToHWwoXFIheeLruD9nmZ3fijkYUys/edit?usp=drivesdk
- **Título:** `[Colli & CO] - [O3NT …] - Breakeven E-commerce - AI Auto`
- **Local:** `spreadsheet/o3nt-breakeven.xlsx`

## Premissas (Flow + SR linha 70)

| Campo | Valor |
|-------|------:|
| Fee | R$ 5.000 |
| Mídia | R$ 4.100 |
| Margem | 40% |
| Breakeven competência | R$ 22.750 |
| Modelo | E-commerce D2C |
| LT | Dez/25 – Jun/26 (7 meses) |
| Último mês | Jun/26 — faturamento R$ 6.080 |

## v3 — cabeçalhos calendário nos cenários

- Colunas Pessimista / Realista / Otimista: **Jul/26, Ago/26, …** (geração 22/jun/2026 → mês seguinte).
- Skill consolidada em `SKILL.md` + push GitHub.

## v2 — motor compartilhado + aba unificada

- `projection_rules`: alavanca de mídia (+5% após mês positivo), CPS mínimo **R$ 0,86** (85% do CPS real Jun/26).
- Aba **Breakeven 7M unificada** (v16 e-commerce): funil GA4 completo + financeiro; Premissas com 6 taxas + Sessão→Venda calculada.
- **Contexto sazonal** (SR col. O) em `config.context.seasonal` e Leitura estratégica no Resumo.

## Pipeline executado

1. Growth Pack (`source/growthpack.xlsx`)
2. Config via `build_config_from_growthpack_acompanhamento.py` + `source/seasonal-context.txt`
3. `validate_config.py` → OK
4. `generate_breakeven.py` → planilha v2
5. Upload Google Sheets (link público leitor)

## Observações

- Funil intermediário: taxas **4.2 Funil** (Mai–Jun/2026); volumes do **6.0 Acompanhamento Mensal**.
- Fee no GP variou (R$ 8.000 histórico → R$ 5.100 recente); projeção usa Flow/SR.
- v1 (layout legacy): https://docs.google.com/spreadsheets/d/1AByMatMbQyFLJVORIS5HJCXf4ttOu46CbJm5AphuZVg/edit?usp=drivesdk
