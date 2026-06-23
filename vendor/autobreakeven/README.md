# Auto Breakeven

Skill portátil para analisar Growth Packs de projetos, calcular breakeven é gerar:

- relatório estratégico em Markdown;
- planilha de breakeven com fórmulas;
- bench interno pela mediana dos meses de LT;
- funil para zerar a competência;
- recuperação do carry over;
- cenários Pessimista, Realista e Otimista.

## Estrutura

```text
breakeven-projetos/
├── SKILL.md
├── agents/
├── assets/
├── references/
└── scripts/
```

O arquivo principal de instruções é:

```text
breakeven-projetos/SKILL.md
```

## Instalação rápida

### Codex

```bash
./install.sh codex
```

Instala em `~/.codex/skills/breakeven-projetos`.

### Claude Code

```bash
./install.sh claude
```

Instala em `~/.claude/skills/breakeven-projetos`.

### Cursor ou Composer

```bash
./install.sh cursor
```

Instala em `.cursor/skills/breakeven-projetos` no projeto atual.

### Caminho personalizado

```bash
./install.sh custom /caminho/para/skills
```

## Dependência

```bash
python3 -m pip install -r breakeven-projetos/scripts/requirements.txt
```

O inspetor de Growth Packs e o gerador de Markdown usam apenas a biblioteca padrão do Python. A criação da planilha requer `xlsxwriter`.

## Uso

Peça ao agente:

```text
Use a skill breakeven-projetos para analisar este Growth Pack e gerar
o relatório estratégico e a planilha completa de breakeven.
```

O agente deve seguir o gate de alinhamento do `SKILL.md` antes de gerar os arquivos.

## Teste

```bash
./smoke-test.sh
```

O teste valida o JSON de exemplo e gera uma planilha e um relatório em uma pasta temporária.

## Portabilidade

A skill não depende de APIs específicas de uma IA. Ela usa:

- Markdown e JSON em UTF-8;
- Python 3;
- arquivos `.xlsx`;
- comandos locais reproduzíveis.

Em ambientes que não reconhecem skills automaticamente, adicione `breakeven-projetos/SKILL.md` ao contexto do agente.
