# RUNBOOK — Breakeven E-commerce (modo executor)

> **Objetivo:** este arquivo é **prescritivo**. Uma IA executora (ou humano) deve **seguir os passos na ordem**, sem reinterpretar a metodologia. As decisões de negócio já estão tomadas aqui. Se algo fugir do descrito, **PARE e pergunte ao Rafael** — não improvise.
>
> Escopo: clientes **e-commerce** da carteira (funil Sessões→...→Purchase, tracking GA4 ou plataforma). Inside sales usa `RUNBOOK-executor-inside-sales.md`.

---

## 0. Conceito em uma frase

Para cada cliente, montar uma planilha de breakeven que: (a) mostra o **histórico real** do contrato (acumulado), (b) **projeta** o funil mês a mês a partir do **desempenho recente**, e (c) calcula **quando o projeto recupera o déficit** (breakeven), em 3 cenários + Mídia V4.

> A metodologia é **idêntica** ao inside sales — mediana 3M para tudo na projeção (baseline, tetos, CPS). O que muda é o funil (Sessões/Purchase em vez de Impressões/Vendas) e o CPS (Investimento/Sessões, não Impressões).

---

## 0.1 PASSO ZERO — Classificar o cliente (LER os documentos ANTES de tudo)

> **Cada cliente é diferente.** Não existe "config padrão". **Leia o GrowthPack e a linha da Strategy Review do cliente** e responda às 4 perguntas abaixo. As respostas definem o caminho. Se não conseguir responder com os documentos, **PARE e pergunte ao Rafael**.

**Pergunta 1 — É realmente e-commerce (e não inside sales ou marketplace)?**
- Funil com **Sessões → ... → Purchase/Compra** (GA4 ou plataforma) → **e-commerce** (siga este runbook).
- Funil com **Impressões → Cliques → Leads → MQL → SQL → Vendas** → **inside sales** → use `RUNBOOK-executor-inside-sales.md`. PARE.
- Funil de **marketplace** (tracking de plataforma, sem GA4: visitas → compras plataforma) → modelo híbrido (`alumtech`-style). Verificar `docs/handoff-inside-sales-vs-ecommerce.md` §6. PARE e confirme com Rafael.

**Pergunta 2 — Quantas etapas de funil o GP rastreia (e quais os NOMES)?**
- O funil é **exatamente** o do GP daquele cliente. Mapeie as etapas com os nomes do GP — nunca inventar etapas que não existem no GP.
- **GA4 completo (8 etapas):** Sessões → View item → Add to cart → View cart → Begin checkout → Add shipping → Add payment → Purchase.
- **GA4 simplificado (6 etapas):** Sessões → View item → Add to cart → Begin checkout → (Add shipping/payment) → Purchase.
- **Muito simplificado (3–4 etapas):** Sessões → Add to cart → Checkout → Purchase (ou Sessões → Pedidos → Vendas → Faturamento).
- Etapas do GA4 que **não existem no GP** → taxa = 1,0 internamente (pass-through). **Nunca** expor como "100% de conversão" visível ao usuário — linha fica oculta.
- **Qualquer estrutura radicalmente diferente** (ex.: marketplace sem GA4, ou funil misto IS+GA4) → PARE e confirme com Rafael.

**Pergunta 3 — Tem MRR/LTV? (SR col. L)**
- E-commerce D2C: quase sempre **vazio** → **sem multiplicador de ticket** (`mrr_months` ausente).
- Se preenchida (ex.: produto de assinatura, box mensal) → opt-in LTV igual ao IS: `"mrr_months": N`. Raro.
- **Col. H (LT)** = duração do contrato ativo em meses — **nunca** multiplica ticket. Só informa `lt_months`.

**Pergunta 4 — Qual o layout do GP (perfil)?**
- Perfis e-commerce implementados: `bublu` (All Bling, GP `6.0 Acompanhamento Mensal`, sessões L17, revenue L42).
- Layout novo (linhas diferentes, aba diferente) → **PARE e peça o mapeamento ao Rafael** (não chutar linhas).

| Resposta | Efeito no config |
|----------|------------------|
| E-commerce | `"project_model": "E-commerce D2C"` (ou omitir `Inside Sales`) |
| Inside sales | outro runbook |
| MRR preenchido (raro) | `"mrr_months": N` |
| Sem MRR (default e-commerce) | omitir `mrr_months` |
| LT (col. H) | `"lt_months": N` — só informa duração, não multiplica ticket |
| Perfil GP | `--profile bublu\|<novo>` |

---

## 1. Pré-requisitos (checar antes de começar)

1. Estar em `projects/breakeven-auto`.
2. Saber **a ordem (nº) ou o nome** do cliente na Strategy Review.
3. Dependências instaladas: `.\ops\setup.ps1` (uma vez).
4. Credenciais Google em `../assessor-pessoal/mcp/credentials/google_sheets_token.json`.

---

## 2. Fontes de dado e o que tirar de cada uma

| Fonte | O que extrair | Como |
|-------|---------------|------|
| **Strategy Review** (sheet `1MrUklD9tulNHsxWmAh3fcUUBlBdY-IHzSUuEPAz32YQ`, aba `Start Strategy Review`) | Fee, Mídia, Margem, MRR (se existir), link GrowthPack, contexto sazonal | `read_strategy_review_row.py "<nome>"` |
| **Flow Cockpit** | Fee, mídia prevista, margem, link GrowthPack Atualizado | manifest (já roda) |
| **GrowthPack (.xlsx)** | **Funil mês a mês** (sessões→…→purchase), faturamento, investimento | baixar + inspecionar |

### 2.1 Colunas da Strategy Review (CONFERIR O CABEÇALHO — já mudaram antes)

Layout atual (conferido 2026-06-24). **Antes de ler, abra a linha 1 e confirme que os títulos batem.** Se mudaram, ajuste `read_strategy_review_row.py`.

| Col | Conteúdo | Uso |
|-----|----------|-----|
| B | Projeto | match do cliente |
| H | LT | duração contrato (`lt_months`) — **não** multiplica ticket |
| I | Fee | premissa |
| J | Mídia | premissa |
| K | Margem de contribuição | premissa |
| L | **MRR** | ativa LTV só se preenchida — quase sempre vazia em e-commerce |
| M | Link Break-even (Antigo) | referência |
| N | **Link do GrowthPack** | baixar o GP |
| O | Retrospectiva (By AI) | contexto |
| P | **Contexto do projeto (Datas sazonais)** | texto estratégico/sazonal |

### 2.2 Funil e-commerce (GA4 padrão)

| Etapa GA4 | Chave interna | Label na planilha |
|-----------|---------------|-------------------|
| Sessões | `sessions` | Sessões |
| View item | `view_item` | View item |
| Add to cart | `add_to_cart` | Add to cart |
| View cart | `view_cart` | View cart |
| Begin checkout | `begin_checkout` | Begin checkout |
| Add shipping | `add_shipping_info` | Add shipping |
| Add payment | `add_payment_info` | Add payment |
| Purchase | `purchase` | Purchase |

> Etapas ausentes no GP → taxa `1.0` (pass-through) internamente. O gerador expõe só as etapas reais.

---

## 3. Passo a passo (PowerShell, na pasta `projects/breakeven-auto`)

```powershell
# 3.1 Manifest da carteira (ordem + dados Flow) — uma vez por lote
python src/integrations/build_strategy_review_manifest.py

# 3.2 Criar pasta do projeto
python src/integrations/prepare_strategy_review_projects.py

# 3.3 Growth Pack — leitura online (padrão)
#     O builder lê direto do link no manifest via Sheets API (ou Drive export em memória).
#     Fallback local: --gp-source local se existir source/growthpack.xlsx.

# 3.4 Ler o contexto da Strategy Review (fee, mídia, margem, MRR, sazonal)
python src/integrations/read_strategy_review_row.py "<nome do projeto>"

# 3.5 GATE — confirmar fee/mídia/margem com o Rafael. NUNCA inventar números.
#     Registrar em projects/<slug>/gate.md.

# 3.6 Gerar o config a partir do GrowthPack
#     Perfil = layout do GP do cliente (bublu / <novo>).
python src/integrations/build_growthpack_ecommerce_config.py `
  --project-folder projects/<slug> --profile <perfil> --reference-date <AAAA-MM-DD>

# 3.7 Gerar a planilha
python vendor/autobreakeven/breakeven-projetos/scripts/generate_breakeven.py `
  --config projects/<slug>/config.json `
  --output projects/<slug>/spreadsheet/breakeven.xlsx --reference-date <AAAA-MM-DD>

# 3.8 Validar (DEVE imprimir "OK — no errors")
python projects/<slug>/scripts/validate_breakeven_xlsx.py

# 3.9 Publicar no Google Sheets (pedir OK do Rafael antes; usar --replace-id para atualizar)
python src/integrations/upload_xlsx_to_google_sheet.py `
  projects/<slug>/spreadsheet/breakeven.xlsx `
  --config projects/<slug>/config.json --share-anyone [--replace-id <ID>]
```

> **Nota sobre o builder:** `build_growthpack_ecommerce_config.py` é a generalização de `build_bublu_ecommerce_config.py` com suporte a `--profile`. Perfis implementados: `bublu`, `alumtech` (marketplace). Se o perfil do cliente não existir → **PARE e peça o mapeamento ao Rafael** (não chutar linhas do GP).

---

## 4. Regras de cálculo (NÃO ALTERAR — já decididas)

### 4.1 Funil
- Use **exatamente** o funil do GrowthPack do cliente. **Nunca** inventar etapas (sem MQL/SQL/impressões de inside sales num funil GA4).
- Etapas do GA4 que o GP não rastreia → taxa pass-through (1,0) internamente, **não exibir** no output.

### 4.2 Janela de dados — projeção vs histórico (REGRA-CHAVE)
- **Projeção** (baseline M1 + tetos do funil + CPS) = **ÚLTIMOS 3 MESES** fechados do GP.
- **Histórico** (acumulado / "Feito até o momento" / bench / Dados Fonte) = **TODO o contrato** (todos os meses válidos do GP). Não truncar pelo LT.

### 4.3 Baseline M1 (ponto de partida da projeção)
- Taxa de cada etapa no Mês 1 = **mediana dos últimos 3 meses** (não média — a média é sensível a outliers como campanhas pontuais, sazonalidade, pico de Black Friday).

### 4.4 Tetos de saturação (Premissas C28:C32)
- Cada taxa cresce mês a mês mas **satura** num teto por etapa.
- **Teto = `max(mediana dos últimos 3 meses, baseline M1) × 1,10`** (cap 95%).
  - Mediana, **não** melhor mês (evita ancorar no pico de Black Friday / promoção pontual).
  - `max(…, baseline)` garante que o teto não fique abaixo do ponto de partida.
- Calculado automaticamente por `stage_ceilings_from_history`. Editável no Sheets (Premissas C28:C32).

### 4.5 Evolução mensal por cenário (Premissas B20:D24, % composto/mês por etapa)
- Default por etapa (Sessões→View item / View→Cart / Cart→Checkout / Checkout→Purchase):
  - **Pessimista** 2% / 1% / 1% / 1%
  - **Realista** 4% / 2% / 2% / 1%
  - **Otimista** 6% / 3% / 3% / 2%
- Fórmula M2+: `MIN(teto_etapa; taxa_anterior × (1+avanço))`.
- **Realista = cenário mínimo.** Mídia V4 usa avanço Realista (coluna C).
- Etapas de pass-through (taxa 1,0) não têm entrada de avanço — permanecem em 1,0.

### 4.6 Recorrência / LTV
- E-commerce: **quase sempre OFF** (compra única, D2C).
- Se SR col. L preenchida (ex.: assinatura/box) → LTV = faturamento × meses. Setar `mrr_months`.
- **Sem recorrência (default):** faturamento = compras × ticket médio — sem multiplicador.

### 4.7 Mídia
- Cenários P/R/O: **mídia Flow fixa** (valor da SR/Flow).
- Aba **Mídia V4**: rampa linear do investimento (último mês GP → Flow) + funil Realista.

### 4.8 CPS / sessões (evita #REF circular)

**Valor do CPS de projeção (regra crítica — idêntica ao IS):**
- CPS e-commerce = **Investimento / Sessões** (não impressões — e-commerce usa sessões como topo do funil).
- CPS de projeção = **mediana dos últimos 3 meses** do GP (mesma janela do baseline e dos tetos). **Não** usar CPS acumulado (todo o contrato) nem CPS médio — o acumulado é inflado por meses antigos e subdimensiona sessões → projeto nunca breakevar.
- Builder: `projection_cps = median(baseline_cps_samples)` onde `cps_samples = media_m / sessions_m` dos 3 últimos meses. Emitido no config como `gp_cps_projection`.

**Evitar referência circular (#REF):**
- Sessões projetadas = `investimento ÷ CPS` com **CPS fixo na primeira coluna de projeção (`$G$34`)** (NÃO derivar CPS de investimento÷sessões na mesma coluna — gera referência circular que quebra no Google Sheets).
- O valor de `$G$34` é editável — permite testar cenários de CPS sem quebrar fórmulas.

### 4.9 Cor do status (EM RECUPERAÇÃO vs breakeven atingido)

- A linha 13 de cada cenário exibe o status: `"EM RECUPERAÇÃO"` ou `"BREAKEVEN ATINGIDO"` (texto via fórmula).
- A **cor deve ser condicional** (seguir o resultado acumulado, linha 11, ao vivo) — **nunca estática** (valor de cache da geração).
  - Resultado acumulado **< 0** → cor **vermelho** (ainda em recuperação).
  - Resultado acumulado **≥ 0** → cor **verde** (breakeven atingido).
- Implementado com `conditional_format` na linha 13 seguindo `linha 11`.
- **Regra de ouro:** se a linha 13 está verde, a linha 11 DEVE ser ≥ 0 no mesmo mês. Se não, há bug de cor estática — regenerar.

---

## 5. O que cada aba faz (objetivo)

| Aba | Objetivo |
|-----|----------|
| **Resumo Executivo** | Visão de 1 página: resultado atual, breakeven mensal, cenário atual × mínimo, gráfico de evolução, comparativo dos 4 cenários (Receita 54M, Saldo, mês de breakeven). |
| **Breakeven 7M** | Projeção detalhada do **cenário mínimo (Realista)**: custos, funil, financeiro e resultado acumulado mês a mês. Col. B = feito; col. C = total projetado; col. E+ = meses. |
| **Pessimista / Realista / Otimista** | Um cenário cada. Colunas: **B** = acumulado do contrato; **C** = funil do mês anterior (GP); **D** = breakeven da competência; **E** = total projetado; **G+** = mês a mês. Realista = base. |
| **Mídia V4** | Igual aos cenários, mas com **rampa de mídia** (investimento crescente) + funil Realista. |
| **Funil Completo** | Funil do **último mês fechado** vs **bench interno** (mediana do contrato) por etapa. Diagnóstico. |
| **Premissas** | **Painel de controle editável.** Fee/mídia/margem, curva mensal, e a tabela A18:D32: evolução %/mês por cenário (B20:D24), baseline M1 (B28:B32), **tetos por etapa (C28:C32)**. Mudar aqui recalcula tudo. |
| **Dados Fonte** | Histórico bruto do GP (mês a mês) que alimenta o bench e o acumulado. |

### 5.1 Significado das colunas B/C/D/E nos cenários
- **B — Atual acumulado:** soma real do contrato (caixa). Fee × meses, mídia somada, faturamento de caixa, déficit acumulado real.
- **C — Funil mês anterior (GP):** o funil real do último mês fechado anterior à referência. Faturamento = ticket × purchase desse mês.
- **D — Breakeven da competência:** quantas **compras novas/mês** cobrem o custo mensal. "ZERA A COMPETÊNCIA".
- **E — Total projetado:** soma dos 54 meses de projeção.

---

## 6. Checklist de validação (rodar SEMPRE antes de publicar)

1. `validate_breakeven_xlsx.py` imprime **"OK — no errors"**.
2. **Sem `#REF!` / `#DIV/0!`** — abrir no Google Sheets e checar visualmente (recarregar/F5).
3. **Coluna D (breakeven competência)** com compras plausíveis (`breakeven ÷ ticket médio`). Sem MRR: **não** dividir por meses.
4. **Tetos (Premissas C28:C32)** = `max(mediana 3M, baseline) × 1,1` — números na faixa do histórico recente, não chutes.
5. **Cenários** partem do mesmo M1 e saturam num teto plausível — não milhares de purchase/mês.
6. **Mês de breakeven** ordenado: Otimista ≤ Realista ≤ Pessimista.
7. **Resumo** comparativo: cenário mínimo = Realista (mesma Receita 54M e Saldo).
8. **CPS de projeção** (`Premissas G34`) = mediana dos 3M (não CPS acumulado). Verificar `gp_cps_projection` no config.
9. **Cor do status** (linha 13): meses em recuperação = **vermelho**; mês de breakeven = **verde**. "EM RECUPERAÇÃO" em verde → regenerar.
10. **Funil sem etapas inside sales** (MQL, SQL, Leads, Impressões) no output. Só etapas GA4 / plataforma do cliente.

---

## 7. Erros conhecidos e como evitar (lições já pagas)

| Sintoma | Causa | Prevenção |
|---------|-------|-----------|
| `#REF!` da coluna H em diante | Taxa M2+ com dependência circular (previous_col stale) | `previous_col` recalculado por coluna — se voltar, checar loop das taxas |
| Compras absurdas (milhares/mês) na projeção | Taxas compunham sem teto por 54 meses | Tetos por etapa (saturação) — §4.4 |
| Projeto nunca breakevar / perde todo mês | CPS de projeção = **acumulado** (inflado por meses antigos) | CPS projeção = **mediana dos últimos 3M** — §4.8 |
| `#REF!` circular CPS | Sessões = Investimento/CPS e CPS = Investimento/Sessões na mesma célula | CPS fixo `$G$34` — §4.8 |
| "EM RECUPERAÇÃO" aparece em verde | Cor da linha 13 estática (cache da geração) | `conditional_format` seguindo resultado acumulado (linha 11) — §4.9 |
| Baseline M1 muito alto (acima do recente) | Baseline = **média** inflada por pico (ex.: Black Friday) | Baseline = **mediana** dos últimos 3M — §4.3 |
| Tetos = melhor mês (ex.: campanha de fim de ano) | Usar max histórico em vez de mediana | Teto = `max(mediana 3M, baseline) × 1,1` — §4.4 |
| Colunas da SR trocadas | Layout da Strategy Review mudou | Conferir cabeçalho linha 1 — §2.1 |
| Etapas IS no funil e-commerce (MQL, SQL) | Copiar config de inside sales | Perfil e-commerce próprio — §0.1 |
| Coluna D com compras × 12 (MRR falso) | `mrr_months` ativado sem SR col. L preenchida | MRR só se col. L explícita — §4.6 |

> **Nota sobre valores em cache:** o `.xlsx` guarda valores "congelados". O **Google Sheets recalcula ao abrir** — as fórmulas são a fonte da verdade. A validação confere fórmulas e relações.

---

## 8. Quando PARAR e perguntar ao Rafael

- GP com layout novo (não bate com perfis existentes).
- Fee/mídia/margem divergentes entre Flow e GP.
- Cliente sem 3 meses de funil fechado (baseline insuficiente).
- Funil GA4 com dados inválidos (datetime em células de receita, zeros sistemáticos, tracking quebrado).
- Cliente marketplace (não GA4 puro, não IS puro) — pode precisar de modelo próprio.
- Qualquer número que destoe da realidade do cliente após a validação.
- Pedido de mudar a metodologia (tetos, janela 3M, CPS) — isso é decisão de negócio.

---

## 9. Referências

- Metodologia e decisões: `_context/decisions.md`
- Playbook inside sales: `docs/inside-sales-breakeven.md`
- RUNBOOK inside sales: `docs/RUNBOOK-executor-inside-sales.md`
- Handoff IS vs E-commerce: `docs/handoff-inside-sales-vs-ecommerce.md`
- Status da carteira: `_context/status.md`
- Caso de referência e-commerce: `projects/<ordem>-bublu/` (BUBLU — e-commerce D2C pet)
- Builder legado (Bublu, hardcoded Jun/26): `src/integrations/build_bublu_ecommerce_config.py`
- **Builder genérico (use este):** `src/integrations/build_growthpack_ecommerce_config.py` — perfil `--profile bublu` replica Bublu com mediana 3M + tetos por etapa (mesma metodologia IS)
