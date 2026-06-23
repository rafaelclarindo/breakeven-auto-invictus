# Snapshot — Inside Sales Breakeven (2026-06-22)

Sessão de consolidação após piloto Soma. Rafael confirmou: **ajustes são só para inside sales; e-commerce não deve ser alterado.**

## Entregável canônico

- **Google Sheets v11:** https://docs.google.com/spreadsheets/d/1F8kYLiPUxq-yxX7TIJT2-VtSnBmWSEfI_886y859x7c/edit?usp=drivesdk
- **XLSX local:** `projects/17-soma-solucoes-financeiras-ltda/spreadsheet/Soma Soluções - Breakeven Inside Sales v11.xlsx`
- **Config:** `projects/17-soma-solucoes-financeiras-ltda/config-inside-sales-template.json`
- **Playbook:** `docs/inside-sales-breakeven.md`

## Decisões-chave desta sessão

1. Ramificação `is_inside_sales` em `generate_breakeven.py` — e-commerce permanece no `else`.
2. Funil inside sales = 6 etapas; última taxa operacional = SQLs → Vendas.
3. Dados Fonte bench: 6 colunas de volume + 6 taxas (sem duplicatas).
4. Template visual Jefferson preservado; linhas e-commerce extras ficam vazias.
5. Projeção dinâmica até breakeven (max 36 meses).
6. Taxa de conversão do funil = Leads → Vendas (não impressões → vendas).

## Arquivos modificados na frente inside sales

- `vendor/autobreakeven/breakeven-projetos/scripts/generate_breakeven.py`
- `src/integrations/relabel_inside_sales_template.py`
- `src/integrations/build_soma_inside_sales_template_config.py` (config builder piloto)

## Próximo passo operacional

Generalizar `build_soma_inside_sales_template_config.py` e replicar pipeline §5 do playbook para demais clientes inside sales da Strategy Review.
