# Decisions — Breakeven Auto

## 2026-06-22 — Projeção M1 IS: medianas de volume + taxas (não Flow÷CPI)

- **Problema (Green Way):** Jul/26 abria com **~7 vendas** na projeção Realista — acima do melhor mês histórico (5 vendas Mar/26). Causa: funil forward partia de `mídia Flow ÷ CPI mediano` (93.986 imp) × taxas medianas.
- **Regra acordada Rafael:** M1 da projeção = **mediana das quantidades** (imp, cliques, leads, MQL, SQL, vendas) **e mediana das taxas** na janela 3M; **M2+** evolui conforme cenário (taxas compostas em Premissas). Impressões projetadas **ancoram na mediana** (célula `$G$16`), não em Flow÷CPI.
- **Flow÷CPI** permanece em `impression_traceability` como **referência** (“se toda mídia Flow comprasse ao CPI recente, quantas imp?”) — **não** alimenta colunas G+ dos cenários.
- **Código:** `baseline_funnel_volumes` no builder; `revenue_from_funnel(..., baseline_volumes=)`; `build_inside_sales_funnel_forward(..., baseline_volumes=)`; `inside_sales_forward_volume_formulas(..., baseline_impressions_cell=$G$16)`.

## 2026-06-22 — Coluna D e projeção G+: vendas meta ≠ vendas realizadas (GAP proibido)

- **Problema (Green Way Insulation):** coluna D (~7 vendas) e Jul/26 (~7 vendas) lidos como **realizado histórico** — cliente nunca fez 7 vendas/mês (máx. 5 em Mar/26; Jul/25 = 0).
- **Causa:** rótulo genérico "Breakeven da competência" + linha "Vendas" igual em todas as colunas; número D = `breakeven competência ÷ ticket` (meta); G+ = funil forward projetado.
- **Regra gravada:**
  1. **Col. B (Atual acumulado):** única coluna de **vendas realizadas** somadas no contrato (GP).
  2. **Col. C:** funil **real** do último mês fechado no GP (vendas = fato).
  3. **Col. D:** renomeada **"Meta breakeven (vendas necessárias)"** — quantas vendas **precisariam** fechar o mês (`(fee+mídia Flow)÷margem ÷ ticket`). **Nunca** apresentar como histórico.
  4. **Col. G+ (Jul/26…):** **projeção forward** — não confundir com mês calendário passado (Jul/25 ≠ Jul/26).
  5. **Nota de rodapé** nos cenários IS: explicitar D e G+ ≠ realizado.
  6. **Checklist pré-publicação:** se col. D > máximo histórico mensal de vendas, validar com Rafael **antes** de entregar — pode ser meta legítima (ticket baixo) ou erro de ticket/funil.
- **Código:** `generate_breakeven.py` (header col. D + `scenario_note`); `build_growthpack_inside_sales_config.py` (`context.diagnosis`).
- **Docs:** `RUNBOOK-executor-inside-sales.md` §5.1 e §7; `inside-sales-breakeven.md`.

## 2026-06-22 — Impressões/sessões: mediana de CPI ≠ mediana de volume (GAP proibido)

- **Problema (Centro Auditivo Macaé):** planilha mostrava ~133k impressões na projeção M1 sem explicar que **não** é mediana do histórico (~82k mediana mensal · ~164k acumulado funil). Causava leitura errada (“fizeram mediana de impressões?”).
- **Regra gravada:**
  1. **CPI/CPS (projeção):** mediana dos últimos **3 meses com mídia + impressões/sessões** em `investment_months` — **inclui pré-funil** (Abr com mídia/impressões, sem vendas). Helper: `select_cpi_baseline_months()`.
  2. **Taxas do funil:** mediana só em meses com funil completo (`funnel_months`). Janela separada do CPI.
  3. **Volume M1 projetado (cenários IS):** **medianas de quantidade** por etapa na janela baseline 3M + **taxas medianas** — crescimento só a partir de M2 (taxas compostas). **Não** iniciar projeção com `Flow ÷ CPI` (isso fica só como referência em `impression_traceability`).
  4. **Histórico funil (Resumo col. Atual):** acumulado/mediana mensal só de `benchmark_months`. Em branco = zero.
  5. **Investimento acumulado:** todos os meses com mídia > 0 (inclui pré-funil).
  6. **Histórico curto (≤3M):** usar todos os meses elegíveis, não truncar a 1. `select_projection_baseline_months()`.
  7. **Transparência:** `impression_traceability` + linha Impressões no Resumo + Leitura estratégica (CPI 3M vs funil 2M quando diferirem).
- **Código:** `build_impression_traceability()`, builders IS/EC, `generate_breakeven.py` Resumo, `breakeven_personalization.py`.

## 2026-06-22 — Perfil GP `centroauditivo` (Fee L5 + funil L6–L15)

- **Cliente:** Centro Auditivo Macaé · SR linha 12.
- **GP ganhou linha Fee Mensal L5** — investimento desceu para **L6**; funil L8–L15 (Imp, Clique, Leads, MQL, SQL, Vendas, Receita L15, Ticket L7).

## 2026-06-22 — Perfil GP `malbork` (MQL/SQL manual + impressões L29)

- **Cliente:** Malbork · SR linha 6.
- **Aba:** `6.0 Acompanhamento Mensal`.
- **Linhas:** mídia 5 · impressões **29** · cliques 8 · leads 9 · MQL/SQL manual 10–11 · vendas 12 · receita 13.
- **Normalização:** quando MQL/SQL manual = 0 e Leads > 0 → MQL = SQL = Leads (`normalize_manual_funnel`).

## 2026-06-22 — Perfil GP `sigo` + resolução automática da aba Acompanhamento Mensal

- **Cliente:** SIGO ERP · SR linha 4.
- **Regra:** sempre ler a aba cujo nome contém **Acompanhamento Mensal** (`find_acompanhamento_mensal_sheet` — prefere `6.0`, depois `2.2`).
- **Aba:** `6.0 Acompanhamento Mensal` (ano linha 1 + mês texto linha 4).
- **Linhas:** mídia **7** (Investimento, não linha 5 com fee), impressões 8, cliques 9, leads 10, MQL 11, SQL 12, Novos Clientes 15, receita 16 (Mensalidade + Implementação). RM/RR (13–14) informativas — fora do funil breakeven.

## 2026-06-22 — Perfil GP `visoflex` (GP 4.0)

- **Cliente:** Visoflex · SR linha 8.
- **Aba:** `2.2 Acompanhamento Mensal` (não `6.0`).
- **Linhas:** investimento 7 · impressões 11 · cliques 12 · leads 14 · MQL 15 · SQL 16 · vendas 17 · receita 18 · datas linha 2 (`datetime_row`).

## 2026-06-24 — Conta OAuth = `rafael.clarindo@v4company.com`

- Growth Packs e planilhas da carteira devem ser compartilhados com **`rafael.clarindo@v4company.com`** (conta do token OAuth em `assessor-pessoal/mcp/credentials/google_sheets_token.json`).
- **Não** usar `rafael.clarindoreis@gmail.com` — estava incorreto na documentação inicial do pipeline online.
- Constante no código: `OAUTH_ACCOUNT_EMAIL` em `growthpack_sheets_reader.py`.

## 2026-06-24 — CPS de projeção = mediana 3M + fix cor do status

- **Constatação Rafael:** Realista "nunca breakeva" (perde ~R$70/mês) e havia "EM RECUPERAÇÃO" em **verde**.
- **Bug 1 (CPS inconsistente):** impressões da projeção usavam o CPS **acumulado** (18 meses, R$0,054, `$B$34`) enquanto as taxas usam os **últimos 3 meses**. CPS acumulado (inflado por meses antigos) → 637k impressões → ~25 vendas → não breakeva.
- **Decisão Rafael:** CPS de projeção = **mediana dos últimos 3 meses** (R$0,029), consistente com as taxas. Builder: `projection_cps = median(baseline_cps_samples)`. Gerador: impressões referenciam `$G$34` (input editável = CPS recente), não `$B$34`. Breakeven 7M já usava `inside_sales_month_cps` (segue o gp_cps_projection).
- **Resultado:** 1,196M impressões → satura ~46 vendas → **breakeva**: Otimista Mar/28, Realista **Abr/28**, Pessimista Jun/28.
- **Bug 2 (cor do status):** a cor do status (linha 13) era **estática (do cache da geração)** enquanto o texto é fórmula → "EM RECUPERAÇÃO" podia ficar verde. **Correção:** `conditional_format` na linha 13 (projeção + Total) seguindo o resultado acumulado (linha 11) ao vivo. Em recuperação = vermelho; breakeven = verde.

## 2026-06-24 — Baseline M1 = mediana (não média) + fix bloco consolidado Premissas

- **Constatação Rafael:** o M1 da projeção começava acima do nível recente real (ex.: Imp→Clique 3,79% quando Mai/26 foi 2,94%) → "crescimento absurdo desde o início". Causa: **baseline = MÉDIA** dos 3 meses, inflada por outlier (Mar/26 = 5,79%).
- **Decisão:** baseline M1 = **MEDIANA** dos últimos 3 meses (mesma lógica anti-outlier dos tetos). Builder: `median_stage_rate` no lugar de `mean_funnel_rate`. Ex. MSYS: Imp→Clique 3,79%→**2,94%**; tetos = mediana×1,1.
- **Efeito:** M1 parte do nível recente; cenários mais sóbrios (MSYS satura ~44 vendas, breakeven Realista Jul/28).
- **Bug corrigido (mesmo dia):** bloco consolidado das Premissas (B7–B17, "feito até o momento") tinha **cross-refs deslocadas 1 linha** (layout antigo): Custo `=B6+B7`→`=B7+B8` (vinha só o fee → déficit subdimensionado → **falso breakeven no mês 3** na Breakeven 7M); Ticket `B9/B12`→`B10/B13` (vinha Custo/SQLs = R$159 em vez de R$223,88); MC `B9*B14`→`B10*B15`; Resultado `B15-B8`→`B16-B9`. Afetava Breakeven 7M (referencia Premissas B9/B14).

## 2026-06-24 — Rótulo da etapa extra do funil configurável (`extra_stage_label`)

- **Constatação Rafael:** o funil de cada cliente pode ter etapa(s) a mais/menos, e a etapa extra **não é necessariamente "lead quali"** — pode ter qualquer nome (agendamento, reunião, proposta, visita…).
- **Antes:** o slot extra (`funnel_has_lead_quali: true`) tinha o rótulo **fixo "Lead quali"** em ~12 lugares do gerador + `breakeven_unified_sheet.py`.
- **Agora:** config `"extra_stage_label": "<nome>"` (default `"Lead quali"`). Todos os rótulos do funil em todas as abas usam esse nome. Threading via `extra_stage_label` (gerador) e parâmetro `extra_label` nas funções de label + `write_unified_breakeven_worksheet`.
- **Compatibilidade:** default preserva Soma ("Lead quali"); MSYS/cdsi/primeset (6 etapas) não tocam esses ramos — saída idêntica.
- **Teste:** config Soma com `extra_stage_label="Agendamento"` → 21 rótulos trocados, 0 sobra de "Lead quali" em rótulo gerado (só texto livre da config). MSYS regenerado + validado OK.
- **Regra:** o executor lê o nome da etapa **no GP do cliente** e seta `extra_stage_label`. Estrutura muito diferente (outra contagem/ordem) → PARA e pede ajuste no gerador.

## 2026-06-24 — Strategy Review mudou de colunas (re-mapeamento)

- **Constatação Rafael:** as colunas da aba **Start Strategy Review** deslocaram (inserida "Retrospectiva (By AI)").
- **Layout atual confirmado (2026-06-24):**
  | Col | Conteúdo |
  |-----|----------|
  | B | Projeto |
  | H | LT |
  | I | Fee |
  | J | Mídia |
  | K | Margem de contribuição |
  | L | **MRR** (recorrência TM — só se preenchida) |
  | M | Link do Break-even (Antigo) |
  | N | **Link do GrowthPack** |
  | O | Retrospectiva (By AI) *(coluna nova)* |
  | P | **Contexto do projeto (Datas sazonais)** |
- **Não mudaram:** B, H, I, J, K, L (recorrência) — `build_strategy_review_manifest.py` lê só B/H/L, segue OK.
- **Mudaram:** old-breakeven L→**M**; GrowthPack M→**N**; **sazonal O→P**; nova Retrospectiva em **O**.
- **Corrigido:** `read_strategy_review_row.py` re-mapeado (M/N/O/P). **Ao ler a SR, sempre conferir o cabeçalho** — o layout pode mudar de novo.

## 2026-06-24 — Saturação do funil por teto por etapa (v26)

- **Problema:** a projeção compunha cada taxa do funil X%/mês por 54 meses com cap único de 95% → estouro irreal (Realista 21 mil vendas/mês, Otimista 164 mil/mês, CTR 50% em Dez/30).
- **Decisão Rafael:** Rafael delegou a escolha da curva ("o que faz mais sentido para uma projeção"); escopo **só MSYS por enquanto**.
- **Solução:** funil **satura** num teto realista **por etapa**, em vez de compor indefinidamente. Fórmula M2+: `MIN(teto_etapa; taxa_anterior×(1+avanço))`. O teto substitui o 95% como termo do `MIN`.
- **Base do teto (derivada dos dados, não chute):** `max(mediana dos últimos 3 meses, baseline M1) × 1,1`.
  - **Mediana** e não melhor mês: o melhor mês pode ser outlier (Black Friday, oferta pontual) e inflar o teto — mediana é robusta.
  - **Últimos 3 meses** e não todo histórico: a **projeção** (baseline + tetos) parte do desempenho recente. O **restante da análise** (acumulado, bench, Dados Fonte, "Feito até o momento") continua com **TODO o período do contrato** do GrowthPack — não interferir nisso.
  - **`max(…, baseline)`**: o teto nunca cai abaixo do ponto de partida da projeção; **+10%** de folga para esticar.
  - Implementado em `stage_ceilings_from_history` (calcula por cliente). Tetos ficam **editáveis** em Premissas C28:C32.
- **Tetos MSYS resultantes:** Imp→Clique 4,17% · Clique→Lead 1,48% · Lead→MQL 30,18% · MQL→SQL 55,0% · SQL→Venda 51,61%.
- **Efeito:** cenários partem de 35 vendas/mês e saturam em ~60/mês (~1,7×); diferença entre Pessimista/Realista/Otimista fica na **velocidade** e no **mês de breakeven**, não em volume fantasioso. Convergência no teto é intencional (teto realista é o mesmo; otimismo = chegar mais rápido). Para diferenciar o teto por cenário no futuro, criar tetos por coluna.
- **Evolução da decisão (mesma sessão):** chute inicial (7/3/40/65/60) → melhor mês ×1,1 → **mediana últimos 3M ×1,1** (versão final, robusta a outliers e ancorada no recente).
- **Implementação:** `STAGE_RATE_CEILINGS` + `stage_ceiling()` + `compound_rate_series(ceiling=)` no builder; `prem_ceiling_cell()`/`rate_cap_term()`/`use_stage_ceilings` no gerador; render Premissas C27/C28:C32. Ativa quando config tem `stage_rate_ceilings`.
- **Escopo do builder:** saturação é o novo **default** de todos os inside sales construídos pelo builder genérico; só MSYS foi regenerado/publicado agora. Primeset/CDSI herdam na próxima regeração (tinham o mesmo bug de explosão) e devem ser re-revisados.

## 2026-06-24 — Breakeven 7M col. C alinhada ao funil Realista (v26)

- **Pendência herdada (v25):** col. C ("Cenário mínimo") usava motor legacy — forçava receita = requisito de breakeven e derivava vendas de trás pra frente (1,56 mi vendas/mês, ticket R$3,00, cache desalinhado das fórmulas).
- **Causa raiz adicional:** com recorrência, a receita (linha 18) é LTV (×12) mas a venda dividia pelo ticket **mensal** (que ainda crescia 1%/mês) → vendas infladas ~7×.
- **Decisão:** col. C e as colunas de projeção da Breakeven 7M devem espelhar o funil **Realista** (mesma contagem de vendas).
- **Correção (gated em `is_inside_sales and tm_recurrence_months > 1` → só MSYS/recorrência):**
  - Vendas (linha 11) = `receita ÷ (ticket × recorrência)`; ticket de projeção fixo (`=$B$15`, não cresce 1%/mês).
  - Col. C agregada = **soma real do funil** (receita, vendas, MC, resultado), cache alinhado às fórmulas `=SUM(...)`. Linha 32 ("Receita futura necessária") permanece como requisito de breakeven.
- **Resultado:** Breakeven 7M projeção = 370,6 vendas/mês (= Realista); col. C ticket R$2.686 (LTV), resultado coerente.
- **e-commerce e clientes sem recorrência:** intocados (branch legacy preservado).

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
- **LT no acumulado:** usar **todos os meses válidos do GP** (funil + faturamento preenchidos) para Dados Fonte e “Feito até o momento”. O LT da Strategy Review (col. H) é referência Flow, **não** recorte automático do histórico — só limitar com `--lt-months` se o Rafael pedir.
- **Histórico completo obrigatório:** o breakeven acumulado depende de **todo** o histórico disponível no GP (ex.: Primeset desde Mai/25). Validar sempre no GP antes de gerar; meses com receita mas funil incompleto ficam de fora — meses com funil completo entram todos, inclusive anteriores a Jan/26.
- **Funil 100% do GP — nunca copiar de outro cliente:** `funnel_has_lead_quali: true` **somente** quando o GP tiver etapa operacional de lead quali (ex.: Soma linha 19). **Proibido** mapear “Leads no Ploomes” ou campos informativos como lead quali se o GP não define essa etapa no funil (Primeset: 6 etapas, Leads→MQL direto).

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
- **Horizonte:** projeção até **dez/2030** (`PROJECTION_END_YEAR`); mínimo = meses até 2030 ou até breakeven, o que for maior (máx. 72 meses).
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
- **Receita dos cenários:** crescimento composto a partir do último mês fechado do GP — **nunca** `max(receita, breakeven_competência)` no Mês 1 (gera salto irreal de vendas).
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
- **Regra:** 1ª coluna = **mês seguinte** ao da geração (ex.: 22/jun/2026 → Jul/26).
- **Implementação:** `projection_month_headers()` em `breakeven_projection.py`; CLI `--reference-date`.

## 2026-06-22 — Nomenclatura de entrega Colli & CO

- **Padrão:** `[Colli & CO] - [Nome do Cliente] - Breakeven [Inside Sales | E-commerce] - AI Auto`
- **Google Sheets e `.xlsx` local** usam o mesmo título (sem sufixo de versão no nome canônico).
- **Implementação:** `src/integrations/breakeven_naming.py`; `generate_breakeven.py` (default `--output`) e `upload_xlsx_to_google_sheet.py` (`--config` deriva `--name`).
- **Soma:** entregas v1–v18 mantêm nomes antigos; próximos clientes seguem o padrão.

## 2026-06-22 — Handoff Inside Sales vs E-commerce

- Documento para próxima IA: **`docs/handoff-inside-sales-vs-ecommerce.md`**
- Resume: motor compartilhado (`breakeven_projection.py`, `generate_breakeven.py`); funil e builders **separados**; MRR/LT SR; entregas da sessão; pendências e-commerce.

## 2026-06-22 — LT (col. H) ≠ MRR (col. L)

- **LT (col. H):** meses de contrato ativo — gravar `lt_months`; **não** multiplica ticket.
- **MRR (col. L):** recorrência do ticket — **só** quando a célula estiver preenchida (ex.: MSYS = "12 meses").
- **Implementação:** `strategy_review_fields.resolve_mrr_from_manifest()` — ignora `tm_recurrence_months` sem texto MRR; batch usa `apply_sr_fields_to_manifest()` lendo SR online.

## 2026-06-23 — MRR / LTV (Strategy Review col. L) — capacidade global

- **Fonte:** aba **Start Strategy Review**, coluna **L** — **MRR**.
- **Escopo:** feature **opt-in**. Só entra quando col. L preenchida no manifest (ex.: MSYS = **"12 meses"**). Col. L vazia → faturamento = vendas × ticket mensal GP (sem multiplicador).
- **Regra (com recorrência):**
  - **LTV** = **faturamento mensal GP × meses_recorrência** (ex.: Mai/26 → R$ 8.768,97 × 12 = R$ 105.227,64). Não usar TM médio acumulado SR/GP como substituto do faturamento do mês.
  - Ticket GP mensal = **faturamento GP ÷ vendas** do mês (col. C usa o ticket real de Mai/26; projeções usam **mediana** mensal histórica em B7).
  - Faturamento LTV nas colunas de funil = **vendas × ticket GP mensal (linha 7) × recorrência** — fórmula `=Col32*Col7*12`.
  - Breakeven da competência (col. D): meta **mensal** = `(fee + mídia Flow) ÷ margem`; vendas = meta ÷ ticket GP mensal (**sem** ×12).
  - **Taxas projetadas:** controle central em **Premissas A18:D32** (baseline B28:B32 + % mensal por cenário); abas de cenário e Breakeven 7M recalculam via fórmula. Ver seção **2026-06-22 — Tabela de controle do funil na aba Premissas**.
- **Onde NÃO aplica recorrência:** col. B linha 6 (faturamento **caixa GP** acumulado real). Funil col. B linha 37 pode mostrar LTV modelado + linha 38 = gap vs GP (quando recorrência ativa).
- **Implementação:** `resolve_mrr_from_manifest()` no builder; ramos `if recurrence_months > 1` em `generate_breakeven.py`. E-commerce **intocável** salvo config explícito futuro.

## 2026-06-22 — Tabela de controle do funil na aba Premissas (v25)

- **Decisão Rafael:** centralizar na aba **Premissas** a edição das taxas do funil (baseline M1 + evolução mensal por cenário). Alterar uma célula amarela deve recalcular Pessimista, Realista, Otimista, Mídia V4, curva mensal Premissas e Breakeven 7M **sem regenerar o xlsx**.
- **Layout Premissas A18:D32:**
  - **A19:D24** — evolução mensal % composto por etapa (5 linhas × 3 cenários).
  - **A27:B32** — taxas baseline M1 (ponto de partida da projeção).
- **Etapas mapeadas** (`PREM_FUNNEL_CONTROL_STAGES`): Imp→Clique (linha cenário 17), Clique→Lead (19), Lead→MQL (21), MQL→SQL (23), SQL→Venda (25).
- **Fórmulas:**
  - M1: `='Premissas'!$B$28` … `$B$32`.
  - M2+: `=MIN(max_rate, taxa_anterior*(1+Premissas!$X$Y))` — X = coluna do cenário (B/C/D); Y = linha do avanço (20–24).
  - Cap: `max_conversion_rate` (95%).
- **Mídia V4:** usa coluna **C** (Realista) para avanço; rampa de mídia permanece editável na linha 4.
- **Ativação:** config com `scenario_stage_monthly_advance` + `baseline_funnel_rates` (builder `build_growthpack_inside_sales_config.py`). Flag interna `use_prem_funnel_controls` no gerador.
- **Defaults MSYS v25:** ver `_context/status.md` sessão v25.
- **Validação:** `validate_breakeven_xlsx.py` — fórmula G17 aponta Premissas; M2 = baseline × (1+advance).
- **Pendência:** Breakeven 7M col. C (cenário mínimo 54M) ainda usa motor legacy de LTV — não herdou totalmente o funil Realista.

### Particularidades MSYS (ordem 43) — **não replicar como padrão**

Estas escolhas são do **projeto Mold Systems**, não defaults do Breakeven Auto:

| Item | MSYS | Demais clientes (padrão) |
|------|------|---------------------------|
| Perfil GP | `msys` — aba 6.0 consolidada | Perfil do GP de cada cliente (`cdsi`, etc.) |
| Col. C cenários | Funil **Mai/26** (mês anterior à ref. Jun/26) | Último mês GP ou regra acordada por cliente |
| Projeção cenário (7 col.) | **Média 3M** taxas + CPS; **mídia Flow** R$ 34.500/mês; col. C = Mai/26 real | Builder `growthpack_inside_sales` |
| Investimento acumulado | 18 meses (incl. Jan–Mai/25 pré-funil) | Conforme GP + SR de cada ordem |
| Recorrência 12M | Sim (SR col. L) | Só se manifest tiver recorrência |

**Ao gerar outro cliente:** usar recorrência **se** SR col. L preenchida; projeção parte da **média dos últimos 3 meses** (taxas + CPS); col. **C** = baseline mediana 3M quando `baseline_funnel_volumes` no config (senão, mês anterior GP).

---

## 2026-06-22 — Col. C cenários IS = baseline mediana 3M (não mês anterior GP)

- **Problema:** col. C exibia o funil **real** do último mês GP (ex. Abr/26: 52 leads, 3 vendas), enquanto M1 (Jul/26) e col. D usavam **medianas 3M** (45 leads, 3 vendas) — Rafael: *“a coluna C é o funil com a mediana, certo?”*
- **Decisão:** quando `baseline_funnel_volumes` está no config, col. **C** = **ponto de partida mediana 3M** (volumes fixos + taxas Premissas B28:B32); status **PONTO DE PARTIDA**; financeiro C = receita das vendas baseline × ticket (não meta breakeven).
- **Col. D** referencia funil C (`=$C$16`…); **Jul/26 (G)** M1 referencia C (`=$C$16`…); projeção M2+ cresce taxas a partir de C.
- **Fallback:** sem `baseline_funnel_volumes`, col. C permanece funil real do mês anterior GP.

- **Entrega MSYS v13:** https://docs.google.com/spreadsheets/d/1Y0w6ABwf3ixcPSuhpwGaqAdSgkKRznZhZ9Xg0eYAvzc/edit?usp=drivesdk
- **Validação:** `projects/43-msys-vistorias-ltda/scripts/validate_breakeven_xlsx.py`

## 2026-06-23 — Recorrência TM (SR col. L) — texto anterior (substituído)

- ~~Coluna C funil = Jun/26; taxas só mediana~~ — ver seção acima e particularidades MSYS.
