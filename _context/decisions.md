# Decisions — Breakeven Auto

## 2026-06-20 — Projeto criado no QGI

- **Origem:** repo [jeffersonvieira-hue/autobreakeven](https://github.com/jeffersonvieira-hue/autobreakeven) (skill `breakeven-projetos`, Python, portátil Codex/Claude/Cursor).
- **Escopo Invictus:** carteira da aba **Start Strategy Review** (74 projetos, HS ordenado).
- **Link Growth Pack:** coluna Cockpit **GrowthPack Atualizado** → `paid_traffic_growthpack_updated_link` (vertical Gestão de Tráfego). Distinto de `results_breakeven_spreadsheet_link` (Break-even/Resultados).
- **Fee:** `fee` (Cockpit).
- **Mídia:** `campaigns_budget_milestone_total_qty` (total investimento previsto Meta+Google consolidado no Flow).
- **Margem:** `results_contribution_margin_pct`.
- **Vendor:** cópia em `vendor/autobreakeven/` — atualizar via git pull manual ou re-copy; não submodule ainda.
- **MCP:** reutiliza `projects/monitor-invictus/ingest/lib/mcp_client.py` e tokens `.env` do Monitor/Tático.
- **Separado de** `breakeven-dashboard` (Node, conversacional, porta 3010) — projetos complementares.

## 2026-06-22 — Funil deve ser nativo do Growth Pack

- **Decisão:** não encaixar todos os projetos no funil e-commerce padrão da skill.
- **Regra para e-commerce:** manter o funil e-commerce já usado pela skill quando o Growth Pack trouxer esse funil: sessões, view item, add cart, checkout/payment/purchase e faturamento.
- **Regra para inside sales:** analisar o Growth Pack e usar exatamente o funil encontrado ali como base dos cálculos e projeções.
- **Exemplo Soma:** o funil correto é `impressões → cliques → leads → lead quali → MQLs → SQLs → vendas → faturamento` (lead quali = GP linha 19).
- **Implicação:** cada projeto pode ter etapas diferentes; o gerador precisa suportar funil dinâmico por cliente.
- **Proibido:** inventar etapas intermediárias ou mapear inside sales para `view item/add cart/checkout` quando essas etapas não existem no Growth Pack.
- **Horizonte:** não travar projeção em 7 meses. A projeção deve rodar até o breakeven acontecer, ou parar em um limite explícito quando o cenário não breakevar em prazo razoável.
- **Saída esperada:** relatório e planilha devem mostrar o mês real de breakeven por cenário, seja antes, no mês 7, ou depois.
- **Breakeven histórico:** se o projeto já estiver breakeven positivo com os dados históricos do Growth Pack, sinalizar explicitamente que o breakeven já foi atingido e separar isso da projeção futura.

## 2026-06-22 — Frente inside sales separada do e-commerce

- **Decisão:** todas as adaptações de funil, labels e abas da planilha Jefferson para inside sales ficam **atrás** de `project_model: "Inside Sales"` no config JSON e de `is_inside_sales_model()` no gerador.
- **E-commerce intocável:** quando `project_model` não contém `"inside sales"`, `generate_breakeven.py` executa o caminho original (sessões, view item, checkout, shipping, payment, purchase). Nenhuma label ou coluna inside sales aparece.
- **Template visual:** manter as 8 abas e layout da skill; inside sales altera **conteúdo** (labels, funil, fórmulas), não a estrutura de arquivo.
- **Funil inside sales (Soma, 7 etapas):** impressões → cliques → leads → **lead quali** → MQLs → SQLs → vendas. Flag `funnel_has_lead_quali: true` no config.
- **Funil inside sales (6 etapas):** quando o GP não tem lead quali, impressões → cliques → leads → MQLs → SQLs → vendas.
- **Última taxa operacional:** SQLs → Vendas. Conversão final exibida: Leads → Vendas.
- **Proibido no inside sales:**
  - Duplicar volumes para preencher colunas e-commerce (SQLs/SQLs, Vendas/Vendas).
  - Exibir “Etapa neutra”, “Vendas → Vendas”, “SQLs → SQLs” ou taxas `Checkout → Shipping` / `Payment → Purchase` no bench.
  - Usar conversão impressões → vendas como “taxa de conversão do funil” (~0,01%).
- **Dados Fonte (inside sales):** bench com 7 colunas (Mês + 6 etapas) e 6 taxas mediana; Premissas usa “Impressões acumuladas” e “SQLs acumulados”.
- **Linhas vazias no grid:** linhas 46–52 (aba Breakeven) e 26–31 (cenários) ficam sem label — restos do template e-commerce, não etapas do GP.
- **Horizonte:** projeção até breakeven, máximo 36 meses (`MAX_PROJECTION_MONTHS`).
- **Mapeamento interno config:** chaves e-commerce da skill reutilizadas (`session_view`, `view_add`, …); `shipping_payment` = taxa SQLs → Vendas; `checkout_shipping`, `payment_order`, `order_sale` = `[1.0]` internamente, **sem exibição**.
- **Scripts QGI:** `build_soma_inside_sales_template_config.py` (config piloto), `relabel_inside_sales_template.py` (PT + refs aba), pipeline em `docs/inside-sales-breakeven.md`.
- **Piloto validado:** Soma ordem 17 — Google Sheets v11 (jun/2026); v12 corrige bench Leads → Vendas.
- **Premissas Leads → Vendas:** Mês 1 = taxa do mês atual; evolução gradual editável — não usar mediana do bench fixa.

## 2026-06-22 — Aba Breakeven unificada (v16)

- **Decisão Rafael:** a parte superior da aba Breakeven deve refletir o **funil completo** do projeto (taxas das Premissas + volumes), não atalhos como Impressões→SQLs ou SQLs→Vendas a 100%.
- **Concatenação:** eliminar o bloco inferior *Funil completo do cenário mínimo* — custos, funil e financeiro num único fluxo.
- **Headers:** linha 2 entre título e dados (`Indicador`, `Feito até o momento`, `Cenário mínimo NM`, meses).
- **Implementação:** `breakeven_unified_sheet.py` quando `(is_inside_sales and funnel_has_lead_quali) or (not is_inside_sales)` — inside sales 6 etapas mantém layout legacy.
- **E-commerce unificado (v18):** mesmas 6 taxas operacionais nas Premissas (Sessão→View item … Pedido→Venda) + linha calculada Sessão→Venda; labels do funil GA4 na aba Breakeven.
- **Piloto validado:** Soma v16 — https://docs.google.com/spreadsheets/d/1l1QZQT5obJc3HSpCv75-PtYKNXWvBFX0Ul4QNuqIqsI/edit?usp=drivesdk

## 2026-06-22 — Personalização e alinhamento de cenários (v17)

- **Proibido:** textos hardcoded do template Dalpack (ex.: R$ 5 mil, “funil maio”, título “E-commerce” em inside sales).
- **Textos:** `breakeven_personalization.py` monta Leitura estratégica a partir de `monthly_media`, `monthly_fee`, `margin`, `context.diagnosis`, `context.main_risk`, `source_mapping`.
- **Motor financeiro único:** `breakeven_projection.py` — Breakeven, Pessimista/Realista/Otimista e Resumo Executivo usam a mesma lógica (MC, alavanca de mídia após resultado mensal ≥ 0).
- **Breakeven acumulado vs mensal:** breakeven mensal pode ser Mês 14; acumulado (recuperar déficit) Mês 29 porque alavanca de mídia (+5%/mês após mês positivo) eleva custos.
- **Realista = cenário mínimo:** `minimum_scenario.revenue` deve ser a mesma série do Realista no config builder.
- **Resumo Executivo:** linha explícita “Cenário mínimo (Breakeven)” referenciando aba Breakeven; cenários com BEP recalculado pelo motor compartilhado.
- **Piloto validado:** Soma v17 — https://docs.google.com/spreadsheets/d/1PCcoCc9tvSqrBMHldiAwhfNk2G7wqBpnspu7fV1hEuM/edit?usp=drivesdk

## 2026-06-22 — Contexto sazonal Strategy Review (col. O)

- **Decisão Rafael:** a coluna **Contexto do projeto (Datas sazonais)** da Strategy Review é insumo estratégico obrigatório no breakeven (Leitura estratégica / Resumo), não apenas metadado.
- **Implementação:** `read_strategy_review_row.py` lê col. O; builders gravam `context.seasonal` e `strategy_review_context` no config; `breakeven_personalization.py` inclui bloco sazonal na leitura.
- **Regra:** ao regenerar qualquer cliente, consultar col. O e refletir campanhas, mix de produtos e picos de demanda nas ações e no texto estratégico.

## 2026-06-22 — Motor compartilhado inside sales + e-commerce

- **Decisão Rafael:** motor financeiro (`breakeven_projection.py`), personalização (`breakeven_personalization.py`), Realista = mínimo, Mês 1 = taxa atual, cap 95% e `projection_rules` valem para **ambos** os modelos; só muda o funil (GP + `project_model`).
- **Alavanca mídia:** `media_lever_after_monthly_breakeven: true` + `min_cost_per_impression` calibrado do GP (CPS mínimo).
- **E-commerce:** aba Breakeven unificada v16+ (mesmo módulo que inside sales + lead quali).

## 2026-06-23 — Cabeçalhos calendário nos cenários

- **Decisão Rafael:** abas Pessimista/Realista/Otimista exibem meses reais (`Jul/26`), não `Mês 1`.
- **Regra:** dia da geração ≤15 → 1ª coluna = mês seguinte; dia ≥16 → 1ª coluna = mês subsequente (+2).
- **Implementação:** `projection_month_headers()` em `breakeven_projection.py`; CLI `--reference-date`.

## 2026-06-22 — Nomenclatura de entrega Colli & CO

- **Padrão:** `[Colli & CO] - [Nome do Cliente] - Breakeven [Inside Sales | E-commerce] - AI Auto`
- **Google Sheets e `.xlsx` local** usam o mesmo título (sem sufixo de versão no nome canônico).
- **Implementação:** `src/integrations/breakeven_naming.py`; `generate_breakeven.py` (default `--output`) e `upload_xlsx_to_google_sheet.py` (`--config` deriva `--name`).
- **Soma:** entregas v1–v18 mantêm nomes antigos; próximos clientes seguem o padrão.
