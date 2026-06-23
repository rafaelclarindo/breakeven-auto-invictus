# Mapeamento do Growth Pack

## Sumário

1. Inspeção
2. Gate de alinhamento
3. Dados financeiros
4. Dados de funil
5. Tratamento de inconsistências

## 1. Inspeção

Executar:

```bash
python3 scripts/inspect_growthpack.py caminho/growthpack.xlsx --rows 80 --output /tmp/growthpack.json
```

Buscar abas com nomes semelhantes a:

- `Acompanhamento Mensal`
- `bd Analytics`
- `Bd Google Analytics Events`
- `Meta Ads`
- `Google Ads`
- `Dashboard`

O nome e a posição variam por projeto. Não assumir que a Dalpack é o padrão universal.

## 2. Gate de alinhamento

Antes de criar o relatório ou a planilha, apresentar:

- Linha do Fee V4.
- Linha do investimento de mídia.
- Linha do faturamento válido.
- Meses com Fee preenchido.
- Último mês fechado.
- Margem de contribuição.
- Canal ou escopo de faturamento.
- Definição de pedido e venda.

Esperar confirmação quando algum item estiver ambíguo.

## 3. Dados financeiros

Montar `source_months` na ordem:

```json
[
  "Mês",
  5500,
  5000,
  5307,
  112,
  100,
  30112.98
]
```

Campos:

1. Mês
2. Fee
3. Mídia
4. Sessões
5. Pedidos
6. Vendas
7. Faturamento

## 4. Dados de funil

Montar `benchmark_months` para todos os meses do LT:

```json
[
  "Mês",
  5307,
  4223,
  187,
  306,
  223,
  495,
  327,
  105
]
```

Campos:

1. Mês
2. Sessões
3. View item
4. Add to cart
5. View cart
6. Begin checkout
7. Add shipping info
8. Add payment info
9. Purchase

Se uma etapa não existir, não substituí-la silenciosamente. Alinhar se o funil será reduzido ou se outra fonte preencherá o dado.

## 5. Tratamento de inconsistências

- Eventos podem ser maiores que a etapa anterior por repetição ou escopo.
- Verificar se existem duplicatas reais por data, usuário, transação ou evento.
- Registrar como `tracking não sequencial` quando a causa não estiver confirmada.
- Para o bench, limitar taxas mensais a 100%.
- Manter os volumes brutos visíveis na aba `Dados Fonte`.
