# [Gerência Invictus] - [Análise e Estratégia] - [Dalpack]

[Dash IA](dashboards/dalpack-redesign.html)

Objetivos dentro de todos os projetos:

**Geração de Demanda Qualificada:** subir campanhas rastreadas com os melhores criativos para o melhor ambiente de conversão, considerando canal, plataforma, posicionamento, campanhas, públicos e criativos.

**Coleta de dados:** coletar e armazenar os dados relevantes para o resultado-alvo.

**Analisar os dados:** avaliar o caminho para o resultado-alvo, mapear quebras, causas e hipóteses.

**Otimizar:** construir planos e priorizar ações que resolvam a causa raiz.

---

## Contexto do projeto

| Campo | Valor |
| ----- | ----- |
| Cliente | Dalpack |
| Produto ativo | Executar |
| Modelo | E-commerce B2B de embalagens, com operação própria na Tray e presença em marketplaces |
| ICP | Gestores e proprietários de PMEs, restaurantes, fast food, delivery e pequenos varejos |
| Fase atual | Estabilização pós-migração da Loja Integrada para Tray |
| Maior risco | Tracking Google/GA4, volume de tráfego pago e quebra no fechamento do checkout |
| Premissa financeira | Margem de contribuição de 15,00% |

## Premissas financeiras

| Item | Valor |
| ----- | -----: |
| Fee V4 mensal | R$ 5.500,00 |
| Mídia inicial | R$ 5.000,00/mês |
| Custo mensal inicial | R$ 10.500,00 |
| Margem de contribuição | 15,00% |
| Faturamento para breakevar 1 mês | R$ 70.000,00 |
| Negativo acumulado atual | -R$ 47.042,73 |

## Cenário atual acumulado

Fonte: aba `6.0 Acompanhamento Mensal` do Growth Pack.

Regras de leitura:

- Fee V4: linha 6.
- Investimento de mídia: linha 9.
- Faturamento: linha 28.
- Período: apenas os meses com Fee V4 preenchido, de novembro/2025 a junho/2026, colunas `AJ:AQ`.

| Item | Valor |
| ----- | -----: |
| Fee V4 acumulado | R$ 44.000,00 |
| Investimento acumulado | R$ 35.163,17 |
| Custo total acumulado | R$ 79.163,17 |
| Faturamento acumulado | R$ 214.136,28 |
| Resultado MC acumulado | R$ 32.120,44 |
| Resultado líquido acumulado | **-R$ 47.042,73** |
| Faturamento necessário para breakevar o acumulado | R$ 527.754,47 |
| Faturamento adicional necessário | R$ 313.618,19 |

## Funil atual + bench interno

Período atual considerado: maio/2026, último mês fechado.

O bench interno corresponde à mediana das taxas mensais dos oito meses de LT com Fee V4, de novembro/2025 a junho/2026. Para cada etapa, as oito taxas foram ordenadas e a mediana foi calculada pela média entre o quarto e o quinto valor. Quando uma taxa mensal excede 100,00%, ela é travada em 100,00% antes do cálculo.

| Etapa | Volume atual | Taxa atual | Bench interno: mediana de 8 meses |
| ----- | -----: | -----: | -----: |
| Sessões | 5.307 | 100,00% | 100,00% |
| View item | 4.223 | 79,57% | 90,96% |
| Add to cart | 187 | 4,43% | 16,01% |
| View cart | 306 | 100,00%* | 61,27% |
| Begin checkout | 223 | 72,88% | 42,21% |
| Add shipping info | 495 | 100,00%* | 98,98% |
| Add payment info | 327 | 66,06% | 68,83% |
| Purchase | 105 | 32,11% | 53,82% |
| **Sessão -> Purchase** | **105** | **1,98%** | **1,84%** |

\* Taxa originalmente acima de 100,00%, limitada conforme regra da projeção.

A mediana de 1,84% para `Sessão -> Purchase` foi calculada diretamente sobre a conversão final de cada mês. Ela não corresponde à multiplicação das medianas individuais das etapas.

### Qualidade do tracking

A base `bd Analytics` apresenta sessões coerentes com `session_start`. A inconsistência está concentrada na base de eventos:

- `add_to_cart` deixou de disparar corretamente em maio;
- `add_shipping_info` passou a disparar excessivamente após a migração para Tray;
- não existem linhas duplicadas por data + evento;
- o padrão indica implementação não sequencial ou disparo múltiplo, não duplicação da base.

O bench revisado substitui o uso isolado do melhor mês por uma referência central dos oito meses de LT. As projeções financeiras e os funis mensais apresentados nas seções seguintes ainda refletem o bench anterior e serão recalculados na próxima etapa.

## Diagnóstico das alavancas

O dashboard gerencial indica que a eficiência unitária não explica sozinha o gap. Conversão e ticket ficaram próximos ou acima do planejado em parte do Q2, enquanto o volume de sessões pagas ficou muito abaixo da meta.

| Alavanca | Situação observada | Impacto gerencial estimado |
| ----- | ----- | -----: |
| Recuperar Google Ads | Tracking quebrado e ROAS zerado em abril | +R$ 9.000,00 |
| Melhorar pagamento -> pedido | 34,25% no funil gerencial | +R$ 12.000,00 |
| Recuperar sessões pagas | 4.763 realizadas de 11.504 planejadas no Q2 | Principal alavanca de volume |
| Recuperar Connect Rate | 55,40% em abril; alvo de 75,00%-80,00% | +R$ 7.000,00 |
| Ativar CRM e recompra | Base aproximada de 1.500 clientes sem régua ativa | +R$ 4.000,00 |
| Melhorar mix e ticket | Ticket próximo de R$ 300,00 | Kits, combos e priorização de PJ |

## Faturamento necessário

Com margem de 15,00%, atingir R$ 70.000,00/mês apenas impede o aumento do déficit. Para recuperar o saldo negativo em sete meses:

`(-R$ 47.042,73 + 7 x R$ 10.500,00) / 15% = R$ 803.618,20`

| Indicador | Valor |
| ----- | -----: |
| Faturamento total necessário em 7 meses | R$ 803.618,20 |
| Média mensal necessária | R$ 114.802,60 |
| Meta operacional recomendada | R$ 115.000,00/mês |

| Faturamento mensal | Resultado líquido/mês | Prazo aproximado para recuperar R$ 47 mil |
| -----: | -----: | -----: |
| R$ 70.000,00 | R$ 0,00 | Não recupera |
| R$ 82.000,00 | R$ 1.800,00 | 26 meses |
| R$ 106.000,00 | R$ 5.400,00 | 9 meses |
| R$ 115.000,00 | R$ 6.750,00 | 7 meses |
| R$ 125.000,00 | R$ 8.250,00 | 6 meses |

## Regra de escala de mídia

A mídia aumenta apenas depois de o projeto breakevar um mês. Cada incremento de R$ 3.000,00 precisa sustentar ROAS superior a 6,67x para gerar contribuição líquida.

| Fase | Mídia mensal | Condição |
| ----- | -----: | ----- |
| Inicial | R$ 5.000,00 | Até o primeiro mês positivo |
| Primeira escala | R$ 8.000,00 | A partir do mês seguinte ao primeiro mês positivo |
| Segunda escala | R$ 11.000,00 | Três meses após o primeiro mês positivo |

Premissas da receita incremental:

| Cenário | ROAS incremental |
| ----- | -----: |
| Realista | 7,00x |
| Otimista | 8,00x |

## Cenários de breakeven

| Cenário | Base usada | Mídia | Faturamento/mês | Resultado líquido/mês | Breakeven acumulado |
| ----- | ----- | -----: | -----: | -----: | ----- |
| Pessimista | Melhora leve, sem recuperação completa de Google e CRM | R$ 5 mil | R$ 35 mil -> R$ 65 mil | -R$ 5.250 -> -R$ 750 | Não breakeva |
| Realista | Google, checkout, Connect Rate e CRM em evolução | R$ 5 mil -> R$ 11 mil | R$ 55 mil -> R$ 202 mil | -R$ 2.250 -> R$ 13.800 | Mês 7 |
| Otimista | Bench interno, tráfego recuperado, CRM e ticket maior | R$ 5 mil -> R$ 11 mil | R$ 65 mil -> R$ 243 mil | -R$ 750 -> R$ 19.950 | Mês 6 |

## Evolução mês a mês

### Realista

| Mês | Mídia | Faturamento | Custo total | Resultado do mês | Resultado acumulado |
| ----- | -----: | -----: | -----: | -----: | -----: |
| Mês 1 | R$ 5.000,00 | R$ 55.000,00 | R$ 10.500,00 | -R$ 2.250,00 | -R$ 49.292,73 |
| Mês 2 | R$ 5.000,00 | R$ 75.000,00 | R$ 10.500,00 | R$ 750,00 | -R$ 48.542,73 |
| Mês 3 | R$ 8.000,00 | R$ 121.000,00 | R$ 13.500,00 | R$ 4.650,00 | -R$ 43.892,73 |
| Mês 4 | R$ 8.000,00 | R$ 146.000,00 | R$ 13.500,00 | R$ 8.400,00 | -R$ 35.492,73 |
| Mês 5 | R$ 11.000,00 | R$ 187.000,00 | R$ 16.500,00 | R$ 11.550,00 | -R$ 23.942,73 |
| Mês 6 | R$ 11.000,00 | R$ 197.000,00 | R$ 16.500,00 | R$ 13.050,00 | -R$ 10.892,73 |
| Mês 7 | R$ 11.000,00 | R$ 202.000,00 | R$ 16.500,00 | R$ 13.800,00 | **R$ 2.907,27** |

### Otimista

| Mês | Mídia | Faturamento | Custo total | Resultado do mês | Resultado acumulado |
| ----- | -----: | -----: | -----: | -----: | -----: |
| Mês 1 | R$ 5.000,00 | R$ 65.000,00 | R$ 10.500,00 | -R$ 750,00 | -R$ 47.792,73 |
| Mês 2 | R$ 5.000,00 | R$ 90.000,00 | R$ 10.500,00 | R$ 3.000,00 | -R$ 44.792,73 |
| Mês 3 | R$ 8.000,00 | R$ 144.000,00 | R$ 13.500,00 | R$ 8.100,00 | -R$ 36.692,73 |
| Mês 4 | R$ 8.000,00 | R$ 169.000,00 | R$ 13.500,00 | R$ 11.850,00 | -R$ 24.842,73 |
| Mês 5 | R$ 11.000,00 | R$ 213.000,00 | R$ 16.500,00 | R$ 15.450,00 | -R$ 9.392,73 |
| Mês 6 | R$ 11.000,00 | R$ 228.000,00 | R$ 16.500,00 | R$ 17.700,00 | **R$ 8.307,27** |
| Mês 7 | R$ 11.000,00 | R$ 243.000,00 | R$ 16.500,00 | R$ 19.950,00 | R$ 28.257,27 |

## Funil inverso mês a mês

O funil inverso usa as etapas confiáveis do dashboard:

`Sessões -> View cart -> Checkout -> Frete -> Pagamento -> Pedido -> Venda`

As taxas evoluem gradualmente e a conversão final não ultrapassa o bench interno comprovado de 2,95%.

### Realista — Mês 1

Faturamento alvo: **R$ 55.000,00**  
Ticket médio: **R$ 305,00**  
Vendas necessárias: **180**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 9.091 |
| View cart | 15,19% | 1.381 |
| Begin checkout | 89,70% | 1.239 |
| Add shipping info | 68,46% | 848 |
| Add payment info | 66,06% | 560 |
| Pedidos | 35,99% | 202 |
| Vendas | 89,29% | 180 |
| Taxa final Sessão -> Venda | 1,98% | - |

### Realista — Mês 2

Faturamento alvo: **R$ 75.000,00**  
Ticket médio: **R$ 308,00**  
Vendas necessárias: **244**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 11.619 |
| View cart | 15,30% | 1.778 |
| Begin checkout | 89,70% | 1.595 |
| Add shipping info | 69,50% | 1.108 |
| Add payment info | 67,50% | 748 |
| Pedidos | 36,48% | 273 |
| Vendas | 89,40% | 244 |
| Taxa final Sessão -> Venda | 2,10% | - |

### Realista — Mês 3

Faturamento alvo: **R$ 121.000,00**  
Ticket médio: **R$ 312,00**  
Vendas necessárias: **388**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 17.244 |
| View cart | 15,40% | 2.656 |
| Begin checkout | 89,80% | 2.385 |
| Add shipping info | 70,50% | 1.681 |
| Add payment info | 69,00% | 1.160 |
| Pedidos | 37,37% | 434 |
| Vendas | 89,50% | 388 |
| Taxa final Sessão -> Venda | 2,25% | - |

### Realista — Mês 4

Faturamento alvo: **R$ 146.000,00**  
Ticket médio: **R$ 315,00**  
Vendas necessárias: **463**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 19.292 |
| View cart | 15,50% | 2.990 |
| Begin checkout | 89,80% | 2.685 |
| Add shipping info | 71,50% | 1.920 |
| Add payment info | 70,00% | 1.344 |
| Pedidos | 38,45% | 517 |
| Vendas | 89,60% | 463 |
| Taxa final Sessão -> Venda | 2,40% | - |

### Realista — Mês 5

Faturamento alvo: **R$ 187.000,00**  
Ticket médio: **R$ 318,00**  
Vendas necessárias: **588**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 23.059 |
| View cart | 15,60% | 3.597 |
| Begin checkout | 89,90% | 3.234 |
| Add shipping info | 72,50% | 2.345 |
| Add payment info | 71,00% | 1.665 |
| Pedidos | 39,38% | 656 |
| Vendas | 89,70% | 588 |
| Taxa final Sessão -> Venda | 2,55% | - |

### Realista — Mês 6

Faturamento alvo: **R$ 197.000,00**  
Ticket médio: **R$ 322,00**  
Vendas necessárias: **612**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 22.667 |
| View cart | 15,80% | 3.581 |
| Begin checkout | 89,90% | 3.220 |
| Add shipping info | 73,50% | 2.366 |
| Add payment info | 72,00% | 1.704 |
| Pedidos | 40,00% | 682 |
| Vendas | 89,80% | 612 |
| Taxa final Sessão -> Venda | 2,70% | - |

### Realista — Mês 7

Faturamento alvo: **R$ 202.000,00**  
Ticket médio: **R$ 325,00**  
Vendas necessárias: **622**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 21.825 |
| View cart | 16,00% | 3.492 |
| Begin checkout | 90,00% | 3.143 |
| Add shipping info | 74,50% | 2.341 |
| Add payment info | 73,00% | 1.709 |
| Pedidos | 40,48% | 692 |
| Vendas | 89,90% | 622 |
| Taxa final Sessão -> Venda | 2,85% | - |

### Otimista — Mês 1

Faturamento alvo: **R$ 65.000,00**  
Ticket médio: **R$ 310,00**  
Vendas necessárias: **210**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 10.000 |
| View cart | 15,30% | 1.530 |
| Begin checkout | 89,70% | 1.372 |
| Add shipping info | 69,50% | 954 |
| Add payment info | 67,50% | 644 |
| Pedidos | 36,48% | 235 |
| Vendas | 89,40% | 210 |
| Taxa final Sessão -> Venda | 2,10% | - |

### Otimista — Mês 2

Faturamento alvo: **R$ 90.000,00**  
Ticket médio: **R$ 315,00**  
Vendas necessárias: **286**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 12.711 |
| View cart | 15,50% | 1.970 |
| Begin checkout | 89,80% | 1.769 |
| Add shipping info | 71,00% | 1.256 |
| Add payment info | 69,00% | 867 |
| Pedidos | 36,87% | 320 |
| Vendas | 89,50% | 286 |
| Taxa final Sessão -> Venda | 2,25% | - |

### Otimista — Mês 3

Faturamento alvo: **R$ 144.000,00**  
Ticket médio: **R$ 320,00**  
Vendas necessárias: **450**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 18.750 |
| View cart | 15,70% | 2.944 |
| Begin checkout | 89,80% | 2.643 |
| Add shipping info | 72,50% | 1.917 |
| Add payment info | 70,50% | 1.351 |
| Pedidos | 37,17% | 502 |
| Vendas | 89,60% | 450 |
| Taxa final Sessão -> Venda | 2,40% | - |

### Otimista — Mês 4

Faturamento alvo: **R$ 169.000,00**  
Ticket médio: **R$ 325,00**  
Vendas necessárias: **520**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 20.392 |
| View cart | 15,90% | 3.242 |
| Begin checkout | 89,90% | 2.915 |
| Add shipping info | 74,00% | 2.157 |
| Add payment info | 72,00% | 1.553 |
| Pedidos | 37,33% | 580 |
| Vendas | 89,70% | 520 |
| Taxa final Sessão -> Venda | 2,55% | - |

### Otimista — Mês 5

Faturamento alvo: **R$ 213.000,00**  
Ticket médio: **R$ 330,00**  
Vendas necessárias: **645**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 23.889 |
| View cart | 16,10% | 3.846 |
| Begin checkout | 89,90% | 3.458 |
| Add shipping info | 75,00% | 2.593 |
| Add payment info | 73,00% | 1.893 |
| Pedidos | 37,94% | 718 |
| Vendas | 89,80% | 645 |
| Taxa final Sessão -> Venda | 2,70% | - |

### Otimista — Mês 6

Faturamento alvo: **R$ 228.000,00**  
Ticket médio: **R$ 335,00**  
Vendas necessárias: **681**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 23.895 |
| View cart | 16,40% | 3.919 |
| Begin checkout | 90,00% | 3.527 |
| Add shipping info | 75,50% | 2.663 |
| Add payment info | 74,00% | 1.970 |
| Pedidos | 38,44% | 758 |
| Vendas | 89,90% | 681 |
| Taxa final Sessão -> Venda | 2,85% | - |

### Otimista — Mês 7

Faturamento alvo: **R$ 243.000,00**  
Ticket médio: **R$ 340,00**  
Vendas necessárias: **715**

| Etapa | Taxa usada | Volume necessário |
| ----- | -----: | -----: |
| Sessões | - | 24.237 |
| View cart | 16,58% | 4.019 |
| Begin checkout | 90,00% | 3.617 |
| Add shipping info | 76,00% | 2.749 |
| Add payment info | 74,00% | 2.034 |
| Pedidos | 39,06% | 794 |
| Vendas | 90,00% | 715 |
| Taxa final Sessão -> Venda | 2,95% | - |

## 5W1H

| O quê | Por quê | Onde | Quando | Quem | Como | Indicador |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| Reconfigurar tags Google Ads e GA4 | Recuperar mensuração e otimização do canal que zerou o ROAS após a migração | GTM, GA4, Google Ads e Tray | Imediato, até 7 dias | Tráfego + desenvolvimento | Auditar tags, gatilhos, transaction_id, purchase e importação de conversões | ROAS Google acima de 2x e compras atribuídas |
| Corrigir disparo de `add_shipping_info` | O evento acima de 100% distorce o funil e impede decisões confiáveis | GTM e GA4 | Até 7 dias | Tráfego | Validar disparo único por etapa, revisar dataLayer e remover gatilhos duplicados | Taxa de frete abaixo de 100% e coerência sequencial |
| Corrigir `add_to_cart` na Tray | Em maio há dias com compra sem registro de adição ao carrinho | Tray, GTM e GA4 | Até 7 dias | Desenvolvimento + tráfego | Auditar botão, AJAX, variantes e eventos da nova plataforma | Evento registrado em todas as adições reais |
| Simplificar checkout | Pagamento -> pedido é a maior fricção validada | Checkout Tray | Até 14 dias | Account + cliente + desenvolvimento | Destacar Pix, reduzir campos, revisar antifraude, boleto, frete e mensagens de erro | Pagamento -> pedido acima de 50% |
| Diagnosticar Connect Rate | Parte relevante dos cliques não chega ao site | Meta, Google, UTMs e redirecionamentos | Até 7 dias | Tráfego | Comparar clique, landing page view, sessão, velocidade, redirects e parâmetros UTM | Connect Rate acima de 75% |
| Reativar Shopping/PMax | Recuperar tráfego de fundo de funil e intenção de compra | Google Ads e feed Tray | Até 14 dias, após tracking | Tráfego | Corrigir XML, Merchant Center, produtos reprovados e campanhas por margem/estoque | Conversões Shopping acima de zero e ROAS acima de 6,67x |
| Escalar Meta catálogo de forma controlada | Meta sustentou a operação durante a quebra do Google | Meta Ads | Contínuo | Tráfego | Aumentos graduais condicionados a ROAS e estoque; priorizar campanhas e criativos vencedores | ROAS incremental acima de 6,67x |
| Estruturar régua de CRM | Reduzir dependência de mídia e ativar a base de 1.500 clientes | CRM, e-mail e WhatsApp | Até 30 dias | Account + CRM + cliente | Fluxos de recompra em 15, 30 e 45 dias, win-back e kits de reposição | Recompra +5 p.p. e receita CRM acima de R$ 4 mil/mês |
| Criar kits, combos e ofertas progressivas | Aumentar ticket e margem média sem depender apenas de sessões | PDP, carrinho, CRM e mídia | Até 30 dias | Account + cliente + mídia | Combos por segmento, frete grátis por faixa, desconto progressivo e priorização PJ | Ticket acima de R$ 325 e margem preservada |
| Aplicar escala de mídia por gatilho | Evitar aumentar custo antes da validação econômica | Meta e Google Ads | Após mês positivo | Account + tráfego | R$ 5 mil -> R$ 8 mil -> R$ 11 mil, condicionado a ROAS incremental superior a 6,67x | Resultado mensal positivo e acumulado em recuperação |

## Leitura estratégica

O breakeven em sete meses não será alcançado apenas com otimização de taxa. O projeto precisa combinar recuperação de tráfego pago, melhora do checkout, aumento gradual do ticket, ativação de recompra e escala de mídia condicionada à eficiência.

O cenário Realista exige chegar a aproximadamente R$ 202 mil/mês no mês 7, com conversão final de 2,85%. O cenário Otimista exige R$ 243 mil/mês e conversão final no teto comprovado de 2,95%.

A escala de mídia só cria valor se o ROAS incremental permanecer acima de 6,67x. Abaixo disso, o aumento de verba melhora faturamento, mas piora ou não acelera a recuperação do breakeven.
