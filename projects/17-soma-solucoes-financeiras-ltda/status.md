# Status — SOMA SOLUCOES FINANCEIRAS LTDA

**Atualizado:** 2026-06-22  
**Status:** `uploaded_v17_personalizado_cenarios_alinhados`  
**Ordem Strategy Review:** 17

## Entrega canônica (usar esta)

| Item | Link / caminho |
|------|----------------|
| **Google Sheets v17** | https://docs.google.com/spreadsheets/d/1PCcoCc9tvSqrBMHldiAwhfNk2G7wqBpnspu7fV1hEuM/edit?usp=drivesdk |
| XLSX local | `spreadsheet/soma-inside-sales-v17.xlsx` |
| Config | `config-inside-sales-template.json` |
| Playbook frente | `../../docs/inside-sales-breakeven.md` |

## v17 — Personalização + cenários alinhados

- **Textos do config/GP** — Leitura estratégica usa fee, mídia, margem e `context` do projeto (não mais template Dalpack).
- **Motor financeiro único** — Breakeven, Pessimista/Realista/Otimista e Resumo com mesma lógica (incl. alavanca de mídia).
- **BEP acumulado Mês 29** — Realista agora coincide com cenário mínimo (Breakeven); antes Realista mostrava Mês 25 por não aplicar alavanca.
- Resumo Executivo: linha **Cenário mínimo (Breakeven)** + comparativo com meses de breakeven corrigidos.

## Resultado do teste

- Breakeven mensal: R$ 248.000,00
- Resultado líquido acumulado histórico: -R$ 150.700,85
- Cenário mínimo / Realista: breakeven acumulado **Mês 29**; Otimista **Mês 18**; Pessimista **não breakeva**
- QA: `qa.json`

## Próximo passo

Generalizar `build_soma_inside_sales_template_config.py` → `build_inside_sales_template_config.py` para outros GPs.
