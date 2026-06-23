# Status — FABIO LUCHESI (Primeset)

**Atualizado:** 2026-06-23  
**Status:** `uploaded`  
**Ordem Strategy Review:** 44 · **Linha SR:** 45

## Entrega

- **Google Sheets:** https://docs.google.com/spreadsheets/d/13Xba49hj2T3XtPIYLMb7ItG6rnNu1feu1K98-oQ1MyI/edit?usp=drivesdk
- **Título:** `[Colli & CO] - [FABIO LUCHESI (Primeset)] - Breakeven Inside Sales - AI Auto`
- **Local:** `spreadsheet/primeset-breakeven.xlsx`
- **Growth Pack:** [INSIDE SALES PRIMESET V1](https://docs.google.com/spreadsheets/d/1cLMVytMO4Jq0GBAfJegc7EKvU-f-h9tEWeiPSc71Q5U/edit?usp=sharing)

## Premissas (Flow + SR linha 45)

| Campo | Valor |
|-------|------:|
| Fee | R$ 15.836 |
| Mídia | R$ 60.000 |
| Margem | 41% |
| Breakeven competência | R$ 185.941 |
| Modelo | Inside Sales + Lead quali (Ploomes) |
| LT | Mar/26 – Jun/26 (4 meses) |
| Último mês | Jun/26 — faturamento R$ 12.326 |

## Pipeline

1. GP baixado (`source/growthpack.xlsx`)
2. Config via `build_primeset_inside_sales_config.py` (layout GP Primeset — linhas 5–17)
3. `validate_config.py` → OK
4. `generate_breakeven.py` → aba Breakeven unificada v16
5. Upload Google Sheets (link público leitor)

## Observações

- Fee mensal V4 não existe no GP; usa Flow/SR (R$ 15.836).
- Mídia competência Flow (R$ 60k) vs investimento realizado histórico no GP (variável).
- Jun/26 com queda forte de vendas (18) e receita — cenário mínimo puxado pelo breakeven da competência.
