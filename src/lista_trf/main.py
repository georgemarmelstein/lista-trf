"""Módulo principal - ponto de entrada do sistema de análise."""

from pathlib import Path
from lista_trf.extractor import extract_processes_from_docx
from lista_trf.agents.orchestrator import convert_extracted_to_processo
from lista_trf.agents.analyst import build_analyst_task_prompt


def prepare_analysis(file_path: str) -> dict:
    """
    Prepara análise extraindo processos do documento Word.

    Esta função é o ponto de entrada para carregar uma lista de julgamento
    e preparar os dados para análise pelos agentes.

    Args:
        file_path: Caminho do documento Word (.docx)

    Returns:
        Dicionário com:
        - file_path: Caminho absoluto do arquivo
        - total_processos: Quantidade de processos extraídos
        - processos: Lista de objetos Processo (Pydantic)
        - metadata: Metadados da sessão (turma, data, gabinete)

    Raises:
        FileNotFoundError: Se o arquivo não existir
        ValueError: Se o formato do arquivo não for .docx
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    if not path.suffix.lower() == '.docx':
        raise ValueError(f"Formato não suportado: {path.suffix}. Use arquivos .docx")

    # Extrair processos do documento Word
    extracted = extract_processes_from_docx(path)

    # Converter para schema Pydantic
    processos = [convert_extracted_to_processo(e) for e in extracted]

    # Extrair metadados do primeiro processo (todos têm os mesmos)
    metadata = {}
    if processos and processos[0].metadata:
        metadata = processos[0].metadata

    return {
        "file_path": str(path.absolute()),
        "total_processos": len(processos),
        "processos": processos,
        "metadata": metadata
    }


def generate_analyst_prompts(processos: list) -> list[dict]:
    """
    Gera prompts de análise para todos os processos.

    Cada prompt contém as instruções completas para um agente analista
    pesquisar precedentes e determinar o nível de alerta do processo.

    Args:
        processos: Lista de objetos Processo

    Returns:
        Lista de dicionários, cada um contendo:
        - numero: Número CNJ do processo
        - ordem: Ordem do processo na lista
        - prompt: Prompt completo para o agente analista
    """
    prompts = []
    for processo in processos:
        prompts.append({
            "numero": processo.numero,
            "ordem": processo.ordem,
            "prompt": build_analyst_task_prompt(processo)
        })
    return prompts


# =============================================================================
#                           PROMPT MASTER
# =============================================================================
# Este prompt serve como guia de uso do sistema no Claude Code.
# Pode ser exibido ao usuário ou usado como referência para comandos.

MASTER_PROMPT = '''
================================================================================
          SISTEMA DE ANÁLISE DE LISTAS DE JULGAMENTO - TRF5
================================================================================

Este sistema analisa listas de julgamento do TRF5, pesquisa precedentes em
múltiplas bases (BNP, JULIA, CJF) e gera relatório destacando incompatibilidades
jurisprudenciais e casos sensíveis.

--------------------------------------------------------------------------------
                              COMO USAR
--------------------------------------------------------------------------------

### 1. Carregar e Preparar a Lista

```python
from lista_trf.main import prepare_analysis, generate_analyst_prompts

# Carregar documento Word
data = prepare_analysis(r"CAMINHO_DO_ARQUIVO.docx")

# Verificar informações
print(f"Processos encontrados: {data['total_processos']}")
print(f"Turma: {data['metadata'].get('turma', 'N/A')}")
print(f"Sessão: {data['metadata'].get('sessao', 'N/A')}")
print(f"Gabinete: {data['metadata'].get('gabinete', 'N/A')}")

# Gerar prompts para os analistas
prompts = generate_analyst_prompts(data['processos'])
```

### 2. Analisar Processos com Subagentes

Para cada processo, lance um subagente usando a ferramenta Task:

```
Task tool:
- description: "Analisar processo [NÚMERO]"
- prompt: prompts[i]['prompt']
- run_in_background: true
```

Lance em lotes de 5-10 para paralelizar sem sobrecarregar.

### 3. Coletar Resultados

Use TaskOutput para coletar os JSONs de análise de cada agente.

### 4. Gerar Relatório

```python
from lista_trf.report import generate_markdown_report, save_report
from lista_trf.schemas import RelatorioConsolidado, AnaliseProcesso, NivelAlerta

# Após converter os JSONs coletados em objetos AnaliseProcesso
relatorio = RelatorioConsolidado(
    sessao=data['metadata'].get('sessao', ''),
    turma=data['metadata'].get('turma', ''),
    gabinete=data['metadata'].get('gabinete', ''),
    total_processos=len(analises),
    analises=analises
)

# Gerar e salvar
output_path = save_report(relatorio, "output/relatorio.md")
print(f"Relatório salvo em: {output_path}")
```

### 5. Modo Conversa

Após o relatório, responda perguntas do usuário:
- "Explique o processo 3"
- "Por que o processo X está vermelho?"
- "Pesquise mais sobre [tema]"

--------------------------------------------------------------------------------
                           NÍVEIS DE ALERTA
--------------------------------------------------------------------------------

- VERMELHO: Divergência com precedente vinculante
- AMARELO: Tema sensível, jurisprudência em evolução, divergência entre turmas
- VERDE: Alinhado com jurisprudência consolidada

--------------------------------------------------------------------------------
                          FERRAMENTAS MCP
--------------------------------------------------------------------------------

BNP (Banco Nacional de Precedentes):
  mcp__bnp-api__buscar_precedentes
  Sintaxe: +termo -excluir "frase exata"

JULIA (TRF5):
  mcp__julia-trf5__buscar_julia
  Sintaxe: termo1 e termo2 ou alternativa

CJF (Base Unificada):
  mcp__cjf-jurisprudencia__buscar_jurisprudencia_cjf
  Sintaxe: termo1 E termo2 OU alternativa[EMEN]

================================================================================
'''
