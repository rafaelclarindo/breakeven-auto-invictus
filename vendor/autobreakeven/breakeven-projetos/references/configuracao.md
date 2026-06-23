# Contrato do arquivo de configuração

O gerador recebe um JSON UTF-8.

Modelo completo: `../assets/config-exemplo-dalpack.json`.

## Campos obrigatórios

| Campo | Descrição |
| ----- | ----- |
| `client` | Nome do cliente |
| `current_period` | Último mês fechado |
| `lt_period` | Intervalo dos meses com Fee |
| `margin` | Margem decimal, por exemplo `0.25` |
| `monthly_fee` | Fee da competência |
| `monthly_media` | Mídia usada no breakeven da competência |
| `source_months` | Dados financeiros dos meses válidos |
| `benchmark_months` | Funil mensal de todo o LT |
| `current_funnel` | Funil do último mês fechado |
| `minimum_scenario` | Curva do cenário mínimo |
| `scenarios` | Pessimista, Realista e Otimista |

## Regras dos cenários

Cada cenário deve conter sete valores para:

- `media`
- `revenue`
- `ticket`
- `session_view`
- `view_cart_share`
- `add_view_cart`
- `viewcart_checkout`
- `checkout_shipping`
- `shipping_payment`
- `payment_order`
- `order_sale`

`view_cart_share` representa `View cart / Sessões`. O gerador deriva `View item → Add to cart` para manter coerência com `session_view` e `add_view_cart`.

## Cenário mínimo

`minimum_scenario.revenue` pode ter:

- sete valores; ou
- seis valores, deixando o sétimo mês fechar automaticamente a receita necessária para recuperar o carry over.

## Dependência

O gerador de `.xlsx` requer:

```bash
python3 -m pip install xlsxwriter
```

O inspetor e o gerador de Markdown usam apenas a biblioteca padrão do Python.
