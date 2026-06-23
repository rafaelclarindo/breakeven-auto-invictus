---
name: breakeven-auto-invictus
description: Automação Invictus de breakeven — Strategy Review + Flow Cockpit + skill Auto Breakeven (Jefferson). Gera relatório Markdown e planilha Colli & CO com cenários Pessimista/Realista/Otimista, aba Breakeven unificada (inside sales + e-commerce), projection_rules e contexto sazonal da SR col. O. Use para qualquer cliente da carteira Breakeven Auto ou reprodução do pipeline QGI.
---

# Breakeven Auto — Invictus

Skill consolidada: **upstream** (`vendor/autobreakeven/breakeven-projetos/SKILL.md`) + **extensões QGI** (`src/integrations/`, `docs/`).

## Princípios Invictus

- **Motor compartilhado** (`breakeven_projection.py`, `breakeven_personalization.py`): inside sales e e-commerce — Realista = mínimo, Mês 1 = taxa atual, cap 95%, `projection_rules`.
- **Funil:** inferido do Growth Pack + `project_model` (`Inside Sales` vs `E-commerce D2C`).
- **Aba Breakeven unificada v16+:** inside sales + lead quali **ou** e-commerce (`breakeven_unified_sheet.py`).
- **Contexto sazonal:** coluna **O** da Strategy Review → `context.seasonal` + Leitura estratégica no Resumo.
- **Cabeçalhos de cenário:** meses calendário (`Jul/26`), não `Mês 1` — regra dia **15/16** (ver abaixo).

## Cabeçalhos mensais (Pessimista / Realista / Otimista)

| Dia da geração | 1ª coluna |
|----------------|-----------|
| Qualquer dia | **mês seguinte** (ex.: jun/26 → Jul/26) |

Implementação: `projection_month_headers()` em `src/integrations/breakeven_projection.py`.

```bash
python vendor/autobreakeven/breakeven-projetos/scripts/generate_breakeven.py \
  --config projects/<slug>/config.json \
  --output projects/<slug>/spreadsheet/breakeven.xlsx \
  --reference-date 2026-06-22
```

## Pipeline QGI (por cliente)

```powershell
cd projects/breakeven-auto

# 1. Manifest + pastas
python src/integrations/build_strategy_review_manifest.py
python src/integrations/prepare_strategy_review_projects.py

# 2. Growth Pack local
python src/integrations/download_growthpacks.py --orders <N>

# 3. Contexto SR (fee, mídia, margem, GP, col. O sazonal)
python src/integrations/read_strategy_review_row.py "<nome projeto>"

# 4. Config
# Inside sales: build_soma_inside_sales_template_config.py
# E-commerce GP 3.0: build_config_from_growthpack_acompanhamento.py --seasonal-context-file source/seasonal-context.txt

# 5. Validar + gerar
python vendor/autobreakeven/breakeven-projetos/scripts/validate_config.py projects/<slug>/config.json
python vendor/autobreakeven/breakeven-projetos/scripts/generate_breakeven.py --config projects/<slug>/config.json

# 6. Upload
python src/integrations/upload_xlsx_to_google_sheet.py projects/<slug>/spreadsheet/breakeven.xlsx --config projects/<slug>/config.json --share-anyone
```

## Documentação

| Tópico | Arquivo |
|--------|---------|
| Inside sales + motor compartilhado | `docs/inside-sales-breakeven.md` |
| Strategy Review + Flow | `docs/strategy-review-integration.md` |
| Decisões | `_context/decisions.md` |
| Skill upstream Jefferson | `vendor/autobreakeven/breakeven-projetos/SKILL.md` |

## Nomenclatura de entrega

`[Colli & CO] - [Cliente] - Breakeven [Inside Sales | E-commerce] - AI Auto` (`breakeven_naming.py`).

## Saída

- Link Google Sheets (público leitor)
- Atualizar `projects/<slug>/status.md`, `qa.json`, `_context/status.md`
