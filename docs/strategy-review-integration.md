# Strategy Review × Auto Breakeven

## Planilha operacional

| Campo | Valor |
|-------|--------|
| URL | https://docs.google.com/spreadsheets/d/1MrUklD9tulNHsxWmAh3fcUUBlBdY-IHzSUuEPAz32YQ/edit#gid=226918461 |
| Aba | **Start Strategy Review** |
| Projetos | 74 (coluna **B**, ordem de prioridade HS) |

### Colunas na planilha (referência)

| Col | Conteúdo |
|-----|----------|
| B | Projeto |
| H | Fee (snapshot manual) |
| J–L | FEE / Mídia / Margem (preenchimento Flow — sessão 20/06) |
| M | Link do Break-even |
| N | Link do GrowthPack (vazio — links corretos vêm do Cockpit) |

## Fonte oficial no Flow Cockpit

Vertical **Gestão de Tráfego** → coluna **GrowthPack Atualizado**:

```
paid_traffic_growthpack_updated_link
```

Outros insumos para pré-preencher o JSON da skill:

| Campo skill | Coluna Flow |
|-------------|-------------|
| `monthly_fee` / Fee | `fee` |
| `monthly_media` | `campaigns_budget_milestone_total_qty` |
| `margin` | `results_contribution_margin_pct` |

**Não usar** `results_breakeven_spreadsheet_link` como Growth Pack — é o link de break-even da vertical Resultados.

## Manifest (automático)

```powershell
cd projects/breakeven-auto
python src/integrations/build_strategy_review_manifest.py
```

Gera `assets/strategy_review_manifest_<YYYY-MM-DD>.json`:

```json
{
  "sheet_id": "1MrUklD9…",
  "sheet_tab": "Start Strategy Review",
  "generated_at": "2026-06-20",
  "projects": [
    {
      "order": 1,
      "name": "MANCHESTER …",
      "fee": 6073.85,
      "media_planned": 12000,
      "margin_pct": 20,
      "growthpack_updated_link": "https://docs.google.com/spreadsheets/d/…"
    }
  ]
}
```

Depois do manifest, preparar a carteira local:

```powershell
python src/integrations/prepare_strategy_review_projects.py
```

Esse passo gera:

- `assets/strategy_review_readiness_<YYYY-MM-DD>.json`
- `projects/index.md`
- `projects/index.json`
- `projects/<ordem>-<slug>/` para cada projeto da Strategy Review

## Pipeline por cliente (skill Jefferson)

Cada cliente deve ser trabalhado dentro da própria pasta:

```text
projects/<ordem>-<slug>/
├── source/growthpack.xlsx
├── source/manifest-entry.json
├── inspection/inspection.json
├── gate.md
├── config.json
├── report/
├── spreadsheet/
├── qa.json
└── status.md
```

1. Baixar GP do link → `projects/<ordem>-<slug>/source/growthpack.xlsx` (Google Sheets: Arquivo → Baixar → `.xlsx`).
2. `inspect_growthpack.py` → `projects/<ordem>-<slug>/inspection/inspection.json`.
3. Gate de alinhamento (SKILL.md) — confirmar fee/mídia/margem com manifest + GP.
4. Montar `config.json` a partir de `assets/config-exemplo-dalpack.json`.
5. `validate_config.py` → `generate_report.py` + `generate_breakeven.py`.

### Regra de funil

O funil da planilha precisa respeitar o funil real encontrado no Growth Pack do cliente.

Exemplos:

- E-commerce: sessões, view item, add cart, checkout, purchase, faturamento.
- Inside sales: impressões, cliques, leads, MQLs, SQLs, vendas, faturamento.

Para e-commerce, o funil padrão da skill continua válido quando esse é o funil do Growth Pack. Para inside sales, sempre analisar o Growth Pack e usar as etapas encontradas ali. Não converter inside sales para etapas e-commerce quando essas etapas não existem no Growth Pack.

**Inside sales (Invictus):** pipeline completo, checklist e regra “não alterar e-commerce” em [`inside-sales-breakeven.md`](inside-sales-breakeven.md). Exige `"project_model": "Inside Sales"` no config JSON.

O parser/gate deve registrar as etapas do funil, a fonte de cada linha/aba e a projeção deve usar essas mesmas etapas.

### Breakeven histórico

Antes de projetar, calcular o resultado acumulado histórico com os meses válidos do Growth Pack:

```text
Resultado histórico = faturamento acumulado × margem - (fee acumulado + mídia acumulada)
```

Se o resultado histórico já for positivo, sinalizar que o breakeven já foi atingido no histórico e mostrar o primeiro mês em que o acumulado virou positivo. A projeção futura continua existindo, mas não deve tratar o projeto como se ainda precisasse recuperar carry over.

### Horizonte de projeção

A projeção não deve ficar travada em 7 meses. O gerador deve:

- projetar mês a mês até o breakeven acumulado acontecer;
- aceitar breakeven antes do mês 7;
- continuar depois do mês 7 quando o cenário só breakevar mais tarde;
- declarar `não breakeva no horizonte` quando não houver breakeven dentro do limite definido.

O limite do horizonte deve ser uma premissa explícita no config, não uma regra fixa escondida no código.

Comandos de apoio para lote/piloto:

```powershell
python src/integrations/download_growthpacks.py --status ready,needs-review --orders 1,2,3,4,5
python src/integrations/inspect_downloaded_growthpacks.py --orders 1,2,3,4,5
```

Observação: se o Drive API retornar `404` para um Growth Pack, o downloader tenta fallback via export público do Google Sheets. Se retornar `401`, o link existe, mas exige permissão/autenticação; nesse caso o projeto fica pendente até o compartilhamento ser liberado ou o arquivo ser baixado manualmente para `source/growthpack.xlsx`.

## Relação com outros projetos QGI

| Projeto | Papel |
|---------|--------|
| **breakeven-auto** (este) | Método Jefferson, lote Strategy Review, `.md` + `.xlsx` fórmulas |
| **breakeven-dashboard** | UI chat, análise ad-hoc, export Excel simplificado |
| **monitor-invictus** | Breakeven tab oficial Flow + ingest `sync_flow_breakevens.py` |
| **tatico-gerencial** | ScoreOps, export HS, antecipação |
