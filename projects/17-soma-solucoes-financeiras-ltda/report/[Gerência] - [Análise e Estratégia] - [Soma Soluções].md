# [Gerência] - [Análise e Estratégia] - [SOMA SOLUCOES FINANCEIRAS LTDA]

## Contexto do projeto

| Campo | Valor |
| ----- | ----- |
| Cliente | SOMA SOLUCOES FINANCEIRAS LTDA |
| Produto ativo | Executar |
| Modelo | Inside Sales / geração de demanda |
| Fase atual | Teste Strategy Review / skill Jefferson |
| Maior risco | Divergência entre Growth Pack, Flow e breakeven antigo; funil inside sales adaptado ao contrato e-commerce do gerador. |
| Premissa financeira | Margem de contribuição de 15,00% |

## Premissas financeiras

| Item | Valor |
| ----- | -----: |
| Fee mensal | R$ 7.200,00 |
| Mídia mensal | R$ 30.000,00 |
| Margem de contribuição | 15,00% |
| Faturamento para breakevar uma competência | R$ 248.000,00 |
| Resultado líquido acumulado | **-R$ 150.700,85** |

## Cenário atual acumulado

Fonte: meses válidos do Growth Pack, período Janeiro/2024 a Março/2024.

| Item | Valor |
| ----- | -----: |
| Fee acumulado | R$ 51.000,00 |
| Investimento acumulado | R$ 229.778,00 |
| Custo total acumulado | R$ 280.778,00 |
| Faturamento acumulado | R$ 867.181,00 |
| Resultado MC acumulado | R$ 130.077,15 |
| Resultado líquido acumulado | **-R$ 150.700,85** |
| Ticket médio | R$ 133,25 |
| Receita futura necessária em 7 meses | R$ 2.740.672,33 |

## Funil atual + bench interno

Período atual considerado: Março/2024 fechado.

| Etapa | Taxa atual | Bench interno |
| ----- | -----: | -----: |
| Sessão → View item | 100,00% | 100,00% |
| View item → Add to cart | 3,55% | 3,55% |
| Add to cart → View cart | 44,58% | 44,58% |
| View cart → Begin checkout | 100,00% | 100,00% |
| Begin checkout → Add shipping info | 100,00% | 100,00% |
| Add shipping info → Add payment info | 108,13% | 95,57% |
| Add payment info → Purchase | 100,00% | 100,00% |
| Sessão → Purchase | 1,71% | 1,71% |

O bench corresponde à mediana dos 3 meses de LT. Taxas mensais acima de 100,00% são limitadas a 100,00% antes do cálculo.

## Qualidade do tracking

- Validar taxas acima de 100,00% e eventos não sequenciais.
- Não classificar o dado como duplicado sem verificar data + evento e implementação.
- Registrar aqui somente evidências confirmadas no Growth Pack, GA4 ou GTM.

## Diagnóstico das alavancas

- O Growth Pack traz apenas Janeiro a Março/2024 com Fee V4 preenchido, então o LT usado no acumulado é de 3 meses.
- A competência usa Fee R$ 7.200, mídia R$ 30.000 e margem 15% da Strategy Review/Flow.
- O breakeven antigo da coluna M usa outro contrato financeiro na aba Projeção Break Even: Fee R$ 5.500 e mídia R$ 35.000.
- A aba Tabela Mensal do Growth Pack mostra margem 30%, mas a Strategy Review/Flow e o breakeven antigo usam 15% como margem de projeção.
- Como o projeto é inside sales, as etapas não disponíveis no contrato e-commerce foram mantidas como passagem neutra e documentadas no gate.

## Cenários de breakeven

| Cenário | Receita 7M | Mídia 7M | Saldo final | Breakeven acumulado |
| ----- | -----: | -----: | -----: | ----- |
| Pessimista | R$ 2.002.021,00 | R$ 210.000,00 | -R$ 110.797,70 | Não breakeva |
| Realista | R$ 2.777.089,13 | R$ 210.000,00 | R$ 5.462,52 | Mês 7 |
| Otimista | R$ 3.174.633,30 | R$ 210.000,00 | R$ 65.094,14 | Mês 6 |

## Evolução mês a mês

### Pessimista

| Mês | Mídia | Faturamento | Resultado do mês | Resultado acumulado |
| ----- | -----: | -----: | -----: | -----: |
| Mês 1 | R$ 30.000,00 | R$ 243.102,55 | -R$ 734,62 | -R$ 151.435,47 |
| Mês 2 | R$ 30.000,00 | R$ 257.402,70 | R$ 1.410,40 | -R$ 150.025,06 |
| Mês 3 | R$ 30.000,00 | R$ 271.702,85 | R$ 3.555,43 | -R$ 146.469,64 |
| Mês 4 | R$ 30.000,00 | R$ 286.003,00 | R$ 5.700,45 | -R$ 140.769,18 |
| Mês 5 | R$ 30.000,00 | R$ 300.303,15 | R$ 7.845,47 | -R$ 132.923,71 |
| Mês 6 | R$ 30.000,00 | R$ 314.603,30 | R$ 9.990,49 | -R$ 122.933,22 |
| Mês 7 | R$ 30.000,00 | R$ 328.903,45 | R$ 12.135,52 | -R$ 110.797,70 |

### Realista

| Mês | Mídia | Faturamento | Resultado do mês | Resultado acumulado |
| ----- | -----: | -----: | -----: | -----: |
| Mês 1 | R$ 30.000,00 | R$ 286.003,00 | R$ 5.700,45 | -R$ 145.000,40 |
| Mês 2 | R$ 30.000,00 | R$ 328.903,45 | R$ 12.135,52 | -R$ 132.864,88 |
| Mês 3 | R$ 30.000,00 | R$ 371.803,90 | R$ 18.570,58 | -R$ 114.294,30 |
| Mês 4 | R$ 30.000,00 | R$ 408.984,29 | R$ 24.147,64 | -R$ 90.146,65 |
| Mês 5 | R$ 30.000,00 | R$ 440.444,62 | R$ 28.866,69 | -R$ 61.279,96 |
| Mês 6 | R$ 30.000,00 | R$ 460.464,83 | R$ 31.869,72 | -R$ 29.410,24 |
| Mês 7 | R$ 30.000,00 | R$ 480.485,04 | R$ 34.872,76 | R$ 5.462,52 |

### Otimista

| Mês | Mídia | Faturamento | Resultado do mês | Resultado acumulado |
| ----- | -----: | -----: | -----: | -----: |
| Mês 1 | R$ 30.000,00 | R$ 314.603,30 | R$ 9.990,49 | -R$ 140.710,36 |
| Mês 2 | R$ 30.000,00 | R$ 357.503,75 | R$ 16.425,56 | -R$ 124.284,79 |
| Mês 3 | R$ 30.000,00 | R$ 414.704,35 | R$ 25.005,65 | -R$ 99.279,14 |
| Mês 4 | R$ 30.000,00 | R$ 457.604,80 | R$ 31.440,72 | -R$ 67.838,42 |
| Mês 5 | R$ 30.000,00 | R$ 500.505,25 | R$ 37.875,79 | -R$ 29.962,63 |
| Mês 6 | R$ 30.000,00 | R$ 543.405,70 | R$ 44.310,85 | R$ 14.348,22 |
| Mês 7 | R$ 30.000,00 | R$ 586.306,15 | R$ 50.745,92 | R$ 65.094,14 |

## Funil inverso

O funil para zerar somente a competência parte de R$ 248.000,00 de faturamento. Os funis completos, mês a mês, ficam na planilha gerada.

## 5W1H

| O quê | Por quê | Onde | Quando | Quem | Como | Indicador |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| Confirmar se a margem oficial para Soma deve ser 15% ou 30% | [CAUSA] | [LOCAL] | [PRAZO] | [RESPONSÁVEL] | [MÉTODO] | [KPI] |
| Confirmar se o Fee vigente para breakeven da competência é R$ 7.200 ou o Fee histórico de R$ 17.000 do Growth Pack | [CAUSA] | [LOCAL] | [PRAZO] | [RESPONSÁVEL] | [MÉTODO] | [KPI] |
| Validar com o time se a etapa Add cart do Growth Pack representa leads/cadastros para Soma | [CAUSA] | [LOCAL] | [PRAZO] | [RESPONSÁVEL] | [MÉTODO] | [KPI] |
