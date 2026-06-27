# Breakeven — Auto

> **LEIA `_context/status.md` e `_context/decisions.md` ANTES DE QUALQUER AÇÃO.**

## O que é

Automação de **análise de breakeven** para a carteira Invictus (aba **Start Strategy Review**), combinando:

1. **Skill Auto Breakeven** ([jeffersonvieira-hue/autobreakeven](https://github.com/jeffersonvieira-hue/autobreakeven)) — relatório Markdown + planilha `.xlsx` com fórmulas, cenários Pessimista/Realista/Otimista, bench por mediana do LT, breakeven da competência e carry over.
2. **Cockpit Flow** — insumos por projeto: Fee, mídia prevista, margem, link **GrowthPack Atualizado** (`paid_traffic_growthpack_updated_link`).
3. **Planilha Strategy Review** — ordem e recorte dos 74 projetos (coluna B).

Diferente de `breakeven-dashboard` (chat Node + Claude Haiku, porta 3010): aqui o motor é **Python + skill agentica**, focado em lote/carteira e método Jefferson.

## O que o Auto Breakeven faz (upstream)

| Entrada | Saída |
|---------|--------|
| Growth Pack `.xlsx` (funil + fee + mídia + faturamento) | Relatório `[Gerência] - [Análise e Estratégia] - [Cliente].md` |
| Margem de contribuição confirmada | Planilha `[Colli & CO] - [Cliente] - Breakeven Inside Sales|E-commerce - AI Auto` |
| LT (meses com fee no GP) | Bench interno (mediana por etapa) |
| Funil do último mês fechado | Cenários 7M + funil inverso |

Workflow da skill: inspecionar GP → gate de alinhamento → JSON config → `generate_report.py` + `generate_breakeven.py`.

**Inside sales (Invictus):** ver [`docs/inside-sales-breakeven.md`](docs/inside-sales-breakeven.md) — exige `"project_model": "Inside Sales"` no config. E-commerce usa o pipeline original sem esse campo.

**Handoff IS vs E-commerce (jun/2026):** [`docs/handoff-inside-sales-vs-ecommerce.md`](docs/handoff-inside-sales-vs-ecommerce.md) — arquitetura compartilhada/separada, entregas da sessão e guia para IA analisar e-commerce.

## Pipeline QGI (este projeto)

```
Strategy Review (col B) ──ordem──┐
                                 ├── manifest JSON ──► skill breakeven-projetos (por cliente)
Flow Cockpit (Gestão Tráfego) ───┘         │
  • paid_traffic_growthpack_updated_link     ├──► .md estratégia
  • fee                                      └──► .xlsx projeção
  • campaigns_budget_milestone_total_qty
  • results_contribution_margin_pct
```

## Comandos

```powershell
# dependências da skill
cd projects/breakeven-auto
.\ops\setup.ps1

# manifest da carteira (ordem Strategy Review + dados Flow)
python src/integrations/build_strategy_review_manifest.py

# readiness + uma pasta por projeto
python src/integrations/prepare_strategy_review_projects.py

# baixar/inspecionar Growth Packs de um piloto
python src/integrations/download_growthpacks.py --status ready,needs-review --orders 1,2,3,4,5
python src/integrations/inspect_downloaded_growthpacks.py --orders 1,2,3,4,5

# smoke da skill upstream
cd vendor/autobreakeven
bash smoke-test.sh
```

## Mapa de pastas

```
breakeven-auto/
├── CLAUDE.md
├── README.md
├── _context/
├── docs/
│   ├── strategy-review-integration.md
│   └── inside-sales-breakeven.md      ← playbook frente inside sales (não altera e-commerce)
├── src/integrations/
│   └── build_strategy_review_manifest.py
│   └── build_soma_inside_sales_template_config.py
│   └── relabel_inside_sales_template.py
│   └── prepare_strategy_review_projects.py
│   └── download_growthpacks.py
│   └── inspect_downloaded_growthpacks.py
├── projects/                      ← uma pasta por projeto da Strategy Review
├── vendor/autobreakeven/          ← fork local do repo Jefferson
│   └── breakeven-projetos/        ← SKILL.md + scripts
├── assets/                        ← manifests e sumários de execução
└── ops/setup.ps1
```

## Integrações

| Sistema | Uso |
|---------|-----|
| Flow Cockpit MCP | Fee, mídia prevista, margem, GrowthPack Atualizado |
| Google Sheet Strategy Review | Ordem dos projetos (`1MrUklD9tulNHsxWmAh3fcUUBlBdY-IHzSUuEPAz32YQ`, aba Start Strategy Review) |
| Monitor Invictus | Cliente MCP (`ingest/lib/mcp_client.py`) e `.env` compartilhado |
| Tático Gerencial | `clientExecutar.json` (match projeto ↔ documentId) |
| breakeven-dashboard | Complementar (UI conversacional); não substitui esta skill |

## Regras

1. **GrowthPack Atualizado** (`paid_traffic_growthpack_updated_link`) é a fonte de link — não confundir com `results_breakeven_spreadsheet_link` (Resultados).
2. **Mídia** = investimento previsto total (`campaigns_budget_milestone_total_qty`), não realizado.
3. A skill exige **GP em `.xlsx`** local — baixar do Google Sheets antes de `inspect_growthpack.py`.
4. Nunca inventar margem/fee/mídia — usar Flow + confirmação no gate da skill.
