# Metodologia de breakeven

## Sumário

1. Recorte temporal
2. Cenário acumulado
3. Bench interno
4. Breakeven da competência
5. Carry over
6. Cenários
7. Funil inverso
8. Regras de qualidade

## 1. Recorte temporal

- Definir o LT como a quantidade de meses com Fee V4 preenchido.
- Considerar Fee, mídia e faturamento somente nesses meses.
- Usar o último mês fechado para o funil atual. Não misturar mês parcial sem sinalização.
- Confirmar com o usuário as linhas e colunas antes de calcular.

## 2. Cenário acumulado

```text
Custo acumulado = Fee acumulado + mídia acumulada
Resultado MC = faturamento acumulado × margem de contribuição
Resultado líquido acumulado = Resultado MC - custo acumulado
```

Quando houver canais com margens diferentes, calcular cada canal separadamente:

```text
Resultado MC = Σ(faturamento do canal × margem do canal)
```

Não aplicar uma margem única sobre inside sales, marketplace e e-commerce quando as margens forem diferentes.

## 3. Bench interno

Usar a mediana de todos os meses do LT, etapa por etapa.

1. Calcular a taxa de cada mês.
2. Limitar a 100% taxas intermediárias superiores a 100%.
3. Ordenar as taxas mensais.
4. Calcular a mediana.

A taxa final `Sessão → Purchase` deve ser calculada diretamente em cada mês e depois ter sua mediana calculada. Não multiplicar as medianas intermediárias para representar a conversão final.

Taxas acima de 100% indicam tracking não sequencial, disparo múltiplo ou diferença de escopo. Não chamar automaticamente de duplicidade.

## 4. Breakeven da competência

Representa o faturamento necessário para pagar apenas o mês atual:

```text
Breakeven da competência = (Fee mensal + mídia mensal) / margem
```

Esse cálculo não recupera o resultado negativo acumulado.

## 5. Carry over

O carry over é o resultado líquido acumulado negativo.

Para recuperar o carry over em sete meses:

```text
Receita futura necessária =
  (ABS(resultado líquido acumulado) + custos futuros) / margem
```

Na planilha, manter três leituras separadas:

- `Atual acumulado / funil atual`
- `Breakeven da competência`
- `Total projetado`, que inclui a recuperação do carry over

## 6. Cenários

### Pessimista

- Parte do desempenho atual.
- Aplica melhorias leves.
- Respeita a verba disponível.
- Pode não breakevar o acumulado.

### Realista

- Aplica evolução gradual e operacionalmente defensável.
- Evita saltos bruscos de faturamento ou conversão.
- Busca breakeven entre os meses 6 e 7 quando possível.

### Otimista

- Aproxima-se das melhores faixas sustentáveis do histórico ou do bench interno.
- Continua respeitando capacidade, verba e limites de tracking.
- Não usa todas as melhores taxas históricas simultaneamente sem justificativa.

## 7. Funil inverso

Partir de faturamento e ticket:

```text
Vendas = faturamento / ticket
Pedidos = vendas / taxa Pedido → Venda
Add payment = pedidos / taxa Add payment → Pedido
Add shipping = Add payment / taxa Shipping → Payment
Begin checkout = Add shipping / taxa Checkout → Shipping
View cart = Begin checkout / taxa View cart → Checkout
Add to cart = View cart / taxa Add cart → View cart
View item = Add to cart / taxa View item → Add cart
Sessões = View item / taxa Sessão → View item
```

Projetar taxas com variação gradual mês a mês. Não repetir todas as taxas de forma idêntica se o cenário pressupõe evolução.

## 8. Regras de qualidade

- Nunca inventar Fee, mídia, margem, faturamento, ticket ou taxas.
- Diferenciar pedido, compra aprovada e venda.
- Documentar fonte, linha, coluna, aba e período.
- Preservar fórmulas na planilha.
- Verificar `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?` e `#N/A`.
- Renderizar todas as abas antes da entrega.
