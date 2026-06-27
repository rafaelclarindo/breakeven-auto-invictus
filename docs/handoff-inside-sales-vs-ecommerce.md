# Handoff — Inside Sales vs E-commerce (Breakeven Auto)

**Criado:** 2026-06-22  
**Autor da sessão:** pipeline QGI / Breakeven Auto (Cursor)  
**Destinatário:** próxima IA que vai analisar e evoluir a **parte e-commerce**  
**Projeto:** `projects/breakeven-auto/`

---

## 1. Objetivo deste documento

Registrar:

1. **O que é compartilhado** e **o que é separado** entre inside sales e e-commerce no Breakeven Auto.
2. **Tudo que foi feito** na sessão de jun/2026 (correções LT/MRR, entregas, perfis GP).
3. **Onde a próxima IA deve começar** para e-commerce — sem reutilizar por engano a lógica inside sales.

Leia também: `_context/decisions.md`, `docs/inside-sales-breakeven.md`, `docs/RUNBOOK-executor-inside-sales.md`.

---

## 2. Resposta direta: a lógica inside sales vai no e-commerce?

**Não integralmente.**

| Camada | Inside Sales | E-commerce | Compartilhado? |
|--------|--------------|------------|----------------|
| **Builder de config** | `build_growthpack_inside_sales_config.py` + perfis (`msys`, `sigo`, `malbork`, `suprimedico`…) | `build_growthpack_ecommerce_config.py` + perfis (`bublu`, `alumtech`) | **Não** |
| **Funil** | Impressões → Cliques → Leads → MQL → SQL → Vendas | Sessões → View item → Add cart → Checkout → Payment → Purchase | **Não** |
| **Gerador de planilha** | `vendor/autobreakeven/.../generate_breakeven.py` | Mesmo arquivo | **Sim** |
| **Motor financeiro** | `src/integrations/breakeven_projection.py` | Mesmo módulo | **Sim** |
| **Personalização / Resumo** | `breakeven_personalization.py` | Mesmo módulo | **Sim** |
| **Mediana 3M + tetos por etapa** | Implementado no builder IS | Idêntico no builder e-commerce (`build_growthpack_ecommerce_config.py`) | **Sim** |
| **MRR / LTV (col. L SR)** | Opt-in via `strategy_review_fields.py` | Decisão explícita: **e-commerce intocável** por enquanto | **Não** (IS only) |
| **Aba Breakeven unificada** | `breakeven_unified_sheet.py` | Mesmo módulo (`funnel_mode=ecommerce`) | **Sim** (layout) |

### Interruptor no config

```json
"project_model": "Inside Sales"   → ramos IS no generate_breakeven.py
"project_model": "Marketplace"    → 3º funil: Impressões→Cliques→Visitas→Compras→Faturado (ver §6)
"project_model": "E-commerce D2C" → funil GA4 / sessões
(omitir Inside Sales)             → caminho e-commerce original Jefferson
```

Implementação: `is_inside_sales_model()` / `is_marketplace_model()` em `generate_breakeven.py`.
Marketplace reusa o trilho IS internamente (`is_inside_sales = True`), só relabela e oculta
as 2 taxas pass-through.

---

## 3. Strategy Review — colunas críticas

Layout conferido em `read_strategy_review_row.py` (aba `Start Strategy Review`):

| Col | Nome | Uso correto |
|-----|------|-------------|
| **H** | LT (Life Time) | Meses de contrato ativo na V4 → `lt_months` no manifest. **Nunca** multiplica ticket. |
| **I** | Fee | Premissa |
| **J** | Mídia | Premissa Flow |
| **K** | Margem | Premissa |
| **L** | **MRR** | Recorrência do ticket. **Só** se preenchida (ex.: `"12 meses"`). `"Sem recorrência"` → **sem** multiplicador. |
| **N** | Growth Pack | Link GP |
| **P** | Contexto sazonal | Texto estratégico no Resumo |

### Regra MRR (codificada 2026-06-22)

- Módulo: `src/integrations/strategy_review_fields.py`
- `resolve_mrr_from_manifest()` — **ignora** `tm_recurrence_months` numérico sem texto MRR na col. L (evita confundir LT com recorrência).
- `apply_sr_fields_to_manifest(manifest, sr_row)` — lê SR online e grava `lt_months` (H) e `mrr_*` (L) só quando L preenchida.
- Batch SR: `batch_sr_rows_1_6.py` usa `apply_sr_fields_to_manifest()` — não hardcodar LT como recorrência.

### Erro histórico corrigido

O batch SR 1–6 gravava **LT (col. H)** como `tm_recurrence_months` → ticket × N inflado (ex.: Malbork ×30, Vilela ×22). **LT ≠ MRR.**

---

## 4. Inside Sales — o que a sessão consolidou

### Pipeline padrão

```powershell
cd projects/breakeven-auto

# 1. Manifest (LT/MRR da SR)
python src/integrations/read_strategy_review_row.py "<NOME>"

# 2. Config
python src/integrations/build_growthpack_inside_sales_config.py `
  --project-folder projects/<slug> --profile <perfil> `
  --reference-date 2026-06-22 --gp-source online [--from-label Mmm/YY]

# 3. Planilha
python vendor/autobreakeven/breakeven-projetos/scripts/generate_breakeven.py `
  --config projects/<slug>/config.json `
  --output projects/<slug>/spreadsheet/breakeven.xlsx `
  --reference-date 2026-06-22

# 4. Upload
python src/integrations/upload_xlsx_to_google_sheet.py `
  projects/<slug>/spreadsheet/breakeven.xlsx `
  --config projects/<slug>/config.json --share-anyone [--replace-id <id>]
```

### Projeção de taxas (inside sales)

- Baseline M1 = **mediana dos últimos 3 meses** por etapa (não média).
- Janela: últimos 3 meses **excluindo** o mês corrente (ex.: ref. Jun/26 → Mar · Abr · Mai/26).
- Exceção SQL→Venda: últimos 3 meses com vendas > 0 e SQLs > 0.
- Tetos de saturação: `max(mediana 3M, baseline M1) × 1,1`, cap 95%.
- CPS projeção: mediana 3M (mesma janela).

### Perfis GP inside sales (implementados)

| Perfil | Cliente / nota |
|--------|----------------|
| `msys` | Mold Systems — aba 6.0 consolidada |
| `cdsi` | Centro do Silicone / Vilela |
| `sigo` | SIGO ERP — impressões L8, mídia L7 |
| `vicentini` | `baseline_mode: operational`, pré-receita |
| `malbork` | Impressões L29, `date_fallback: 2`, ticket L6, normalize MQL/SQL |
| `visoflex` | GP 4.0 aba 2.2, `--from-label Jan/26` |
| `alumtech` | **Marketplace (3º funil)** — perfil no `build_growthpack_inside_sales_config.py` com flag `"marketplace": True`; `project_model: "Marketplace"`; ver seção 6 |
| `primeset` | Layout datetime row 2, funil L7–17 |

---

## 5. E-commerce — onde a próxima IA deve focar

### Entrada principal existente

| Arquivo | Cliente piloto | Notas |
|---------|----------------|-------|
| `src/integrations/build_bublu_ecommerce_config.py` | BUBLU | GP sessões L17, faturamento L42, `project_model: "E-commerce D2C"` |
| Pipeline Jefferson original | Dalpack / template skill | `generate_breakeven.py` **sem** `Inside Sales` no model |
| `build_config_from_growthpack_acompanhamento.py` | GP 3.0 genérico | Mencionado no SKILL.md — validar se ainda é o caminho preferido |

### Funil e-commerce (GA4)

Sessões → View item → Add to cart → View cart → Begin checkout → Add shipping → Add payment → Purchase.

Taxas e labels diferentes do IS. **Não** usar MQL/SQL/impressões do inside sales.

### O que NÃO aplicar do IS ao e-commerce (decisão Rafael)

- MRR / LTV × meses (`tm_recurrence_months`) — gated em `is_inside_sales` no gerador.
- Premissas B28:B32 com 5 taxas Imp→Clique…SQL→Venda.
- Perfis `build_growthpack_inside_sales_config.py`.
- RUNBOOK inside sales (`docs/RUNBOOK-executor-inside-sales.md`).

### O que pode ser reutilizado (com cuidado)

- `breakeven_projection.py` — regras financeiras, cabeçalhos calendário, Realista = mínimo.
- `breakeven_personalization.py` — resumo estratégico, sazonal col. P.
- `strategy_review_fields.py` — LT e MRR da SR (MRR provavelmente off para e-commerce D2C).
- Upload / naming: `upload_xlsx_to_google_sheet.py`, `breakeven_naming.py`.

### Pendências e-commerce (para análise)

1. ~~Builder genérico e-commerce~~ → **implementado** (`build_growthpack_ecommerce_config.py`).
2. **Marketplace** (Alumtech): perfil `alumtech` no builder e-commerce com funil simplificado (visitas→compras); `project_model: "E-commerce D2C"`.
3. ~~Mediana 3M + tetos~~ → **portados** do IS (CPS = Investimento/Sessões).
4. GP com dados inválidos (datetime em células de receita) — tratamento em `parse_num` retorna 0; documentar por cliente (ex.: Jun/25 Alumtech receita=0 excluído do funil).

---

## 6. Caso marketplace: Alumtech — TERCEIRO FUNIL (Oxxy Motos)

**Marketplace é um 3º funil de pleno direito** (ao lado de IS e E-commerce), com etapas
próprias do GrowthPack: **Impressões → Cliques → Visitas → Compras → Faturado**.
Decisão Rafael 2026-06-25: "só muda o funil, a lógica de projeção é a mesma".

### Interruptor no config

```json
"project_model": "Marketplace"   → ramos marketplace no generate_breakeven.py
```

`is_marketplace_model()` em `generate_breakeven.py` — `"marketplace" in project_model.lower()`.

### Como funciona (reuso do trilho Inside Sales)

Marketplace **reusa toda a estrutura interna do Inside Sales** (`is_inside_sales = True`
internamente: entrada por impressões, CPS por impressão, 5 estágios, mesmas fórmulas/refs).
Os números são idênticos ao IS. O que muda:

1. **Relabel** das etapas visíveis: Cliques→Visitas, Visitas→Compras, Vendas→Compras,
   Receita→Faturado, "Custo por SQL"→"Custo por compra", etc.
2. **Ocultação** (xlsxwriter `set_row hidden`) das 2 taxas pass-through (MQL→SQL, SQL→Venda
   = 1,0) e dos nós/CPS duplicados. As linhas continuam existindo e calculando (funil
   auditável), só ficam ocultas → visão limpa de 3 taxas + Faturado. **Zero reescrita de
   fórmula → zero risco de regressão para as planilhas IS/EC.**

Linhas ocultas: cenário `(22,23,24,25,35)`; integrada `(43-48,56)`; financeiro 7M `(10,11,12)`;
premissas controle `(23,24,31,32)`.

### Mapeamento GP (perfil `alumtech`, flag `"marketplace": True`)

| Rate (interno) | GP | Label marketplace |
|----------------|-----|-------------------|
| `impression_click` | L13/L11 | Taxa Impressões → Cliques (CTR) |
| `click_lead` | L15/L13 | Taxa Cliques → Visitas (**amplificação orgânica**, pode ser >1 → multiplicador fixo) |
| `lead_mql` | L20/L15 | Taxa Visitas → Compras (~3%) |
| `mql_sql`, `sql_sale` | L20/L20 | pass-through 1,0 (ocultas) |

- **Amplificação orgânica** (`build_growthpack_inside_sales_config.py`): quando a mediana de
  uma etapa > 1,0 (Visitas > Cliques), o builder a trata como multiplicador fixo (sem cap 0,95,
  sem crescimento mês a mês) — `stage_ceilings[rk] = baseline_rates[rk]`.
- CPS = Investimento/Impressões. MRR: `"Sem recorrência"` → sem multiplicador.
- Entrega: https://docs.google.com/spreadsheets/d/1jqA0IEqzPtrQ11KqMvgZ9tuhLgOx1XH_N1JLCwkHYGY/edit?usp=drivesdk

**Histórico:** v1 IS adaptado · v2 e-commerce builder (descartado: gerava todos os meses
"BREAKEVEN" e funil GA4 inadequado) · **v3 (atual): 3º funil Marketplace dedicado.**

---

## 7. Entregas desta sessão (inside sales)

Registro completo: `_context/delivered-breakevens.json`

| Cliente | SR | Perfil | Pipeline | Link |
|---------|-----|--------|----------|------|
| Vilela Campos | 1 | `cdsi` | IS · corrigido LT≠MRR | [planilha](https://docs.google.com/spreadsheets/d/1nD1eyZEmHuiAXOoP1IOS7yT1FZxN8MULHa7pbreKe2Q/edit?usp=drivesdk) |
| SIGO ERP | 4 | `sigo` | IS · corrigido LT≠MRR | [planilha](https://docs.google.com/spreadsheets/d/1RJ3F5qlKiUraMGjCd72_DwPU_Jntiaivbjx1chbwoHs/edit?usp=drivesdk) |
| Vicentini | 5 | `vicentini` | IS · desde Dez/25 | [planilha](https://docs.google.com/spreadsheets/d/1UauGd7XtyEbL9klcg9tjCM9e2ZG4TcVtaMWZegA-4Rk/edit?usp=drivesdk) |
| Malbork | 6 | `malbork` | IS · GP completo Jan/25–Jun/26 + fix data L2 | [planilha](https://docs.google.com/spreadsheets/d/18TL7jRxb54rJPbNoHZBJH3aLRj2RxWZKUpMxSboNQvQ/edit?usp=drivesdk) |
| Visoflex | 8 | `visoflex` | IS · Jan/26+ · sem recorrência | [planilha](https://docs.google.com/spreadsheets/d/1b30Tabrr5hAtcoTj5vcqDzyKVXgaUug_lGP70t7nIF4/edit?usp=drivesdk) |
| **Alumtech** | 8 | `alumtech` | E-commerce marketplace (Oxxy GP) | [planilha](https://docs.google.com/spreadsheets/d/1jqA0IEqzPtrQ11KqMvgZ9tuhLgOx1XH_N1JLCwkHYGY/edit?usp=drivesdk) |
| MSYS | 43 | `msys` | IS · referência · MRR 12 meses (col. L) | [planilha](https://docs.google.com/spreadsheets/d/1u_JUUJ0awc8IUyycF1VSlj7OO_hO2yiVpojMtnzxTDg/edit?usp=drivesdk) |

### Correções Malbork (destaque)

1. **v1:** parser ignorava colunas 2025/2026 (data na L2, não L4).
2. **v2:** ticket × 30 (LT confundido com MRR).
3. **v3:** GP SR completo + ticket sem multiplicador.

### Bloqueados (GP 403 OAuth)

- Maidpad (SR 2) · Panamericano (SR 3) — aguardam share do GP.

---

## 8. Arquivos-chave (mapa rápido)

```
projects/breakeven-auto/
├── docs/
│   ├── handoff-inside-sales-vs-ecommerce.md   ← ESTE ARQUIVO
│   ├── inside-sales-breakeven.md
│   └── RUNBOOK-executor-inside-sales.md       ← só IS
├── _context/
│   ├── decisions.md
│   ├── delivered-breakevens.json
│   └── status.md
├── src/integrations/
│   ├── build_growthpack_inside_sales_config.py  ← IS builder + perfis
│   ├── build_growthpack_ecommerce_config.py     ← e-commerce builder genérico (perfis: bublu, alumtech)
│   ├── build_bublu_ecommerce_config.py          ← e-commerce piloto legado (hardcoded Jun/26)
│   ├── strategy_review_fields.py                ← LT (H) + MRR (L)
│   ├── growthpack_sheets_reader.py
│   ├── breakeven_projection.py                  ← motor compartilhado
│   ├── breakeven_personalization.py
│   ├── breakeven_unified_sheet.py
│   └── batch_sr_rows_1_6.py
└── vendor/autobreakeven/breakeven-projetos/scripts/
    └── generate_breakeven.py                    ← gerador único (ramifica IS/EC)
```

---

## 9. Checklist para a IA de e-commerce

- [x] Ler `build_bublu_ecommerce_config.py` e comparar com `generate_breakeven.py` (ramos `not is_inside_sales`).
- [x] Marketplace (Alumtech) → perfil `alumtech` no builder e-commerce (`project_model: "E-commerce D2C"`).
- [x] Avaliar builder genérico e-commerce (como `GP_PROFILES` do IS) — **implementado em `src/integrations/build_growthpack_ecommerce_config.py`** com perfil `bublu`; metodologia em `RUNBOOK-executor-ecommerce.md`.
- [x] Confirmar tratamento MRR col. L para e-commerce — **off por default** (só opt-in se col. L preenchida, raro em D2C).
- [x] Revisar se mediana 3M / tetos / CPS devem ser portados do IS — **sim, metodologia idêntica** (CPS = Investimento/Sessões nos 3 últimos meses).
- [x] Documentar layouts GP e-commerce conhecidos — Bublu: sessões L17, revenue L42, aba `6.0 Acompanhamento Mensal`.
- [x] Não usar `build_growthpack_inside_sales_config.py` para clientes GA4 puros.

---

## 10. Referências externas

- Strategy Review: `https://docs.google.com/spreadsheets/d/1MrUklD9tulNHsxWmAh3fcUUBlBdY-IHzSUuEPAz32YQ/edit`
- OAuth: `projects/assessor-pessoal/mcp/credentials/google_sheets_token.json`
- Skill Jefferson upstream: `vendor/autobreakeven/breakeven-projetos/SKILL.md`
