# Sistema de Análise de Listas de Julgamento - TRF5

## Visão Geral

Sistema agêntico que analisa listas de julgamento do TRF5, pesquisa precedentes em múltiplas bases (BNP, JULIA, CJF) e gera relatório destacando incompatibilidades jurisprudenciais.

## Como Usar

### Comando Principal

Quando o usuário pedir para analisar uma lista, execute:

```
analisa lista: <caminho_do_arquivo.docx>
```

### Fluxo de Análise

1. **Extrair processos**:
```python
from lista_trf.main import prepare_analysis, generate_analyst_prompts

data = prepare_analysis(r"caminho/arquivo.docx")
prompts = generate_analyst_prompts(data['processos'])
```

2. **Analisar em paralelo**: Para cada processo, lance subagente com Task tool:
   - `subagent_type`: "general-purpose"
   - `run_in_background`: true
   - `prompt`: prompt específico do processo

3. **Coletar resultados**: Use TaskOutput para obter análises

4. **Gerar relatório**:
```python
from lista_trf.report import save_report
from lista_trf.schemas import RelatorioConsolidado

relatorio = RelatorioConsolidado(...)
save_report(relatorio, "output/relatorio.md")
```

5. **Modo conversa**: Após relatório, responder perguntas do usuário

## Ferramentas MCP Disponíveis

### BNP (Banco Nacional de Precedentes)
- `mcp__bnp-api__buscar_precedentes`: Busca temas vinculantes
- Sintaxe: `+termo -excluir "frase exata"`

### JULIA (TRF5)
- `mcp__julia-trf5__buscar_julia`: Jurisprudência TRF5
- Sintaxe: `termo e outro ou (alternativa)`
- Filtros: `orgao_julgador`, `relator`

### CJF (Base Unificada)
- `mcp__cjf-jurisprudencia__buscar_jurisprudencia_cjf`: STF, STJ, TRFs
- Sintaxe: `termo E outro OU (alt)[EMEN]`

## Níveis de Alerta

- **VERMELHO**: Divergência com precedente vinculante
- **AMARELO**: Tema sensível, jurisprudência em evolução, divergência entre turmas
- **VERDE**: Alinhado com jurisprudência consolidada

## Estrutura do Projeto

```
lista-trf/
├── src/lista_trf/
│   ├── __init__.py
│   ├── extractor.py      # Extração de documentos Word
│   ├── schemas.py        # Modelos Pydantic
│   ├── prompts.py        # Templates de prompts
│   ├── report.py         # Geração de relatório
│   ├── main.py           # Módulo principal
│   └── agents/
│       ├── __init__.py
│       ├── analyst.py    # Agente analista
│       └── orchestrator.py # Orquestrador
├── tests/                # Testes
├── output/               # Relatórios gerados
├── docs/plans/           # Documentação
├── analyze_list.py       # Entry point
└── CLAUDE.md            # Este arquivo
```
