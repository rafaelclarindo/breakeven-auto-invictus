# Breakeven — Auto

Automação de breakeven para a carteira **Strategy Review** (Invictus), usando a skill [Auto Breakeven](https://github.com/jeffersonvieira-hue/autobreakeven) + dados do Flow Cockpit.

## Quick start

```powershell
cd projects/breakeven-auto
.\ops\setup.ps1
python src/integrations/build_strategy_review_manifest.py
python src/integrations/prepare_strategy_review_projects.py

# piloto ou lote controlado
python src/integrations/download_growthpacks.py --status ready,needs-review --orders 1,2,3,4,5
python src/integrations/inspect_downloaded_growthpacks.py --orders 1,2,3,4,5
```

## O que gera

- `assets/strategy_review_manifest_<data>.json` — 74 projetos na ordem da planilha, com Fee, mídia prevista, margem e **GrowthPack Atualizado** do Cockpit.
- `assets/strategy_review_readiness_<data>.json` — classificação `ready`, `needs-review` ou `blocked`.
- `assets/growthpack_downloads_<data>.json` — resultado dos downloads de Growth Packs.
- `assets/growthpack_inspections_<data>.json` — resultado das inspeções dos Growth Packs baixados.
- `projects/<ordem>-<slug>/` — uma pasta por projeto, com insumos, inspeção, gate, config, relatório, planilha e QA.
- `projects/index.md` — índice executivo da carteira.

## Pasta por projeto

Cada projeto da Strategy Review deve ficar autocontido:

```text
projects/<ordem>-<slug>/
├── source/
│   ├── growthpack.xlsx
│   └── manifest-entry.json
├── inspection/
│   └── inspection.json
├── gate.md
├── config.json
├── report/
├── spreadsheet/
├── qa.json
└── status.md
```

## Skill upstream

Ver `vendor/autobreakeven/breakeven-projetos/SKILL.md` — inspecionar GP `.xlsx`, montar config JSON, gerar relatório `.md` e planilha de projeção `.xlsx`.

## Docs

- `docs/strategy-review-integration.md` — mapeamento planilha ↔ Flow ↔ skill
- `CLAUDE.md` — mapa do projeto no QGI
