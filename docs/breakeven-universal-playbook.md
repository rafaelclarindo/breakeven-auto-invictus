# Breakeven Universal — Playbook de Construção

> **Acordos fechados jun/2026.** Referência canônica para Inside Sales, E-commerce e Marketplace.
> Baseado no desenvolvimento do breakeven Alumtech (Marketplace) e DALP (E-commerce).

---

## 1. Leitura obrigatória antes de qualquer breakeven

### 1.1 Strategy Review (SR)

Do cockpit/Flow, extrair por projeto:

| Campo | Onde |
|-------|------|
| Fee V4 | `monthly_fee` |
| Mídia prevista (Flow) | `campaigns_budget_milestone_total_qty` |
| Margem de contribuição | `results_contribution_margin_pct` |
| LT (meses de contrato com fee) | Contar colunas com fee no GP |
| Modelo do projeto | SR col. P ("Inside Sales", "Marketplace", "E-commerce") |
| GrowthPack Atualizado | `paid_traffic_growthpack_updated_link` |

**Breakeven da competência** = `(fee + mídia) / margem / ticket_médio` = receita mensal mínima para MC zerar o custo V4.

### 1.2 GrowthPack (GP)

Baixar como `.xlsx`. Inspecionar as abas:

- **`6.0 Acompanhamento Mensal`** — linha a linha: fee, mídia, sessões/visitas, pedidos, vendas, faturamento
- **`Bd Google Analytics Events`** (e-commerce) — funil completo por mês
- Contexto do modelo (col. P SR): define quais linhas do GP usar

Nunca inventar fee/mídia/margem — sempre do Flow + confirmação no gate.

---

## 2. Arquitetura de Colunas (universal)

| Col | Nome | Conteúdo | Cor |
|-----|------|----------|-----|
| **A** | Rótulos | Nomes das métricas | — |
| **B** | Acumulado | Todo o período do LT (real) | branco |
| **C** | Funil último mês | Dados reais do último mês fechado do GP | sem amarelo |
| **D** | Alvo breakeven | Funil inverso: volumes mínimos para zerar competência | sem amarelo |
| **E** | Mediana 3M | Ponto de partida — mediana dos 3 últimos meses fechados | taxas=amarelo, volumes/financeiros=branco |
| **F** | Total projetado | Soma acumulada das projeções | branco |
| **G** | Spacer | — | — |
| **H+** | M1, M2… | Projeções mensais (taxas editáveis=amarelo) | taxas=amarelo |

**Col E é a origem das projeções.** M1 = col E. Pessimista/Realista/Otimista ajustam taxas de conversão e investimento de mídia a partir desse ponto.

---

## 3. Col C — Funil do Último Mês Real

- Dados reais do último mês fechado no GP (mesmo que vendas = 0, como Mai/26 Alumtech)
- **Sem amarelo** em nenhuma célula
- Header: `"Funil {prev_month_label}\n(último mês GP)"`
- Fonte: campo `previous_month_funnel` do config

### Por modelo

| Modelo | Etapas |
|--------|--------|
| IS | Sessões → VIs → Add-cart → View-cart → Checkout → Vendas |
| E-commerce | Sessões → View-item → Add-to-cart → View-cart → Checkout → Shipping → Payment → Pedidos → Vendas |
| Marketplace | Impressões → Cliques → Visitas (leads) → Compras |

---

## 4. Col D — Alvo Breakeven (Funil Inverso)

**Lógica:** Dado o breakeven da competência → quantas vendas são necessárias → calcular volumes de cada etapa de funil de trás pra frente usando as **mesmas taxas da mediana (col E)**.

```
comp_sales = (fee + mídia) / margem / ticket_médio
↓ (÷ order_sale)  → pedidos
↓ (÷ payment_order) → add_payment_info
↓ (÷ shipping_payment) → add_shipping_info
↓ (÷ checkout_shipping) → begin_checkout
↓ (÷ viewcart_checkout) → view_cart
↓ (÷ add_view_cart) → add_to_cart
↓ (÷ view_add) → view_item
↓ (÷ session_view) → sessões
```

- Taxas = **idênticas à mediana** (col E) — mesmas taxas históricas
- Volumes = **diferentes** — muito menores que col E (são o mínimo necessário)
- **Sem amarelo** nas taxas (formula_percent, não input_percent)
- Row 37 = faturamento da competência; row 38 = 0

---

## 5. Col E — Mediana 3M (Ponto de Partida)

### Quais meses entram

- Últimos **3 meses fechados** antes da referência
- Exemplo: referência Jun/26 → baseline = Mar/26 · Abr/26 · Mai/26

### O que é amarelo

- **Apenas taxas de conversão** (input_percent) — editável pelo usuário/gerente
- Financeiros (fee, mídia, MC, faturamento, TM): branco (formula_currency)
- Volumes do funil: branco (formula_int/formula_number)
- Rows auxiliares (CPV, CPS, resultado líquido, diferença vs. alvo): branco

### Row 38

`= mediana_revenue − competence_revenue`

Positivo → mediana já supera o breakeven. Negativo → ainda estamos abaixo.

### Lógica de mediana (exclusão de zeros)

A função `median_funnel_volume()` **exclui meses com valor = 0**:
- Mai/26 Alumtech tinha 0 compras → excluído da mediana de compras
- Mas Mai/26 com 4.926 impressões > 0 → incluído na mediana de impressões
- Resultado: mediana de impressões = 4.245.518 (mês central = Mar/26), não distorcida pelo outlier

---

## 6. Lógica da Mediana — Detalhes

```python
def median_funnel_volume(series):
    non_zero = [v for v in series if v > 0]
    return statistics.median(non_zero) if non_zero else 0
```

A mediana é robusta: outliers viram mínimo/máximo, o valor central permanece representativo.

---

## 7. Taxas de Conversão — Por Modelo

### Inside Sales

| Taxa | Fórmula |
|------|---------|
| session_view | view_item / sessões |
| view_add | add_cart / view_item |
| add_view_cart | view_cart / add_cart |
| viewcart_checkout | checkout / view_cart |
| checkout_sale | vendas / checkout |

### E-commerce

| Taxa | Fórmula |
|------|---------|
| session_view | view_item / sessões |
| view_add | add_to_cart / view_item |
| add_view_cart | view_cart / add_to_cart |
| viewcart_checkout | begin_checkout / view_cart |
| checkout_shipping | add_shipping / begin_checkout |
| shipping_payment | add_payment / add_shipping |
| payment_order | pedidos / add_payment |
| order_sale | vendas / pedidos |

> **Nota:** `checkout_shipping` pode ser > 1 (ex: DALP = 2.22). O gerador deve aceitar taxas > 1 sem cap.

### Marketplace (3º funil)

| Taxa | Fórmula |
|------|---------|
| CTR | cliques / impressões |
| click_lead | visitas / cliques |
| lead_sale | compras / visitas |

---

## 8. Ticket Médio

- **IS:** ticket = faturamento / vendas (mediana dos 3 meses baseline)
- **E-commerce:** ticket = faturamento / vendas
- **Marketplace:** ticket = faturamento_plataforma / compras_plataforma

Usar mediana do ticket (não média aritmética) para robustez contra outliers.

---

## 9. Acumulado (Col B)

- Todo o período do LT (desde o primeiro mês com fee até o último mês fechado)
- Fonte: `source_months` no config — soma acumulada de fee, mídia, faturamento, MC
- Resultado líquido acumulado (row 29 ou equivalente) = `Σ(faturamento × margem) - Σ(fee + mídia)`

---

## 10. Projeções (Col H+)

- M1 = cópia da col E (mediana) com taxas editáveis
- Cada cenário (Pessimista/Realista/Otimista) define:
  - Investimento de mídia por mês
  - Faturamento-alvo por mês (opcional — pode ser calculado)
  - Taxas de conversão (séries progressivas de melhoria)
- Ticket médio pode ser fixo ou crescente por cenário
- `extend_numeric_series()` interpola os arrays de taxas para cobrir todos os meses projetados

---

## 11. Regras de Cor (resumo)

| Tipo | Formato | Quando usar |
|------|---------|-------------|
| `input_percent` | amarelo, % | Taxa de conversão editável (col E e H+) |
| `formula_percent` | branco, % | Taxa calculada ou não editável (col C, D) |
| `input_currency` | amarelo, R$ | Campo financeiro editável |
| `formula_currency` | branco, R$ | Campo financeiro calculado (col C, D, E) |
| `formula_number` | branco, inteiro | Volume do funil (qualquer col) |

---

## 12. Bugs Conhecidos e Corrigidos

### Builder `reference_date=None`

**Arquivo:** `src/integrations/build_growthpack_inside_sales_config.py`

Condições `and reference_date:` falhavam silenciosamente quando `--reference-date` não era passado (None é falsy). Resultado: override do mês anterior não executava → config com dados errados.

**Fix:** usar `ref = reference_date or date.today()` (já existia na linha ~995) nas condições downstream:
```python
# Antes (errado)
if profile.get("exclude_reference_month") and reference_date:

# Depois (correto)
if profile.get("exclude_reference_month"):
    _last_closed_dt = date(ref.year, ref.month, 1) - timedelta(days=1)
```

---

## 13. Pipeline Completo por Execução

```
1. Ler SR (cockpit/Flow): fee, mídia, margem, modelo, GP link
2. Confirmar no gate: margem, fee, mídia, LT
3. Baixar GP como .xlsx
4. Inspecionar GP: identificar linhas/colunas de cada métrica
5. Rodar builder: build_growthpack_inside_sales_config.py (IS/Marketplace)
   ou construir config manualmente (E-commerce)
6. Verificar config.json:
   - previous_month_label e previous_month_funnel (Col C)
   - baseline_funnel_volumes e baseline_funnel_rates (Col E)
   - projection_baseline_labels (3 meses)
   - source_months com Jun/xx atualizado
   - margin, monthly_fee, monthly_media corretos
7. Gerar planilha: generate_breakeven.py --config ... --output ...
8. Upload Google Drive → atualizar status.md com link
```

---

## 14. Referências

- Alumtech (Marketplace): `projects/08-alumtech-comercio-ltda/`
- DALP (E-commerce): `projects/09-dalpack-comercio-eletronico-ltda-.../`
- Gerador: `vendor/autobreakeven/breakeven-projetos/scripts/generate_breakeven.py`
- Builder IS/Marketplace: `src/integrations/build_growthpack_inside_sales_config.py`
