# Snapshot — MSYS v25 · Tabela Premissas (controle funil)

**Data:** 2026-06-22  
**Cliente:** MSYS VISTORIAS LTDA (ordem 43)  
**Para:** handoff Claude / continuidade de sessão

---

## O que foi pedido

Adicionar na aba **Premissas** uma tabela com as etapas do funil e os cenários (Pessimista / Realista / Otimista). Ao alterar qualquer valor editável, o restante da planilha deve recalcular automaticamente.

## O que foi entregue (v25)

### Planilha

https://docs.google.com/spreadsheets/d/1u_JUUJ0awc8IUyycF1VSlj7OO_hO2yiVpojMtnzxTDg/edit?usp=drivesdk

### Tabela Premissas A18:D32

| Linhas Excel | Conteúdo | Editável |
|--------------|----------|----------|
| A19:D24 | Evolução mensal % por etapa × cenário | B20:D24 (amarelo) |
| A27:B32 | Taxas baseline M1 (ponto de partida) | B28:B32 (amarelo) |

**Etapas:** Imp→Clique, Clique→Lead, Lead→MQL, MQL→SQL, SQL→Venda.

**Defaults v25:**

| Etapa | Pessimista | Realista | Otimista |
|-------|------------|----------|----------|
| Imp→Clique | 3%/mês | 5%/mês | 7%/mês |
| Clique→Lead | 2% | 3% | 5% |
| Lead→MQL | 1% | 2% | 3% |
| MQL→SQL | 1% | 2% | 3% |
| SQL→Venda | 0,5% | 1% | 2% |

Baseline M1 = média Mar–Mai/26 do GP (Jun/26 excluído — mês parcial na ref. 22/jun).

### Onde recalcula

- Abas **Pessimista**, **Realista**, **Otimista**, **Mídia V4** — linhas 17, 19, 21, 23, 25 (taxas) e volumes downstream.
- **Premissas** curva mensal — colunas F+ linhas 14–18.
- **Breakeven 7M** — taxas linhas 15–19 (Realista).

### Lógica de fórmula

```
M1  = Premissas!$B$28 … $B$32
M2+ = MIN(0,95, taxa_mês_anterior × (1 + Premissas!$col$linha_avanço))
```

- Pessimista → col. B (linhas 20–24)
- Realista / Mídia V4 → col. C
- Otimista → col. D

Exemplo validado: `G17` = `'Premissas'!$B$28`; `H17` = `MIN(0.95,BG17*(1+'Premissas'!$C$20))`.

---

## Regras de negócio MSYS (consolidadas v18–v25)

| Tema | Regra |
|------|-------|
| LTV | Faturamento mensal GP × 12 |
| Col. C | Funil real Mai/26 (31 vendas) |
| Col. D | Breakeven mensal (fee + mídia Flow) ÷ margem; vendas = meta ÷ ticket GP mensal |
| Baseline projeção | Média Mar–Mai/26 |
| Mídia cenários | Flow R$ 34.500 fixo (P/R/O); Mídia V4 = rampa |
| Horizonte | Jul/26 → Dez/2030 (54 meses) |
| Recorrência | 12 meses (SR col. L) |

---

## Arquivos alterados

| Arquivo | Mudança |
|---------|---------|
| `generate_breakeven.py` | Tabela Premissas + `compound_stage_rate_formula()` + fórmulas nos cenários |
| `build_growthpack_inside_sales_config.py` | `SCENARIO_STAGE_MONTHLY_ADVANCE`, `baseline_funnel_rates`, `scenario_stage_monthly_advance` no config |
| `validate_breakeven_xlsx.py` | Checa G17→Premissas, M2 composto, LTV Mai/26 |
| `_context/status.md` | Sessão v25 |
| `_context/decisions.md` | Seção Premissas + MSYS |
| `docs/inside-sales-breakeven.md` | § tabela Premissas + MSYS v25 |
| `projects/43-msys-vistorias-ltda/status.md` | v25 |

---

## Comandos regeneração

```powershell
cd projects/breakeven-auto
python src/integrations/build_growthpack_inside_sales_config.py --project-folder projects/43-msys-vistorias-ltda --profile msys --reference-date 2026-06-22
python vendor/autobreakeven/breakeven-projetos/scripts/generate_breakeven.py --config projects/43-msys-vistorias-ltda/config.json --output projects/43-msys-vistorias-ltda/spreadsheet/breakeven.xlsx --reference-date 2026-06-22
python projects/43-msys-vistorias-ltda/scripts/validate_breakeven_xlsx.py
python src/integrations/upload_xlsx_to_google_sheet.py projects/43-msys-vistorias-ltda/spreadsheet/breakeven.xlsx --config projects/43-msys-vistorias-ltda/config.json --share-anyone --replace-id 1u_JUUJ0awc8IUyycF1VSlj7OO_hO2yiVpojMtnzxTDg
```

---

## Pendências para próxima sessão

1. **Breakeven 7M col. C** — motor legacy (LTV mensal somado → vendas absurdas). Alinhar ao funil Realista se Rafael pedir.
2. Generalizar tabela Premissas para outros clientes inside sales com `scenario_stage_monthly_advance` no builder.

---

## Teste sugerido no Sheets

Alterar **Premissas C20** (Realista Imp→Clique) de 5% para 8% → verificar Realista H17+ e Resumo Executivo.
