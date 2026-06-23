# Status — Breakeven Auto

**Atualizado:** 2026-06-23  
**Status:** Primeset (SR linha 45) entregue + O3NT v3

## Sessão 2026-06-23 — Primeset (FABIO LUCHESI, SR linha 45)

- Inside Sales + Lead quali (Ploomes); builder `build_primeset_inside_sales_config.py` (GP linhas 5–17).
- Premissas: Fee R$ 15.836 · Mídia R$ 60.000 · Margem 41% · LT Mar–Jun/26.
- Entrega: https://docs.google.com/spreadsheets/d/13Xba49hj2T3XtPIYLMb7ItG6rnNu1feu1K98-oQ1MyI/edit?usp=drivesdk

## Sessão 2026-06-23 — Cabeçalhos calendário + skill GitHub

- Cenários: meses calendário (`Jul/26`, …) — 1ª coluna = mês seguinte à geração.
- Skill consolidada: `SKILL.md` (Invictus + upstream Jefferson).
- Repo: https://github.com/rafaelclarindo/breakeven-auto-invictus
- O3NT v3: https://docs.google.com/spreadsheets/d/1nXeozUN1n2xsFqKg2u_L5aBYUw6nqwiIxMtmkLay_8U/edit?usp=drivesdk

## Sessão 2026-06-23 — O3NT v2 (unificado e-commerce)

- **Paridade motor:** `projection_rules` (alavanca mídia, CPS mínimo 0,86), aba Breakeven unificada v16 para e-commerce (`breakeven_unified_sheet.py`, `funnel_mode=ecommerce`).
- **Contexto sazonal:** SR col. O → `context.seasonal` + Leitura estratégica (`breakeven_personalization.py`); `read_strategy_review_row.py` mapeia colunas I–O.
- **Entrega:** https://docs.google.com/spreadsheets/d/1hPFnFImi0ajdDUC69YQ9GTvJT2lxDr91xH9c0MntwI8/edit?usp=drivesdk
- Decisões em `_context/decisions.md` (motor compartilhado + sazonalidade).

## Sessão 2026-06-23 — O3NT v1 entregue

- Growth Pack baixado após liberação de acesso.
- Config e-commerce via `build_config_from_growthpack_acompanhamento.py` (GP 3.0 / aba 6.0).
- Planilha gerada e publicada: https://docs.google.com/spreadsheets/d/1AByMatMbQyFLJVORIS5HJCXf4ttOu46CbJm5AphuZVg/edit?usp=drivesdk
- Premissas: Fee R$ 5.000 · Mídia R$ 4.100 · Margem 40% · LT Dez/25–Jun/26

## Sessão 2026-06-23 — O3NT (ordem 6, SR linha 70) — setup

- Projeto confirmado na Strategy Review linha 70: **O3NT PRODUTOS DE HIGIENE E BEM ESTAR LTDA**.
- Modelo Flow: **E-commerce** (`paid_traffic_mql_sql_criteria`).
- Premissas alinhadas: Fee R$ 5.000 · Mídia R$ 4.100 · Margem **40%** (manifest corrigido de 25%).
- **Bloqueio:** Growth Pack `1xqoZWAARIOeTRjUehiQRD5iyZDjEGI-ID1TQJWgh8KQ` inacessível via OAuth (404/401). Mesmo padrão de SIGO/Gôndolas.
- Pasta: `projects/06-o3nt-produtos-de-higiene-e-bem-estar-ltda-o3nt-produtos-de-higiene-e-bem/` — `gate.md` + `status.md` atualizados.
- Próximo passo: compartilhar GP com `rafael.clarindoreis@gmail.com` ou export manual → pipeline e-commerce.

## Memória operacional — Inside Sales

> **Playbook completo:** [`docs/inside-sales-breakeven.md`](../docs/inside-sales-breakeven.md)

- Entrega de referência: Soma **v17** — https://docs.google.com/spreadsheets/d/1PCcoCc9tvSqrBMHldiAwhfNk2G7wqBpnspu7fV1hEuM/edit?usp=drivesdk

## Sessão 2026-06-22 (nomenclatura)

- Padrão de entrega: `[Colli & CO] - [Cliente] - Breakeven Inside Sales|E-commerce - AI Auto` (`breakeven_naming.py`).

## Sessão 2026-06-22 (v17)

- Textos personalizados via `breakeven_personalization.py` (config + Growth Pack).
- Motor financeiro compartilhado `breakeven_projection.py` — cenários usam mesma alavanca de mídia que aba Breakeven.
- Realista alinhado ao cenário mínimo (BEP acumulado Mês 29).

## Sessão 2026-06-22 (v16)

- **Direcionamento Rafael:** linha de títulos na aba Breakeven; funil completo do cenário mínimo no topo (não Impressões→SQLs); remover bloco funil duplicado embaixo.
- Novo módulo `src/integrations/breakeven_unified_sheet.py` — layout unificado linhas 3–37.
- Resumo Executivo e Funil Completo atualizados para refs das novas linhas.

## Sessão 2026-06-22 (v15)

- Premissas expandidas: 6 taxas editáveis do funil operacional + Leads→Vendas calculada (linha 21).
- Funil integrado (Breakeven) e Funil Completo referenciam Premissas em tempo real.

## Entregue nesta sessão (setup inicial QGI)

- Projeto `projects/breakeven-auto/` criado no QGI.
- Vendor `autobreakeven` copiado de https://github.com/jeffersonvieira-hue/autobreakeven (skill + scripts Python).
- Script `src/integrations/build_strategy_review_manifest.py` — ordem col B + dados Flow (GrowthPack Atualizado, fee, mídia prevista, margem).
- Docs `docs/strategy-review-integration.md`, `README.md`, `ops/setup.ps1`.
- MAPA (`CLAUDE.md` raiz) e `_core/registry.json` atualizados.

## Entregue em 2026-06-21

- `build_strategy_review_manifest.py` ficou resiliente a falhas transitórias do Cockpit com retry.
- Manifest gerado: `assets/strategy_review_manifest_2026-06-21.json`.
  - 74 projetos na Strategy Review.
  - 60 com GrowthPack Atualizado no Flow.
- Novo script `src/integrations/prepare_strategy_review_projects.py`.
  - Cria `projects/<ordem>-<slug>/` para cada projeto.
  - Gera `source/manifest-entry.json` e `status.md` por projeto.
  - Gera `projects/index.md`, `projects/index.json` e `assets/strategy_review_readiness_2026-06-21.json`.
  - Classificação atual: 49 `ready`, 11 `needs-review`, 14 `blocked`.
- Novo script `src/integrations/download_growthpacks.py`.
  - Baixa Growth Packs para `projects/<ordem>-<slug>/source/growthpack.xlsx`.
  - Usa Drive API e fallback por export público do Google Sheets.
- Novo script `src/integrations/inspect_downloaded_growthpacks.py`.
  - Roda a inspeção da skill Jefferson e salva em `inspection/inspection.json`.
- Piloto ordens 1–5:
  - Baixados e inspecionados: 1 Manchester, 2 Binário, 3 Promax.
  - Bloqueados por permissão `401`: 4 SIGO ERP, 5 SA Gôndolas.
  - Promax está `needs-review` por margem ausente no Flow.

## Entregue em 2026-06-22

- Teste completo para `SOMA SOLUCOES FINANCEIRAS LTDA` (ordem 17).
- Growth Pack Atualizado baixado para `projects/17-soma-solucoes-financeiras-ltda/source/growthpack.xlsx`.
- Breakeven antigo da Strategy Review coluna M baixado para `projects/17-soma-solucoes-financeiras-ltda/source/old-breakeven.xlsx`.
- Leitor de linha da Strategy Review criado: `src/integrations/read_strategy_review_row.py`.
- Downloader genérico de Google Sheets criado: `src/integrations/download_google_sheet.py`.
- Resumidor de XLSX criado: `src/integrations/summarize_workbook.py`.
- Builder de config por `Tabela Mensal` criado: `src/integrations/build_config_from_growthpack_monthly.py`.
- Uploader para Google Sheets criado: `src/integrations/upload_xlsx_to_google_sheet.py`.
- Config da Soma validado com `validate_config.py` (`OK`).
- Relatório gerado: `projects/17-soma-solucoes-financeiras-ltda/report/[Gerência] - [Análise e Estratégia] - [Soma Soluções].md`.
- XLSX gerado: `projects/17-soma-solucoes-financeiras-ltda/spreadsheet/Soma Soluções - Projeção Breakeven Inside Sales.xlsx`.
- Upload convertido para Google Sheets:
  - https://docs.google.com/spreadsheets/d/1ljfS-zrwk0XEu_r06dEfLnfLND1qgYE4Kjj-1-yYh94/edit?usp=drivesdk
- Correção após revisão visual do Rafael:
  - Problema: fórmulas quebravam no Google Sheets com `#DIV/0!`.
  - Script criado: `src/integrations/sanitize_breakeven_formulas.py`.
  - A v2 protegeu 623 fórmulas com divisão usando `IFERROR(...,0)`.
  - Upload v2: https://docs.google.com/spreadsheets/d/1wtaG0k0JTnj831qGNMNu27jFno7wZPMSIBheqkuXHFM/edit?usp=drivesdk
  - Export-check da v2 confirmou que as fórmulas protegidas sobreviveram à conversão Google Sheets → XLSX.
- Segunda correção após nova captura do Rafael:
  - A aba `Breakeven 7M` ainda aparecia quebrada visualmente no Google Sheets.
  - Script criado: `src/integrations/freeze_breakeven_values.py`.
  - A v3 congelou 1.184 fórmulas em valores calculados para eliminar recálculo quebrado no Google Sheets.
  - Upload v3 estável: https://docs.google.com/spreadsheets/d/1E_LwCveDPbYGf5Y1EAIkhGosmzdiZ65YjWjrM9JyYNQ/edit?usp=drivesdk
  - Export-check da v3: 0 fórmulas e 0 erros após baixar novamente do Google Sheets.
- Direcionamento metodológico do Rafael:
  - O funil deve ser exatamente o funil do Growth Pack do cliente.
  - Em Soma, usar `impressões → cliques → leads → MQLs → SQLs → vendas → faturamento`.
  - Não adaptar inside sales para funil e-commerce quando essas etapas não existem.
  - Não travar projeção em 7 meses; o horizonte deve ir até o breakeven acontecer, antes ou depois, ou declarar que não breakeva no horizonte definido.
- Versão Soma inside sales nativa:
  - Script criado: `src/integrations/generate_inside_sales_breakeven.py`.
  - Recorte histórico válido: Jan/2026 a Jun/2026, apenas meses com funil completo.
  - Resultado histórico acumulado: -R$ 124.428,52, portanto breakeven ainda não atingido no histórico.
  - Planilha local: `projects/17-soma-solucoes-financeiras-ltda/spreadsheet/Soma Soluções - Breakeven Inside Sales Nativo.xlsx`.
  - Relatório local: `projects/17-soma-solucoes-financeiras-ltda/report/[Gerência] - [Análise e Estratégia] - [Soma Soluções - Inside Sales Nativo].md`.
  - Google Sheets: https://docs.google.com/spreadsheets/d/1SKTWCxUE_xs8REMBAqrnH2kmxxnL-c4RKVkZS4Ev4yE/edit?usp=drivesdk
  - Export-check: 0 fórmulas e 0 erros após baixar novamente do Google Sheets.
- Correção de formato solicitada pelo Rafael:
  - Problema: a versão nativa mudou demais a estrutura visual da planilha.
  - Direção correta: seguir o mesmo modelo/estrutura da skill e-commerce; mudar apenas o funil para inside sales.
  - Scripts criados: `src/integrations/build_soma_inside_sales_template_config.py` e `src/integrations/relabel_inside_sales_template.py`.
  - Planilha final: `projects/17-soma-solucoes-financeiras-ltda/spreadsheet/Soma Soluções - Breakeven Template Inside Sales Final.xlsx`.
  - Google Sheets final: https://docs.google.com/spreadsheets/d/1R_Kg0tdgjlY5ejM_dnXg1TOWKR6mW_GlSwPMDtUJzQs/edit?usp=drivesdk
  - Export-check final: mesmas 8 abas do template e 0 erros após baixar novamente do Google Sheets.
- Correção v6 após Rafael reportar `#DIV/0!` persistente:
  - Causa raiz identificada: `Premissas` referenciava `'Dados Fonte'!G12/F12` fixos, mas com 6 meses o total está na linha 10 → ticket médio quebrava → cascata de 262 erros no Google Sheets.
  - `relabel_inside_sales_template.py` renomeava aba sem atualizar refs `'Breakeven 7M'` → `#REF!` no Resumo Executivo.
  - Funil mínimo usava `Leads → MQLs = 100%` fixo; corrigido para taxa real do Growth Pack (~20%).
  - `generate_breakeven.py` corrigido: linha total dinâmica, taxas reais do funil, divisões com `IFERROR`.
  - Planilha v6: https://docs.google.com/spreadsheets/d/1WLyI1ClH6P8vvtlXN25yti97N2_5nSyxh9t81n-VoOk/edit?usp=drivesdk
  - Export-check v6: **0 erros** confirmados após baixar do Google Sheets.
- Ajuste visual momentâneo (2026-06-22): linhas de título principal (`title`) passaram de azul marinho para **vermelho-escuro 2** (`#CC0000`). Subtítulos de seção (`section`) permanecem inalterados.
  - Planilha v7: https://docs.google.com/spreadsheets/d/1GBUP-q5tgycD589KMdmkV7CO2niuc2i-wYsyuLXAWYo/edit?usp=drivesdk
- Ajustes v8 (2026-06-22):
  - Títulos de seção (`section`) também em **vermelho-escuro 2** — ex.: *Funil completo*, *Cenário atual x cenário mínimo*, *Premissas futuras*, etc.
  - Projeção dinâmica até breakeven (máx. 36 meses), sem travar em 7 meses.
  - Soma: breakeven no cenário mínimo/realista no **Mês 25**; pessimista não breakeva em 36 meses.
  - Planilha v8: https://docs.google.com/spreadsheets/d/1SZdamPLHnm7CA9w0NNtBudv2t3DqLJN3oNAdYb6eXZk/edit?usp=drivesdk
  - Export-check v8: **0 erros**.
- Correção v11 (2026-06-22):
  - **Dados Fonte** limpo: bench com 6 colunas reais, sem duplicar SQLs/Vendas nem taxas artificiais a 100%.
  - Premissas: Impressões acumuladas / SQLs acumulados (não Sessões/Pedidos).
  - Planilha v11: https://docs.google.com/spreadsheets/d/1F8kYLiPUxq-yxX7TIJT2-VtSnBmWSEfI_886y859x7c/edit?usp=drivesdk
- Correção v10 (2026-06-22):
  - Removidas etapas artificiais **Vendas → Vendas** / **Etapa neutra** do funil inside sales (restos do template e-commerce).
  - Funil simplificado: impressões → cliques → leads → MQLs → SQLs → **Taxa SQLs → Vendas** → vendas.
  - Planilha v10: https://docs.google.com/spreadsheets/d/1bZEBo6BLBwk6Wfhg1qnGxC6ytJ7W2W1adXwdMbo_Z9c/edit?usp=drivesdk
- QA local salvo em `projects/17-soma-solucoes-financeiras-ltda/qa.json`.

### Observações do teste Soma

- Strategy Review linha 18, coluna M: breakeven antigo `https://docs.google.com/spreadsheets/d/1ptdQCIQdKPuT770fHO1JoII3NfIA1x0EVouuRmlUImM/edit?gid=1192649677`.
- Breakeven antigo usa estrutura inside sales, com `Taxa de Conversão SQL -> Venda`.
- Na aba `Projeção Break Even` antiga: Fee R$ 5.500, mídia R$ 35.000 e margem futura 15%.
- Strategy Review/Flow atual: Fee R$ 7.200, mídia R$ 30.000 e margem 15%.
- Growth Pack `Tabela Mensal`: Fee V4 R$ 17.000 nos meses Jan/2024–Mar/2024 e margem 30%.
- A execução nova usou Flow/Strategy Review para competência e margem, e Growth Pack para acumulado/funil.
- O funil inside sales foi adaptado ao contrato do gerador via `project_model: Inside Sales`; e-commerce permanece no caminho original.

## Contexto da frente Strategy Review

- Planilha: https://docs.google.com/spreadsheets/d/1MrUklD9tulNHsxWmAh3fcUUBlBdY-IHzSUuEPAz32YQ/edit#gid=226918461
- Aba: **Start Strategy Review** — 74 projetos col B.
- Colunas operacionais na planilha: Fee, Mídia, Margem, Link Break-even / GrowthPack (parcialmente preenchidas manualmente).
- Scripts legados em `monitor-invictus/scripts/` (`export_growthpack_links.py`, `update_hs_sheet_columns.py`, `read_flow_growthpack_atualizado.py`).

## Próximo passo

1. **Inside sales:** seguir `docs/inside-sales-breakeven.md` — generalizar `build_soma_inside_sales_template_config.py` para outros GPs inside sales da carteira.
2. **E-commerce:** manter pipeline original da skill (`config.json` sem `project_model: Inside Sales`).
3. Por cliente: gate → config → validate → generate → relabel → upload → export-check → atualizar `qa.json` e `status.md`.
4. Após cada lote, atualizar este `_context/status.md`.
