# Portabilidade entre IAs

Está skill usa arquivos e comandos comuns:

- `SKILL.md` para instruções.
- Markdown e JSON UTF-8.
- Python 3.
- `xlsxwriter` para gerar a planilha.

## Claude

Pedir para ler `SKILL.md` e executar o fluxo. A pasta pode ser instalada como skill ou mantida dentro do projeto.

## Codex

Invocar `$breakeven-projetos` quando instalada ou apontar diretamente para a pasta.

## Cursor, Composer e outras IAs

Adicionar `SKILL.md` ao contexto ou às regras do projeto e solicitar que siga o workflow. Os scripts não dependem de APIs específicas de uma IA.

## Ambientes sem execução

Quando a IA não puder executar Python:

1. Usar os modelos em `assets/`.
2. Produzir o JSON de configuração.
3. Entregar os comandos exatos para execução local.
4. Não alegar que os arquivos foram gerados ou validados.
