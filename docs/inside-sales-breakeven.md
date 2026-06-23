# Breakeven Inside Sales — Playbook QGI

> **Escopo:** frente **inside sales** apenas.  
> **Não alterar** o fluxo e-commerce da skill Jefferson quando `project_model` não for inside sales.

Documento de referência consolidado após o piloto **Soma Soluções** (ordem 17, jun/2026). Use este arquivo antes de gerar o próximo breakeven inside sales.

---

## 1. Princípio central

| Modelo | Funil | Gerador |
|--------|-------|---------|
| **E-commerce** | Sessões → View item → Add cart → View cart → Checkout → Shipping → Payment → Purchase | Caminho original da skill (`generate_breakeven.py` sem `project_model: Inside Sales`) |
| **Inside sales** | Impressões → Cliques → Leads → MQLs → SQLs → Vendas | Mesmo template visual da skill, **conteúdo** adaptado via `project_model: "Inside Sales"` |

**Regra de ouro:** nunca inventar etapas e-commerce (shipping, payment, pedido) para inside sales. Nunca duplicar volumes (SQLs/SQLs, Vendas/Vendas) para “preencher” colunas do template.

---

## 2. Funil inside sales — referência Soma

### Etapas (Growth Pack → planilha)

**Soma (com Lead quali — v14+):**

| Etapa GP | Linha GP | Campo interno | Label na planilha |
|----------|----------|---------------|-------------------|
| Impressões | 13 | `sessions` | Impressões |
| Cliques | 15 | `view_item` | Cliques |
| Leads | 18 | `add_to_cart` | Leads |
| **Lead quali** | **19** | `view_cart` | **Lead quali** |
| MQLs | 20 | `begin_checkout` | MQLs |
| SQLs | 21 | `add_shipping_info` | SQLs |
| Vendas | 25 | `sales` / `purchase` | Vendas |

Ativar no config: `"funnel_has_lead_quali": true` (Soma). Sem essa flag, o gerador usa funil de 6 etapas (Leads → MQL direto).

**Funil genérico (sem Lead quali no GP):**

| Etapa GP | Campo interno | Label |
|----------|---------------|-------|
| Impressões | `sessions` | Impressões |
| Cliques | `view_item` | Cliques |
| Leads | `add_to_cart` | Leads |
| MQLs | `view_cart` | MQLs |
| SQLs | `begin_checkout` | SQLs |
| Vendas | `sales` | Vendas |

### Taxas exibidas (Soma / Lead quali)

1. Impressões → Cliques  
2. Cliques → Leads  
3. **Leads → Lead quali**  
4. **Lead quali → MQLs**  
5. MQLs → SQLs  
6. **SQLs → Vendas**  
7. **Leads → Vendas** (conversão final)

### Regras estratégicas de projeção (v14+)

| Regra | Comportamento |
|-------|----------------|
| **Alavanca mídia extra** | Só considerada quando `resultado_líquido_mês ≥ 0` no mês anterior (`projection_rules.media_lever_after_monthly_breakeven`) |
| **Breakeven mensal vs acumulado** | O breakeven **mensal** pode ocorrer antes (ex.: Mês 14); o **acumulado** (recuperar déficit histórico) atrasa porque a alavanca de mídia aumenta custos após meses positivos |
| **Motor financeiro único (v17+)** | Aba Breakeven, Pessimista/Realista/Otimista e Resumo usam `breakeven_projection.py` — mesma lógica de MC, alavanca e acumulado |
| **Realista = cenário mínimo** | `minimum_scenario.revenue` deve ser a mesma série do Realista no config (Growth Pack) |
| **Textos personalizados (v17+)** | `breakeven_personalization.py` lê `monthly_media`, `monthly_fee`, `margin`, `context.diagnosis`, `context.main_risk` do config — **nunca** hardcode Dalpack |
| **Cap de conversão** | Taxas limitadas a **95%** — raramente chegamos a 100% mesmo no otimista |
| **Piso de CPS/CPM** | Custo por impressão não desce abaixo de **R$ 0,01** (ou 85% do CPS atual, o que for maior) |
| **Balanceamento** | Priorizar melhora de funil (lead quali → MQL → SQL → venda) antes de pedir verba extra enquanto o projeto não breakeva |

Config opcional:

```json
"projection_rules": {
  "max_conversion_rate": 0.95,
  "min_cost_per_impression": 0.01,
  "media_lever_after_monthly_breakeven": true
}
```

### Bench interno — Leads → Vendas (armadilha corrigida v12)

**Não está certo** usar Impressões → Vendas (~0,01%) como bench da linha **Leads → Vendas**.

| Métrica | Fórmula correta | Erro comum |
|---------|-----------------|------------|
| **Leads → Vendas** (inside sales) | mediana mensal de `vendas ÷ leads` | `bench_session_purchase` = mediana de `vendas ÷ impressões` (~0,01%) |
| **Impressões → Vendas** (e-commerce) | mediana de `purchase ÷ sessões` | Só faz sentido no funil e-commerce, label **Sessão → Purchase** |

**Onde corrigir no código** (`generate_breakeven.py`, só `is_inside_sales`):

- `bench_lead_to_sale` = mediana de `purchase / add_cart` por mês do bench  
- Usar em: Funil Completo (linha resumo), Dados Fonte (funil atual + mediana da coluna Leads → Vendas)  
- **Nunca** reutilizar `bench_session_purchase` para inside sales quando o label diz Leads → Vendas

**Validação rápida (Soma):** bench Leads → Vendas ≈ **2,8%** (mediana 6M), não 0,01%.

### Premissas vs bench — não confundir (v13/v15)

| Onde | Valor | O que é |
|------|-------|---------|
| **Funil atual → Bench interno** (Leads → Vendas) | ~**2,8%** | Mediana histórica de vendas/leads nos 6 meses do GP — **referência**, não premissa de projeção |
| **Funil atual → Taxa atual** | ~**3,42%** | Mês fechado (Jun/2026): 40 vendas ÷ 1.170 leads |
| **Premissas → Leads → Vendas** (linha 21, verde) | **3,42% no Mês 1** | **Calculada** = F17×F18×F19×F20 (produto das taxas operacionais) |

**Premissas editáveis (Soma / lead quali, v15):**

| Linha | Taxa | Mês 1 (Jun/2026) |
|-------|------|------------------|
| 15 | Impressões → Cliques | ~1,88% |
| 16 | Cliques → Leads | ~14,8% |
| 17 | Leads → Lead quali | ~94,9% |
| 18 | Lead quali → MQLs | ~21,6% |
| 19 | MQLs → SQLs | ~89,2% |
| 20 | SQLs → Vendas | ~18,7% |
| 21 | Leads → Vendas | fórmula (≈3,42%) |

**Erro corrigido (v12/v13):** a projeção usava o produto das medianas do bench (~2,80%) fixo em todos os meses — ignorava que o cliente já converte **3,42%** hoje.

**Regra:** Mês 1 de cada taxa operacional = **taxa do mês atual fechado** (ex.: Jun/2026); rampa gradual editável nas células amarelas. Linha 21 recalcula sozinha.

**Erro corrigido (v18):** cenários Pessimista/Realista/Otimista iniciavam com **mediana do bench × 0,98** (~1,84% imp→clique) em vez da taxa **atual** (~2,14%). Projeção parte do que o cliente já faz hoje; bench serve só como referência e meta de longo prazo.

### O que foi removido (e não deve voltar)

- Etapas artificiais: `Vendas → Vendas`, `SQLs → SQLs`, `Etapa neutra — …`
- Colunas duplicadas em **Dados Fonte**: Add shipping, Add payment, Purchase com os mesmos volumes de SQLs/Vendas
- Taxas e-commerce no bench: `Checkout → Shipping`, `Payment → Purchase` (sempre 100% no inside sales mapeado)

---

## 3. Estrutura visual vs conteúdo

**Decisão Rafael (jun/2026):** manter as **8 abas** e layout da skill Jefferson; mudar só labels, funil e fórmulas quando inside sales.

Abas: `Resumo Executivo`, `Breakeven` (ex-7M), `Pessimista`, `Realista`, `Otimista`, `Funil Completo`, `Premissas`, `Dados Fonte`.

### 3.1 Aba Breakeven unificada (v16+) — direcionamento Rafael

**Problema v15:** a aba Breakeven misturava duas camadas:

1. **Parte de cima** — métricas financeiras simplificadas (`Taxa Impressões → SQLs`, `Taxa SQLs → Vendas` fixa em 100%), sem o funil operacional real.
2. **Parte de baixo** — bloco separado *Funil completo do cenário mínimo* (linhas 36–62), duplicando o que deveria estar no topo.

**Decisão (22/06/2026):**

| Item | Comportamento |
|------|----------------|
| **Linha de títulos** | Inserir **linha 2** entre o título (linha 1) e os dados: `Indicador \| Feito até o momento \| Cenário mínimo NM \| (vazio) \| Mês 1…` |
| **Funil no topo** | Usar o **funil completo do projeto** (6 taxas das Premissas + volumes), alinhado ao cenário mínimo e às vendas — **não** usar atalho Impressões→SQLs |
| **Concatenação** | Remover o bloco inferior duplicado; custos + funil + financeiro num único fluxo (linhas 3–37) |
| **Taxas** | Impressões→Cliques, Cliques→Leads, Leads→Lead quali, Lead quali→MQLs, MQLs→SQLs, SQLs→Vendas + Leads→Vendas calculada |
| **Volumes** | Calculados de trás para frente a partir de vendas/faturamento alvo; taxas amarelas vêm das Premissas |

**Implementação:** quando `(project_model: Inside Sales` **e** `funnel_has_lead_quali: true)` **ou** `project_model` e-commerce, o gerador chama `src/integrations/breakeven_unified_sheet.py` (`write_unified_breakeven_worksheet`, `funnel_mode` inside sales ou e-commerce). Inside sales 6 etapas mantém layout legacy.

**Mapa de linhas (Soma / lead quali):**

| Linha | Conteúdo |
|-------|----------|
| 1 | Título |
| 2 | Headers de coluna |
| 3–5 | Custos (total, fee, mídia) |
| 6–19 | Funil completo (volumes + taxas Premissas + Leads→Vendas) |
| 20–22 | CPS, Custo/SQL, Custo/venda |
| 23–37 | Financeiro (ticket, margem, receita, MC, resultado, ROI, status) |

**Refs cruzadas atualizadas (v16):** Resumo Executivo → `B33` (resultado acumulado), `C36` (receita futura); Funil Completo → linhas 25/23/18/5/20/22 da aba Breakeven.

Linhas vazias no funil integrado legacy (Breakeven linhas 49–52; cenários 28–31) eram **intencionais** quando `funnel_has_lead_quali: true` — restos do grid e-commerce. **Com v16 unificado, esse bloco inferior deixa de existir** para Soma/lead quali.

---

## 4. Ativação no código (e-commerce intacto)

Todas as adaptações inside sales passam por:

```python
# vendor/.../generate_breakeven.py
is_inside_sales = is_inside_sales_model(config_data.get("project_model", ""))
# True apenas se project_model contém "inside sales" (case insensitive)
```

**Config JSON obrigatório:**

```json
"project_model": "Inside Sales"
```

Sem esse campo → comportamento **100% e-commerce** original.

### Arquivos da frente inside sales

| Arquivo | Função |
|---------|--------|
| `vendor/autobreakeven/.../generate_breakeven.py` | Ramificações `if is_inside_sales:` (funil, Dados Fonte, Premissas, cenários) |
| `src/integrations/build_soma_inside_sales_template_config.py` | Monta config a partir do GP (adaptar/generalizar por cliente) |
| `src/integrations/relabel_inside_sales_template.py` | Títulos e labels residuais em PT; **não** criar etapas neutras |
| `src/integrations/breakeven_unified_sheet.py` | Aba Breakeven unificada (inside sales + lead quali): header linha 2, funil completo no topo |
| `src/integrations/breakeven_projection.py` | Motor financeiro compartilhado (MC, alavanca mídia, breakeven acumulado) |
| `src/integrations/breakeven_naming.py` | Título canônico `[Colli & CO] - [Cliente] - Breakeven … - AI Auto` |
| `src/integrations/breakeven_personalization.py` | Leitura estratégica e labels do Resumo a partir do config/GP |
| `projects/<cliente>/config-inside-sales-template.json` | Config validado por cliente |

### Arquivos que **não** mudam para inside sales

- Lógica e-commerce pura em `generate_breakeven.py` (blocos `else`)
- `validate_config.py`, `generate_report.py` (upstream Jefferson) — salvo extensões futuras
- Projetos e-commerce da carteira — seguem pipeline original da skill

---

## 5. Pipeline — próximo cliente inside sales

### Pré-requisitos

1. Growth Pack baixado em `projects/<ordem>-<slug>/source/growthpack.xlsx`
2. `source/manifest-entry.json` com fee, mídia, margem do Flow
3. Gate de alinhamento (`gate.md`) — fee/mídia/margem confirmados
4. Funil inside sales identificado no GP (impressões…vendas)

### Nomenclatura de entrega (desde jun/2026)

**Padrão canônico** (Google Sheets e arquivo `.xlsx` local):

```text
[Colli & CO] - [Nome do Cliente] - Breakeven Inside Sales - AI Auto
[Colli & CO] - [Nome do Cliente] - Breakeven E-commerce - AI Auto
```

Implementado em `src/integrations/breakeven_naming.py`. O gerador usa esse nome quando `--output` é omitido; o upload deriva o título via `--config`.

**Exemplo (inside sales):**  
`[Colli & CO] - [MANCHESTER STORE LTDA] - Breakeven Inside Sales - AI Auto`

### Passos (PowerShell, pasta `projects/breakeven-auto`)

```powershell
# 1. Gerar config (hoje: script Soma — generalizar ou copiar/adaptar)
python src/integrations/build_soma_inside_sales_template_config.py `
  --project-folder projects/<ordem>-<slug> `
  --output projects/<ordem>-<slug>/config-inside-sales-template.json

# 2. Validar
python vendor/autobreakeven/breakeven-projetos/scripts/validate_config.py `
  --config projects/<ordem>-<slug>/config-inside-sales-template.json

# 3. Gerar XLSX raw (nome padrão Colli & CO se --output omitido)
python vendor/autobreakeven/breakeven-projetos/scripts/generate_breakeven.py `
  --config projects/<ordem>-<slug>/config-inside-sales-template.json `
  --output projects/<ordem>-<slug>/spreadsheet/breakeven.raw.xlsx

# 4. Relabel PT (títulos, refs Breakeven 7M → Breakeven)
python src/integrations/relabel_inside_sales_template.py `
  projects/<ordem>-<slug>/spreadsheet/breakeven.raw.xlsx `
  --output projects/<ordem>-<slug>/spreadsheet/breakeven.xlsx

# 5. Upload Google Sheets (título derivado do config)
python src/integrations/upload_xlsx_to_google_sheet.py `
  projects/<ordem>-<slug>/spreadsheet/breakeven.xlsx `
  --config projects/<ordem>-<slug>/config-inside-sales-template.json `
  --share-anyone
```

### Checklist pós-geração

- [ ] **Dados Fonte** — bench com 8 colunas (Soma/lead quali) ou 7 (sem lead quali): Mês + etapas reais do GP
- [ ] **Dados Fonte** — taxas mediana alinhadas ao funil (incl. Leads → Lead quali quando aplicável)
- [ ] **Funil Completo G12** — linha **CPM** preenchida (`=verba/impressões×1000`)
- [ ] **Premissas** — “Impressões acumuladas” e “SQLs acumulados” (não Sessões/Pedidos)
- [ ] **Breakeven** — linha 2 com títulos de coluna; funil completo no topo (v16+); **sem** bloco inferior duplicado
- [ ] **Breakeven** — funil mínimo termina em Taxa SQLs → Vendas → Vendas (sem linhas neutras)
- [ ] **Breakeven** — **não** usar Taxa Impressões→SQLs nem SQLs→Vendas fixo em 100% no topo
- [ ] **Taxa de conversão do funil** = Leads → Vendas (não impressões → vendas ~0,01%)
- [ ] Projeção até breakeven (máx. 36 meses), não fixo em 7
- [ ] **Funil Completo / Dados Fonte** — bench **Leads → Vendas** ≈ 2–4% (mediana vendas/leads), **não** ~0,01%
- [ ] Atualizar `projects/<ordem>-<slug>/qa.json`, `status.md` e `_context/status.md`

---

## 6. Horizonte e breakeven

- `MAX_PROJECTION_MONTHS = 36` em `generate_breakeven.py`
- Horizonte calculado até breakeven no cenário mínimo/realista (ou declara “não breakeva em N meses”)
- Soma (referência): breakeven cenário realista/mínimo no **Mês 25**; pessimista não breakeva em 36 meses

---

## 7. Correções técnicas acumuladas (piloto Soma)

| Versão | Problema | Correção |
|--------|----------|----------|
| v6 | `#DIV/0!` — Premissas apontava linha 12 fixa | Linha total dinâmica em Dados Fonte; `IFERROR` em divisões |
| v6 | `#REF!` — aba renomeada sem atualizar refs | `relabel_inside_sales_template.py` atualiza `'Breakeven 7M'` → `'Breakeven'` |
| v8 | Projeção travada em 7 meses | Horizonte dinâmico até breakeven |
| v9 | Conversão funil ~0,01% (impressões→vendas) | Linha 13 = Leads → Vendas (`Premissas F17`) |
| v10 | Vendas → Vendas no funil integrado | Funil simplificado; linhas e-commerce vazias |
| **v11** | SQLs/SQLs e Vendas/Vendas em Dados Fonte | Bench 6 colunas; taxas reais; Premissas inside sales |
| **v13** | Premissas Leads→Vendas fixo no bench (~2,8%) vs atual (~3,42%) | `lead_to_sale_rates`: Mês 1 = atual, rampa editável |
| **v14** | Funil Soma sem **Lead quali**; CPM vazio em Funil Completo G12 | `funnel_has_lead_quali`; etapa GP linha 19; CPM na projeção; caps 95% e piso CPS |
| **v15** | Premissas só tinham 3 taxas (pulava Lead quali→MQL) | 6 taxas editáveis + Leads→Vendas calculada (linha 21); Breakeven integrado referencia Premissas |
| **v16** | Breakeven sem headers; funil simplificado no topo; bloco funil duplicado embaixo | Layout unificado + header linha 2 |
| **v17** | Textos Dalpack (R$ 5 mil, “funil maio”); cenários sem alavanca de mídia → BEP Realista Mês 25 vs Breakeven Mês 29 | Motor financeiro único; textos do config; Realista alinhado ao mínimo |

**Entrega canônica Soma (v17):**  
https://docs.google.com/spreadsheets/d/1PCcoCc9tvSqrBMHldiAwhfNk2G7wqBpnspu7fV1hEuM/edit?usp=drivesdk

(v16 anterior: https://docs.google.com/spreadsheets/d/1l1QZQT5obJc3HSpCv75-PtYKNXWvBFX0Ul4QNuqIqsI/edit?usp=drivesdk)

---

## 8. Mapeamento interno config (compatibilidade skill)

O JSON ainda usa chaves e-commerce da skill para volumes/taxas internas.

**Soma (`funnel_has_lead_quali: true`):**

| Chave config | Significado inside sales |
|--------------|-------------------------|
| `session_view` | Impressões → Cliques |
| `view_add` | Cliques → Leads |
| `add_view_cart` | Leads → **Lead quali** |
| `viewcart_checkout` | **Lead quali → MQLs** |
| `checkout_shipping` | **MQLs → SQLs** |
| `shipping_payment` | **SQLs → Vendas** |
| `payment_order`, `order_sale` | Neutros `[1.0]` — não exibir |

**Funil 6 etapas (sem lead quali):**

| Chave config | Significado |
|--------------|-------------|
| `add_view_cart` | Leads → MQLs |
| `viewcart_checkout` | MQLs → SQLs |
| `checkout_shipping` | Neutro `[1.0]` |

`source_months`: `[mês, fee, mídia, impressões, sqls, vendas, faturamento]`

---

## 9. Limitações conhecidas

- `build_soma_inside_sales_template_config.py` está acoplado ao layout GP da Soma (`6.0 Acompanhamento Mensal`, linhas fixas). Próximo passo: generalizar para `build_inside_sales_template_config.py` lendo linhas do `inspection.json`.
- Fee/margem históricos no GP podem divergir do Flow — registrar no `gate.md`.
- Versão “inside sales nativo” (`generate_inside_sales_breakeven.py`) existe mas **não** é o padrão visual; usar só se Rafael pedir estrutura diferente da skill.

---

## 10. Próximos projetos inside sales na carteira

Antes de rodar o pipeline:

1. Confirmar no GP que o funil é inside sales (não e-commerce).
2. Setar `"project_model": "Inside Sales"` no config.
3. **Não** rodar relabel com mapeamentos que recriem etapas neutras.
4. Replicar checklist §5 e salvar link em `qa.json` + `_context/status.md`.

---

## Referências

- Decisões: `_context/decisions.md`
- Status carteira: `_context/status.md`
- Piloto Soma: `projects/17-soma-solucoes-financeiras-ltda/`
- Integração Strategy Review: `docs/strategy-review-integration.md`
