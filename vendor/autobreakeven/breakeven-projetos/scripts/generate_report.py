#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from statistics import median


def brl(value):
    sign = "-" if value < 0 else ""
    text = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}R$ {text}"


def pct(value):
    return f"{value * 100:.2f}%".replace(".", ",")


def benchmark(config):
    rows = []
    for row in config["benchmark_months"]:
        month, sessions, view, add, cart, checkout, shipping, payment, purchase = row
        rows.append(
            [
                month,
                min(1, view / sessions),
                min(1, add / view),
                min(1, cart / add),
                min(1, checkout / cart),
                min(1, shipping / checkout),
                min(1, payment / shipping),
                min(1, purchase / payment),
                min(1, purchase / sessions),
            ]
        )
    return [median(row[col] for row in rows) for col in range(1, 9)]


def scenario_summary(config, current_result):
    output = []
    for name in ("Pessimista", "Realista", "Otimista"):
        scenario = config["scenarios"][name]
        balance = current_result
        month = "Não breakeva"
        for idx, (revenue, media) in enumerate(
            zip(scenario["revenue"], scenario["media"]), 1
        ):
            balance += revenue * config["margin"] - (
                config["monthly_fee"] + media
            )
            if balance >= 0 and month == "Não breakeva":
                month = f"Mês {idx}"
        output.append(
            [
                name,
                sum(scenario["revenue"]),
                sum(scenario["media"]),
                balance,
                month,
            ]
        )
    return output


def main():
    parser = argparse.ArgumentParser(
        description="Gera o relatório-base de análise e estratégia do breakeven."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    source = config["source_months"]
    fee = sum(row[1] for row in source)
    media = sum(row[2] for row in source)
    sessions = sum(row[3] for row in source)
    orders = sum(row[4] for row in source)
    sales = sum(row[5] for row in source)
    revenue = sum(row[6] for row in source)
    cost = fee + media
    mc = revenue * config["margin"]
    result = mc - cost
    ticket = revenue / sales
    monthly_break_even = (
        config["monthly_fee"] + config["monthly_media"]
    ) / config["margin"]
    future_cost = 7 * (config["monthly_fee"] + config["monthly_media"])
    future_required = (abs(result) + future_cost) / config["margin"]
    medians = benchmark(config)
    current = config["current_funnel"]
    context = config.get("context", {})

    stage_names = [
        "Sessão → View item",
        "View item → Add to cart",
        "Add to cart → View cart",
        "View cart → Begin checkout",
        "Begin checkout → Add shipping info",
        "Add shipping info → Add payment info",
        "Add payment info → Purchase",
        "Sessão → Purchase",
    ]
    current_rates = [
        current["view_item"] / current["sessions"],
        current["add_to_cart"] / current["view_item"],
        min(1, current["view_cart"] / current["add_to_cart"]),
        current["begin_checkout"] / current["view_cart"],
        min(1, current["add_shipping_info"] / current["begin_checkout"]),
        current["add_payment_info"] / current["add_shipping_info"],
        current["purchase"] / current["add_payment_info"],
        current["purchase"] / current["sessions"],
    ]

    lines = [
        f"# [Gerência] - [Análise e Estratégia] - [{config['client']}]",
        "",
        "## Contexto do projeto",
        "",
        "| Campo | Valor |",
        "| ----- | ----- |",
        f"| Cliente | {config['client']} |",
        f"| Produto ativo | {context.get('product', '[PREENCHER]')} |",
        f"| Modelo | {config.get('project_model', '[PREENCHER]')} |",
        f"| Fase atual | {context.get('phase', '[PREENCHER]')} |",
        f"| Maior risco | {context.get('main_risk', '[PREENCHER]')} |",
        f"| Premissa financeira | Margem de contribuição de {pct(config['margin'])} |",
        "",
        "## Premissas financeiras",
        "",
        "| Item | Valor |",
        "| ----- | -----: |",
        f"| Fee mensal | {brl(config['monthly_fee'])} |",
        f"| Mídia mensal | {brl(config['monthly_media'])} |",
        f"| Margem de contribuição | {pct(config['margin'])} |",
        f"| Faturamento para breakevar uma competência | {brl(monthly_break_even)} |",
        f"| Resultado líquido acumulado | **{brl(result)}** |",
        "",
        "## Cenário atual acumulado",
        "",
        f"Fonte: meses válidos do Growth Pack, período {config['lt_period']}.",
        "",
        "| Item | Valor |",
        "| ----- | -----: |",
        f"| Fee acumulado | {brl(fee)} |",
        f"| Investimento acumulado | {brl(media)} |",
        f"| Custo total acumulado | {brl(cost)} |",
        f"| Faturamento acumulado | {brl(revenue)} |",
        f"| Resultado MC acumulado | {brl(mc)} |",
        f"| Resultado líquido acumulado | **{brl(result)}** |",
        f"| Ticket médio | {brl(ticket)} |",
        f"| Receita futura necessária em 7 meses | {brl(future_required)} |",
        "",
        "## Funil atual + bench interno",
        "",
        f"Período atual considerado: {config['current_period']}.",
        "",
        "| Etapa | Taxa atual | Bench interno |",
        "| ----- | -----: | -----: |",
    ]
    for stage, current_rate, bench_rate in zip(
        stage_names, current_rates, medians
    ):
        lines.append(
            f"| {stage} | {pct(current_rate)} | {pct(bench_rate)} |"
        )

    lines.extend(
        [
            "",
            f"O bench corresponde à mediana dos {len(config['benchmark_months'])} meses de LT. Taxas mensais acima de 100,00% são limitadas a 100,00% antes do cálculo.",
            "",
            "## Qualidade do tracking",
            "",
            "- Validar taxas acima de 100,00% e eventos não sequenciais.",
            "- Não classificar o dado como duplicado sem verificar data + evento e implementação.",
            "- Registrar aqui somente evidências confirmadas no Growth Pack, GA4 ou GTM.",
            "",
            "## Diagnóstico das alavancas",
            "",
        ]
    )
    for item in context.get("diagnosis", ["[PREENCHER COM EVIDÊNCIAS]"]):
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Cenários de breakeven",
            "",
            "| Cenário | Receita 7M | Mídia 7M | Saldo final | Breakeven acumulado |",
            "| ----- | -----: | -----: | -----: | ----- |",
        ]
    )
    for name, scenario_revenue, scenario_media, balance, month in scenario_summary(
        config, result
    ):
        lines.append(
            f"| {name} | {brl(scenario_revenue)} | {brl(scenario_media)} | {brl(balance)} | {month} |"
        )

    lines.extend(
        [
            "",
            "## Evolução mês a mês",
            "",
        ]
    )
    for name in ("Pessimista", "Realista", "Otimista"):
        scenario = config["scenarios"][name]
        balance = result
        lines.extend(
            [
                f"### {name}",
                "",
                "| Mês | Mídia | Faturamento | Resultado do mês | Resultado acumulado |",
                "| ----- | -----: | -----: | -----: | -----: |",
            ]
        )
        for idx, (scenario_revenue, scenario_media) in enumerate(
            zip(scenario["revenue"], scenario["media"]), 1
        ):
            monthly_result = scenario_revenue * config["margin"] - (
                config["monthly_fee"] + scenario_media
            )
            balance += monthly_result
            lines.append(
                f"| Mês {idx} | {brl(scenario_media)} | {brl(scenario_revenue)} | {brl(monthly_result)} | {brl(balance)} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Funil inverso",
            "",
            f"O funil para zerar somente a competência parte de {brl(monthly_break_even)} de faturamento. Os funis completos, mês a mês, ficam na planilha gerada.",
            "",
            "## 5W1H",
            "",
            "| O quê | Por quê | Onde | Quando | Quem | Como | Indicador |",
            "| ----- | ----- | ----- | ----- | ----- | ----- | ----- |",
        ]
    )
    for action in context.get("actions", ["[PREENCHER]"]):
        lines.append(
            f"| {action} | [CAUSA] | [LOCAL] | [PRAZO] | [RESPONSÁVEL] | [MÉTODO] | [KPI] |"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
