# RUNBOOK — Breakeven Inside Sales (modo executor)

> **Objetivo:** este arquivo é **prescritivo**. Uma IA executora (ou humano) deve **seguir os passos na ordem**, sem reinterpretar a metodologia. As decisões de negócio já estão tomadas aqui. Se algo fugir do descrito, **PARE e pergunte ao Rafael** — não improvise.
>
> Escopo: clientes **inside sales** da carteira (funil Impressões→Cliques→Leads→MQL→SQL→Vendas). E-commerce usa outro caminho (não coberto aqui).

---

## 0. Conceito em uma frase

Para cada cliente, montar uma planilha de breakeven que: (a) mostra o **histórico real** do contrato (acumulado), (b) **projeta** o funil mês a mês a partir do **desempenho recente**, e (c) calcula **quando o projeto recupera o déficit** (breakeven), em 3 cenários + Mídia V4.

---

## 0.1 PASSO ZERO — Classificar o cliente (LER os documentos ANTES de tudo)

> **Cada cliente é diferente.** Não existe "config padrão". **Leia o GrowthPack e a linha da Strategy Review do cliente** e responda às 4 perguntas abaixo. As respostas definem o caminho. Se não conseguir responder com os documentos, **PARE e pergunte ao Rafael**.

**Pergunta 1 — É inside sales ou e-commerce?**
- Olhe o funil do GrowthPack. Se for **Impressões → Cliques → Leads → MQL → SQL → Vendas** → **inside sales** (`"project_model": "Inside Sales"` no config; siga este runbook).
- Se for **Sessões → View item → Add cart → Checkout → Payment → Purchase** → **e-commerce** → **NÃO use este runbook**; use o pipeline original da skill (config **sem** `project_model: Inside Sales`). PARE e confirme com o Rafael.

**Pergunta 2 — Tem recorrência?**
- Olhe a **Strategy Review col. L (MRR)**.
- Preenchida (ex.: "12 meses") → **recorrência ON**: faturamento = LTV = `vendas × ticket × meses`; setar `mrr_months` / `tm_recurrence_months` no config.
- Vazia → **recorrência OFF**: faturamento = `vendas × ticket mensal` (sem multiplicador). Não setar `mrr_months` nem `tm_recurrence_months`.
- **Col. H (LT)** é duração do contrato ativo — **nunca** usar como multiplicador de ticket.

**Pergunta 3 — Quantas etapas o funil do GP tem e quais os NOMES?**
- O funil é **exatamente** o do GrowthPack daquele cliente. Pode ter **mais ou menos** etapas que o padrão, e a etapa diferente **não é necessariamente "lead quali"** — pode ter qualquer nome (agendamento, reunião, proposta, visita…). **Mapeie o que está no GP, com o nome que está no GP.** Nunca copiar etapas de outro cliente nem assumir um nome.
- **Padrão (6 etapas):** Impressões → Cliques → Leads → MQL → SQL → Vendas → config sem flag extra.
- **1 etapa de qualificação a mais** entre Leads e MQL (qualquer nome) → variante de 7 etapas: `"funnel_has_lead_quali": true` ativa o slot extra **e** `"extra_stage_label": "<nome do GP>"` define o rótulo (ex.: `"Agendamento"`, `"Reunião"`). Se omitir, o default é "Lead quali". **Todos os rótulos do funil em todas as abas usam esse nome.**
- **Qualquer outra estrutura** (contagem/ordem diferente do acima) → **PARE e peça o mapeamento ao Rafael**; o gerador precisa de ajuste antes.

**Pergunta 4 — Qual o layout do GrowthPack (perfil)?**
- Em que linhas estão impressões/cliques/leads/MQL/SQL/vendas. Perfis existentes: `msys`, `cdsi`, `primeset`.
- Layout novo (não bate com nenhum) → **PARE e peça o mapeamento ao Rafael** (não chutar linhas).

| Resposta | Efeito no config |
|----------|------------------|
| Inside sales | `"project_model": "Inside Sales"` |
| E-commerce | sem `project_model` → outro pipeline (não este runbook) |
| MRR "N meses" (col. L preenchida) | `"mrr_months": N` (+ espelho `tm_recurrence_months`) |
| Sem MRR (col. L vazia) | omitir `mrr_months` e `tm_recurrence_months` |
| LT (col. H) | `"lt_months": N` — contrato ativo, **não** multiplica ticket |
| Etapa de qualificação extra (qualquer nome) | `"funnel_has_lead_quali": true` + `"extra_stage_label": "<nome do GP>"` |
| Perfil GP | `--profile msys\|cdsi\|primeset\|<novo>` |

> A metodologia de projeção (últimos 3M, baseline **mediana** 3M, tetos `max(mediana 3M, baseline)×1,1`, CPS **mediana** 3M, evolução por cenário) é **a mesma** para todo inside sales. O que muda por cliente é: modelo, recorrência, lead quali e perfil do GP — **tudo lido dos documentos**.

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
| **Strategy Review** (sheet `1MrUklD9tulNHsxWmAh3fcUUBlBdY-IHzSUuEPAz32YQ`, aba `Start Strategy Review`) | Fee, Mídia, Margem, Recorrência, link GrowthPack, contexto sazonal | `read_strategy_review_row.py "<nome>"` |
| **Flow Cockpit** | Fee, mídia prevista, margem, link GrowthPack Atualizado | manifest (já roda) |
| **GrowthPack (.xlsx)** | **Funil mês a mês** (impressões→…→vendas), faturamento, investimento | baixar + inspecionar |

### 2.1 Colunas da Strategy Review (CONFERIR O CABEÇALHO — já mudaram antes)

Layout atual (conferido 2026-06-24). **Antes de ler, abra a linha 1 e confirme que os títulos batem.** Se mudaram, ajuste `read_strategy_review_row.py`.

| Col | Conteúdo | Uso |
|-----|----------|-----|
| B | Projeto | match do cliente |
| H | LT | referência (não trunca histórico) |
| I | Fee | premissa |
| J | Mídia | premissa |
| K | Margem de contribuição | premissa |
| L | **MRR** | ativa LTV só se preenchida (ex.: "12 meses") |
| H | **LT** | life time contrato ativo — não multiplica ticket |
| M | Link Break-even (Antigo) | referência |
| N | **Link do GrowthPack** | baixar o GP |
| O | Retrospectiva (By AI) | contexto |
| P | **Contexto do projeto (Datas sazonais)** | texto estratégico/sazonal |

---

## 3. Passo a passo (PowerShell, na pasta `projects/breakeven-auto`)

```powershell
# 3.1 Manifest da carteira (ordem + dados Flow) — uma vez por lote
python src/integrations/build_strategy_review_manifest.py

# 3.2 Criar pasta do projeto
python src/integrations/prepare_strategy_review_projects.py

# 3.3 Growth Pack — leitura **online** (padrão; não grava `source/growthpack.xlsx`)
#     O builder lê direto do link no manifest via Sheets API (ou Drive export em memória).
#     Fallback local: `--gp-source local` se existir `source/growthpack.xlsx`.
#     Download em disco (opcional / legado):
# python src/integrations/download_growthpacks.py --orders <N>

# 3.4 Ler o contexto da Strategy Review (fee, mídia, margem, recorrência, sazonal)
python src/integrations/read_strategy_review_row.py "<nome do projeto>"

# 3.5 GATE — confirmar fee/mídia/margem com o Rafael. NUNCA inventar números.
#     Registrar em projects/<slug>/gate.md.

# 3.6 Gerar o config a partir do GrowthPack (online por padrão)
#     Perfil = layout do GP do cliente (msys / cdsi / primeset / novo).
#     --gp-source online | local | auto  (default: online)
python src/integrations/build_growthpack_inside_sales_config.py `
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

> **`<perfil>` (layout do GP):** define em que linhas do GP está o funil. Hoje existem `msys`, `cdsi`, `primeset`. **GP novo com layout diferente → PARE e peça o mapeamento ao Rafael** (não chutar linhas).

---

## 4. Regras de cálculo (NÃO ALTERAR — já decididas)

### 4.1 Funil
- Use **exatamente** o funil do GrowthPack do cliente. **Nunca** inventar etapas (sem shipping/payment/pedido de e-commerce no inside sales).

### 4.2 Janela de dados — projeção vs histórico (REGRA-CHAVE)
- **Projeção** (baseline M1 + tetos do funil) = **ÚLTIMOS 3 MESES** fechados do GP.
- **Histórico** (acumulado / "Feito até o momento" / bench / Dados Fonte) = **TODO o contrato** (todos os meses válidos do GP). Não truncar pelo LT.

### 4.3 Baseline M1 (ponto de partida da projeção)
- Taxa de cada etapa no Mês 1 = **mediana dos últimos 3 meses** (não média — a média é sensível a outliers como um mês atípico ou Black Friday; a mediana produz o ponto de partida mais representativo do nível recente da operação).

### 4.4 Tetos de saturação (Premissas C28:C32)
- Cada taxa cresce mês a mês mas **satura** num teto por etapa.
- **Teto = `max(mediana dos últimos 3 meses, baseline M1) × 1,10`** (cap 95%).
  - Mediana, **não** melhor mês (evita outlier tipo Black Friday).
  - `max(…, baseline)` garante que o teto não fique abaixo do ponto de partida.
- Calculado automaticamente por `stage_ceilings_from_history`. Editável no Sheets (Premissas C28:C32).

### 4.5 Evolução mensal por cenário (Premissas B20:D24, % composto/mês por etapa)
- Default por etapa (Imp→Clique / Clique→Lead / Lead→MQL / MQL→SQL / SQL→Venda):
  - **Pessimista** 3% / 2% / 1% / 1% / 0,5%
  - **Realista** 5% / 3% / 2% / 2% / 1%
  - **Otimista** 7% / 5% / 3% / 3% / 2%
- Fórmula M2+: `MIN(teto_etapa; taxa_anterior × (1+avanço))`.
- **Realista = cenário mínimo.** Mídia V4 usa avanço Realista (coluna C).

### 4.6 MRR / LTV
- Recorrência **somente** se a SR **col. L (MRR)** estiver preenchida (ex.: "12 meses") → **LTV = faturamento mensal × meses**.
- **Col. H (LT)** = duração do contrato ativo — **nunca** multiplicar ticket pelo LT.
- Faturamento do funil nas projeções (com MRR) = `vendas × ticket mensal × meses` (`=Col32*Col7*12`).
- Sem MRR (col. L vazia) → faturamento = vendas × ticket mensal (sem multiplicador).

### 4.7 Mídia
- Cenários P/R/O: **mídia Flow fixa** (valor da SR/Flow, ex.: R$ 34.500/mês).
- Aba **Mídia V4**: rampa linear do investimento (último mês GP → Flow) + funil Realista.

### 4.8 CPS / impressões

**Valor do CPS de projeção (regra crítica):**
- CPS de projeção = **mediana dos últimos 3 meses** do GP (mesma janela do baseline e dos tetos). **Não** usar CPS acumulado (todo o contrato) nem CPS médio — o acumulado é inflado por meses antigos mais caros e faz as impressões ficarem subdimensionadas → projeto nunca breakevar.
- Builder: `projection_cps = median(baseline_cps_samples)` em `stage_ceilings_from_history`. Emitido no config como `gp_cps_projection`.
- Exemplo: MSYS CPS acumulado R$0,054 × 637k impressões → ~25 vendas → nunca breakevava; CPS mediana 3M R$0,029 × 1,196M impressões → ~46 vendas → Realista Abr/28.

**Evitar referência circular (#REF):**
- Impressões projetadas = `mídia ÷ CPS` com **CPS fixo na primeira coluna de projeção (`$G$34`)** (NÃO derivar CPS de mídia÷impressões na mesma coluna — gera referência circular que quebra no Google Sheets).
- O valor de `$G$34` é editável — permite testar cenários alternativos de CPS sem quebrar fórmulas.

### 4.9 Cor do status (EM RECUPERAÇÃO vs breakeven atingido)

- A linha 13 de cada cenário exibe o status: `"EM RECUPERAÇÃO"` ou `"BREAKEVEN ATINGIDO"` (texto via fórmula).
- A **cor deve ser condicional** (seguir o resultado acumulado, linha 11, ao vivo) — **nunca estática** (valor de cache da geração).
  - Resultado acumulado **< 0** → cor **vermelho** (ainda em recuperação).
  - Resultado acumulado **≥ 0** → cor **verde** (breakeven atingido).
- Implementado com `conditional_format` na linha 13 (projeção + Total) seguindo `linha 11` em `generate_breakeven.py`.
- **Regra de ouro:** se a linha 13 está verde, a linha 11 DEVE ser ≥ 0 no mesmo mês. Se não, há bug de cor estática — regenerar.

---

## 5. O que cada aba faz (objetivo)

| Aba | Objetivo |
|-----|----------|
| **Resumo Executivo** | Visão de 1 página: resultado atual, breakeven mensal, cenário atual × mínimo, gráfico de evolução, comparativo dos 4 cenários (Receita 54M, Saldo, mês de breakeven). |
| **Breakeven 7M** | Projeção detalhada do **cenário mínimo (Realista)**: custos, funil, financeiro e resultado acumulado mês a mês. Col. B = feito; col. C = total projetado; col. E+ = meses. |
| **Pessimista / Realista / Otimista** | Um cenário cada. Colunas: **B** = acumulado do contrato; **C** = baseline mediana 3M (`baseline_funnel_volumes`) ou funil mês anterior GP; **D** = alvo breakeven (meta R$ + funil = C); **E** = total projetado; **G+** = projeção mês a mês (M1 = C; M2+ taxas compostas). Realista = base. |
| **Mídia V4** | Igual aos cenários, mas com **rampa de mídia** (investimento crescente) + funil Realista. |
| **Funil Completo** | Funil do **último mês fechado** vs **bench interno** (mediana do contrato) por etapa. Diagnóstico. |
| **Premissas** | **Painel de controle editável.** Fee/mídia/margem, curva mensal, e a tabela A18:D32: evolução %/mês por cenário (B20:D24), baseline M1 (B28:B32), **tetos por etapa (C28:C32)**. Mudar aqui recalcula tudo. |
| **Dados Fonte** | Histórico bruto do GP (mês a mês) que alimenta o bench e o acumulado. |

### 5.1 Significado das colunas B/C/D/E nos cenários
- **B — Atual acumulado:** soma real do contrato (caixa). Fee × meses, mídia somada, faturamento de caixa, déficit acumulado real.
- **C — Baseline mediana 3M** (quando config tem `baseline_funnel_volumes`): volumes medianos Fev·Mar·Abr (ou janela do builder); taxas = Premissas B28:B32; faturamento = vendas baseline × ticket. Sem baseline: funil real do mês anterior GP.
- **D — Meta breakeven (vendas necessárias):** quantas vendas **precisariam** fechar o mês (`breakeven competência ÷ ticket`). **Não é realizado** — pode ser maior que qualquer mês histórico (ex.: 7 vendas meta vs máx. 5 realizadas). Status "ZERA A COMPETÊNCIA".
- **G+ — Projeção calendário (Jul/26…):** funil forward — **não** confundir com o mesmo mês do ano anterior (Jul/25 real ≠ Jul/26 projetado).
- **E — Total projetado:** soma dos 54 meses de projeção.

---

## 6. Checklist de validação (rodar SEMPRE antes de publicar)

1. `validate_breakeven_xlsx.py` imprime **"OK — no errors"**.
2. **Sem `#REF!` / `#DIV/0!`** — abrir no Google Sheets e checar visualmente (recarregar/F5).
3. **Coluna D (meta breakeven)** — vendas = meta (`breakeven ÷ ticket`), **não** histórico. Se o número parecer “venda que nunca fizemos”, checar: (a) é meta legítima? (b) ticket GP correto? (c) não confundir com col. G+ projetada.
4. **Tetos (Premissas C28:C32)** = `max(mediana 3M, baseline) × 1,1` — números na faixa do histórico recente do cliente, não chutes.
5. **Cenários** partem do mesmo M1 e saturam num teto plausível (poucas × o atual, não milhares/milhão).
6. **Mês de breakeven** ordenado: Otimista ≤ Realista ≤ Pessimista.
7. **Resumo** comparativo: cenário mínimo = Realista (mesma Receita 54M e Saldo).
8. **CPS de projeção** (`Premissas G34`) compatível com o histórico recente — verificar se `gp_cps_projection` do config é a mediana dos 3M (não o CPS acumulado).
9. **Cor do status** (linha 13): meses em recuperação = **vermelho**; mês em que linha 11 ≥ 0 = **verde**. Se algum mês mostrar "EM RECUPERAÇÃO" em verde → há bug de cor estática, regenerar.

---

## 7. Erros conhecidos e como evitar (lições já pagas)

| Sintoma | Causa | Prevenção |
|---------|-------|-----------|
| `#REF!` da coluna H em diante nos cenários | Taxa M2+ referenciava a última coluna (`BG`) em vez da anterior — dependência circular | Já corrigido (`previous_col` recalculado por coluna). Se voltar, checar o loop das taxas. |
| Vendas absurdas (milhares/milhão) na projeção | Taxas compunham sem teto por 54 meses | Tetos por etapa (saturação) — §4.4 |
| Coluna D com vendas ~12× infladas (ex.: 301) | Dividia pelo ticket mensal ignorando a recorrência | `÷ (ticket × meses)` — §4.6 |
| `#REF!` circular CPS | Impressões = mídia/CPS **e** CPS = mídia/impressões | CPS fixo `$G$34` (editável) — §4.8 |
| **Projeto nunca breakevar / perde todo mês** | CPS de projeção = **acumulado** (inflado por meses antigos) → impressões subdimensionadas → poucas vendas | CPS projeção = **mediana dos últimos 3M** (`gp_cps_projection`) — §4.8 |
| **"EM RECUPERAÇÃO" aparece em verde** | Cor da linha 13 era **estática** (gravada na geração) enquanto o texto é fórmula (recalcula) | `conditional_format` na linha 13 seguindo resultado acumulado (linha 11) — §4.9 |
| Funil com etapa errada / inventada | Copiar funil de outro cliente | Usar só o funil do GP daquele cliente — §4.1 |
| Colunas da SR trocadas | Layout da Strategy Review mudou | Conferir cabeçalho — §2.1 |
| Baseline M1 acima do nível recente real | Baseline = **média** dos 3M inflada por outlier | Baseline = **mediana** dos últimos 3M — §4.3 |
| Tetos = melhor mês histórico (ex.: Black Friday) | Usar `max(último mês)` em vez de mediana | Teto = `max(mediana 3M, baseline) × 1,1` — §4.4 |
| **“Fizemos 7 vendas em julho” (nunca aconteceu)** | Col. D ou Jul/26+ lidos como **realizado** | Col. D = **meta** (`breakeven÷ticket`); G+ = **projeção**; histórico só col. B/C — `_context/decisions.md` §2026-06-22 vendas meta |
| **Jul/26 abre com vendas acima do melhor mês histórico** | Projeção partia de `Flow÷CPI` × taxas (volume inflado) | M1 = **medianas de quantidade + taxas** 3M; impressões ancoram `$G$16`; M2+ só taxas compostas — `_context/decisions.md` §2026-06-22 projeção M1 |

> **Nota sobre valores em cache:** o `.xlsx` guarda valores "congelados" que podem ficar levemente defasados das fórmulas (ex.: SQLs na coluna D). O **Google Sheets recalcula ao abrir** — as fórmulas são a fonte da verdade. A validação confere fórmulas e relações.

---

## 8. Quando PARAR e perguntar ao Rafael

- GP com layout novo (não bate com `msys`/`cdsi`/`primeset`).
- Fee/mídia/margem divergentes entre Flow e GP.
- Cliente sem 3 meses de funil fechado (baseline insuficiente).
- Qualquer número que destoe da realidade do cliente após a validação.
- Pedido de mudar a metodologia (tetos, recorrência, janela 3M) — isso é decisão de negócio.

---

## 9. Referências

- Metodologia e decisões: `_context/decisions.md`
- Playbook detalhado: `docs/inside-sales-breakeven.md`
- Status da carteira: `_context/status.md`
- Caso de referência: `projects/43-msys-vistorias-ltda/` (MSYS)
