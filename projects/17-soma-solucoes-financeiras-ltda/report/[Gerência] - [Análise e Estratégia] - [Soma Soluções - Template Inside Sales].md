# [Gerência] - [Análise e Estratégia] - [SOMA SOLUCOES FINANCEIRAS LTDA]

## Contexto do projeto

| Campo | Valor |
| ----- | ----- |
| Cliente | SOMA SOLUCOES FINANCEIRAS LTDA |
| Produto ativo | Executar |
| Modelo | Inside Sales |
| Fase atual | Breakeven inside sales nativo no template da skill |
| Maior risco | Projeto ainda não atingiu breakeven histórico no recorte Jan/2026-Jun/2026. |
| Premissa financeira | Margem de contribuição de 15,00% |

## Premissas financeiras

| Item | Valor |
| ----- | -----: |
| Fee mensal | R$ 7.200,00 |
| Mídia mensal | R$ 30.000,00 |
| Margem de contribuição | 15,00% |
| Faturamento para breakevar uma competência | R$ 248.000,00 |
| Resultado líquido acumulado | **-R$ 124.428,52** |

## Cenário atual acumulado

Fonte: meses válidos do Growth Pack, período 2026-01 a 2026-06.

| Item | Valor |
| ----- | -----: |
| Fee acumulado | R$ 43.200,00 |
| Investimento acumulado | R$ 183.000,00 |
| Custo total acumulado | R$ 226.200,00 |
| Faturamento acumulado | R$ 678.476,53 |
| Resultado MC acumulado | R$ 101.771,48 |
| Resultado líquido acumulado | **-R$ 124.428,52** |
| Ticket médio | R$ 2.081,22 |
| Receita futura necessária em 7 meses | R$ 2.565.523,47 |

## Funil atual + bench interno

Período atual considerado: 2026-06 fechado.

| Etapa | Taxa atual | Bench interno |
| ----- | -----: | -----: |
| Sessão → View item | 2,14% | 1,88% |
| View item → Add to cart | 14,20% | 14,78% |
| Add to cart → View cart | 20,51% | 20,55% |
| View cart → Begin checkout | 89,17% | 85,67% |
| Begin checkout → Add shipping info | 100,00% | 100,00% |
| Add shipping info → Add payment info | 18,69% | 15,93% |
| Add payment info → Purchase | 100,00% | 100,00% |
| Sessão → Purchase | 0,01% | 0,01% |

O bench corresponde à mediana dos 6 meses de LT. Taxas mensais acima de 100,00% são limitadas a 100,00% antes do cálculo.

## Qualidade do tracking

- Validar taxas acima de 100,00% e eventos não sequenciais.
- Não classificar o dado como duplicado sem verificar data + evento e implementação.
- Registrar aqui somente evidências confirmadas no Growth Pack, GA4 ou GTM.

## Diagnóstico das alavancas

- O funil usado é o funil real do Growth Pack: impressões, cliques, leads, MQLs, SQLs, vendas e faturamento.
- A estrutura visual/financeira segue o modelo da skill de e-commerce; apenas as etapas do funil foram substituídas.

## Cenários de breakeven

| Cenário | Receita 7M | Mídia 7M | Saldo final | Breakeven acumulado |
| ----- | -----: | -----: | -----: | ----- |
| Pessimista | R$ 555.018,84 | R$ 210.000,00 | -R$ 301.575,69 | Não breakeva |
| Realista | R$ 705.132,09 | R$ 210.000,00 | -R$ 279.058,71 | Não breakeva |
| Otimista | R$ 894.606,62 | R$ 210.000,00 | -R$ 250.637,53 | Não breakeva |

## Evolução mês a mês

### Pessimista

| Mês | Mídia | Faturamento | Resultado do mês | Resultado acumulado |
| ----- | -----: | -----: | -----: | -----: |
| Mês 1 | R$ 30.000,00 | R$ 70.270,72 | -R$ 26.659,39 | -R$ 151.087,91 |
| Mês 2 | R$ 30.000,00 | R$ 73.081,55 | -R$ 26.237,77 | -R$ 177.325,68 |
| Mês 3 | R$ 30.000,00 | R$ 76.004,81 | -R$ 25.799,28 | -R$ 203.124,96 |
| Mês 4 | R$ 30.000,00 | R$ 79.045,00 | -R$ 25.343,25 | -R$ 228.468,21 |
| Mês 5 | R$ 30.000,00 | R$ 82.206,80 | -R$ 24.868,98 | -R$ 253.337,19 |
| Mês 6 | R$ 30.000,00 | R$ 85.495,08 | -R$ 24.375,74 | -R$ 277.712,93 |
| Mês 7 | R$ 30.000,00 | R$ 88.914,88 | -R$ 23.862,77 | -R$ 301.575,69 |

### Realista

| Mês | Mídia | Faturamento | Resultado do mês | Resultado acumulado |
| ----- | -----: | -----: | -----: | -----: |
| Mês 1 | R$ 30.000,00 | R$ 74.324,80 | -R$ 26.051,28 | -R$ 150.479,80 |
| Mês 2 | R$ 30.000,00 | R$ 81.757,28 | -R$ 24.936,41 | -R$ 175.416,21 |
| Mês 3 | R$ 30.000,00 | R$ 89.933,01 | -R$ 23.710,05 | -R$ 199.126,26 |
| Mês 4 | R$ 30.000,00 | R$ 98.926,31 | -R$ 22.361,05 | -R$ 221.487,31 |
| Mês 5 | R$ 30.000,00 | R$ 108.818,94 | -R$ 20.877,16 | -R$ 242.364,47 |
| Mês 6 | R$ 30.000,00 | R$ 119.700,83 | -R$ 19.244,88 | -R$ 261.609,35 |
| Mês 7 | R$ 30.000,00 | R$ 131.670,92 | -R$ 17.449,36 | -R$ 279.058,71 |

### Otimista

| Mês | Mídia | Faturamento | Resultado do mês | Resultado acumulado |
| ----- | -----: | -----: | -----: | -----: |
| Mês 1 | R$ 30.000,00 | R$ 78.378,88 | -R$ 25.443,17 | -R$ 149.871,69 |
| Mês 2 | R$ 30.000,00 | R$ 90.919,50 | -R$ 23.562,08 | -R$ 173.433,76 |
| Mês 3 | R$ 30.000,00 | R$ 105.466,62 | -R$ 21.380,01 | -R$ 194.813,77 |
| Mês 4 | R$ 30.000,00 | R$ 122.341,28 | -R$ 18.848,81 | -R$ 213.662,58 |
| Mês 5 | R$ 30.000,00 | R$ 141.915,89 | -R$ 15.912,62 | -R$ 229.575,20 |
| Mês 6 | R$ 30.000,00 | R$ 164.622,43 | -R$ 12.506,64 | -R$ 242.081,83 |
| Mês 7 | R$ 30.000,00 | R$ 190.962,02 | -R$ 8.555,70 | -R$ 250.637,53 |

## Funil inverso

O funil para zerar somente a competência parte de R$ 248.000,00 de faturamento. Os funis completos, mês a mês, ficam na planilha gerada.

## 5W1H

| O quê | Por quê | Onde | Quando | Quem | Como | Indicador |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| Validar com gestão se o horizonte deve ser expandido além das 7 colunas do template | [CAUSA] | [LOCAL] | [PRAZO] | [RESPONSÁVEL] | [MÉTODO] | [KPI] |
| Acompanhar evolução de SQL para vendas e faturamento por venda | [CAUSA] | [LOCAL] | [PRAZO] | [RESPONSÁVEL] | [MÉTODO] | [KPI] |
