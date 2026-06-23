---
name: breakeven-projetos
description: Analisa Growth Packs XLSX de projetos, alinha Fee, mídia, faturamento, margem e funil, calcula cenário atual, breakeven da competência, carry over e bench interno pela mediana dos meses de LT, cria relatório estratégico em Markdown e gera planilha de breakeven com fórmulas, funil completo e cenários Pessimista, Realista e Otimista. Use quando o usuário pedir análise de breakeven, projeção de 7 meses, funil inverso, bench interno, relatório de análise e estratégia, atualização de planilha de breakeven ou reprodução desse método para qualquer cliente.
---

# Breakeven de Projetos

Produzir dois artefatos consistentes a partir do Growth Pack:

1. Relatório `[Gerência] - [Análise e Estratégia] - [Cliente].md`.
2. Planilha `[Cliente] Projeção Breakeven E-commerce Completo.xlsx`.

## Princípios

- Trabalhar com dados, não com análises prontas do Growth Pack.
- Nunca inventar margem, Fee, mídia, faturamento, ticket ou taxas.
- Confirmar escopo e mapeamento quando houver ambiguidade.
- Calcular o LT contando os meses com Fee preenchido.
- Calcular o bench pela mediana de todos os meses do LT.
- Separar breakeven da competência da recuperação do carry over.
- Preservar crescimento gradual e capacidade operacional nos cenários.
- Tratar `assets/exemplo-analise-dalpack.md` e `assets/modelo-breakeven-completo.xlsx` apenas como referências de estrutura.

## Recursos

- Ler `references/mapeamento-growthpack.md` ao abrir um Growth Pack.
- Ler `references/metodologia.md` antes dos cálculos.
- Ler `references/configuracao.md` antes de montar o JSON.
- Ler `references/estrutura-relatorio.md` antes de finalizar o Markdown.
- Ler `references/portabilidade.md` quando o ambiente não for Codex.
- Usar `assets/config-exemplo-dalpack.json` como contrato preenchido.
- Usar `assets/modelo-analise-estrategia.md` como estrutura neutra.
- Usar `assets/modelo-breakeven-completo.xlsx` como referência visual.

## Workflow

### 1. Localizar os insumos

Solicitar ou localizar:

- Growth Pack `.xlsx`.
- `MAPA.md` ou contexto do projeto.
- Margem de contribuição.
- Escopo do faturamento: e-commerce, marketplace, inside sales ou combinação.
- Margens diferentes por canal, quando existirem.
- Limite de mídia.

### 2. Inspecionar o Growth Pack

Executar a partir da pasta da skill:

```bash
python3 scripts/inspect_growthpack.py "/caminho/growthpack.xlsx" \
  --rows 80 \
  --output /tmp/growthpack-inspecao.json
```

Mapear abas, linhas, colunas e meses conforme `references/mapeamento-growthpack.md`.

### 3. Executar o gate de alinhamento

Antes de gerar arquivos, informar ao usuário:

- Linha e aba do Fee.
- Linha e aba da mídia.
- Linha e aba do faturamento.
- Meses válidos e LT.
- Último mês fechado.
- Margem.
- Definição de pedido, purchase e venda.
- Escopo dos canais.

Pedir confirmação apenas para pontos que não possam ser comprovados nos arquivos. Se o usuário já confirmou no mesmo contexto, seguir sem repetir a pergunta.

### 4. Montar a configuração

Copiar `assets/config-exemplo-dalpack.json` para um arquivo de trabalho e substituir todos os dados.

Não deixar valores da Dalpack em outro cliente.

Validar:

```bash
python3 scripts/validate_config.py "/caminho/config.json"
```

Só continuar quando retornar `OK`.

### 5. Calcular e revisar

Aplicar `references/metodologia.md`.

Verificar:

- Resultado atual acumulado.
- Breakeven de uma competência.
- Receita necessária para recuperar o carry over.
- Mediana mensal de cada etapa.
- Conversão final calculada diretamente por mês.
- Curvas graduais dos três cenários.
- Pessimista pode não breakevar.
- Realista deve ser operacionalmente defensável.
- Otimista não pode combinar taxas incompatíveis sem justificativa.

### 6. Gerar o relatório-base

```bash
python3 scripts/generate_report.py \
  --config "/caminho/config.json" \
  --output "/caminho/[Gerência] - [Análise e Estratégia] - [Cliente].md"
```

Enriquecer o relatório com diagnóstico, tracking, alavancas e 5W1H usando apenas evidências disponíveis.

Não finalizar com campos `[PREENCHER]` quando os dados estiverem nos insumos.

### 7. Gerar a planilha

Requer Python 3 e `xlsxwriter`.

```bash
python3 scripts/generate_breakeven.py \
  --config "/caminho/config.json" \
  --output "/caminho/[Cliente] Projeção Breakeven E-commerce Completo.xlsx"
```

A planilha deve conter:

- Resumo Executivo.
- Breakeven 7M.
- Pessimista.
- Realista.
- Otimista.
- Funil Completo.
- Premissas.
- Dados Fonte.

Nas abas **Pessimista**, **Realista** e **Otimista**, manter:

`Atual acumulado / funil atual` → `Breakeven da competência` → `Total projetado` → **meses calendário** (`Jul/26`, `Ago/26`, …).

**Regra dos cabeçalhos mensais (cenários):** usar `projection_month_headers()` em `breakeven_projection.py`.

| Dia da geração | 1ª coluna projetada |
|----------------|---------------------|
| **1–15** do mês | mês **seguinte** ao da geração |
| **16–31** do mês | mês **subsequente** (pula o mês imediato) |

Ex.: geração em **22/jun/2026** → 1ª coluna **Ago/26**; geração em **10/jun/2026** → **Jul/26**.

Opcional na CLI: `--reference-date YYYY-MM-DD` (padrão: hoje).

As abas Breakeven, Premissas e Funil Completo usam a mesma sequência de meses.

### 8. Validar

Obrigatório:

- Confirmar que o `.xlsx` abre.
- Procurar erros `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?` e `#N/A`.
- Conferir as medianas na aba `Dados Fonte`.
- Conferir que o breakeven da competência resulta em zero.
- Conferir o saldo final dos três cenários.
- Renderizar todas as abas e verificar cortes, cabeçalhos e legibilidade.
- Revisar o Markdown em português.
- Confirmar que relatório e planilha usam os mesmos números.

## Saída

Entregar links para o `.md` e o `.xlsx` e resumir:

- Resultado acumulado.
- Breakeven da competência.
- Cenário e mês de breakeven acumulado.
- Limitações de tracking ou premissas ainda abertas.

Quando algo não puder ser validado, declarar a limitação. Não apresentar estimativa como dado confirmado.
