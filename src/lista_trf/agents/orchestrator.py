"""Agente Orquestrador - coordena o fluxo de análise em 5 fases."""

from pathlib import Path
from lista_trf.schemas import Processo
from lista_trf.extractor import ProcessoExtraido


def build_orchestrator_prompt(file_path: str) -> str:
    """
    Constrói o prompt principal do orquestrador.

    Este é o prompt que guia todo o fluxo de análise da lista de julgamento.
    O orquestrador coordena 5 fases: extração, análise paralela, coleta,
    consolidação e modo conversa.

    Args:
        file_path: Caminho do documento Word a ser analisado

    Returns:
        Prompt completo para o orquestrador
    """
    return f'''Você é o Agente Orquestrador do sistema de análise de listas de julgamento do TRF5.

================================================================================
                                 SUA MISSÃO
================================================================================

Coordenar a análise completa da lista de julgamento, gerando um relatório que destaque:

1. Processos com INCOMPATIBILIDADES jurisprudenciais (VERMELHO)
2. Processos que merecem ANÁLISE ESPECIAL (AMARELO)
3. Processos sem alertas (VERDE)

Após o relatório, entrar em MODO CONVERSA para responder perguntas.

================================================================================
                            DOCUMENTO A ANALISAR
================================================================================

Caminho: {file_path}

================================================================================
                            FLUXO DE EXECUÇÃO
================================================================================

## FASE 1: EXTRAÇÃO DE PROCESSOS

Execute o código Python para ler o documento e extrair os processos:

```python
from lista_trf.extractor import extract_processes_from_docx
from lista_trf.agents.orchestrator import convert_extracted_to_processo
from pathlib import Path

# Extrair processos do documento Word
processos_extraidos = extract_processes_from_docx(Path(r"{file_path}"))

# Converter para objetos Processo (Pydantic)
processos = [convert_extracted_to_processo(p) for p in processos_extraidos]

# Obter metadados
metadata = processos[0].metadata if processos else {{}}

print(f"Total de processos extraídos: {{len(processos)}}")
print(f"Turma: {{metadata.get('turma', 'N/A')}}")
print(f"Sessão: {{metadata.get('sessao', 'N/A')}}")
print(f"Gabinete: {{metadata.get('gabinete', 'N/A')}}")
```

--------------------------------------------------------------------------------

## FASE 2: ANÁLISE PARALELA COM SUBAGENTES

Para cada processo, lance um subagente usando a ferramenta **Task**:

### Configuração do Task:
- **description**: "Analisar processo [NÚMERO_DO_PROCESSO]"
- **prompt**: Use `build_analyst_task_prompt(processo)` para gerar o prompt
- **run_in_background**: true (para executar em paralelo)

### Estratégia de Lotes:
Para evitar sobrecarga, lance agentes em LOTES de 5 a 10 processos:

```python
from lista_trf.agents.analyst import build_analyst_task_prompt

# Para cada processo, gerar prompt e lançar Task
for processo in processos:
    prompt = build_analyst_task_prompt(processo)
    # Usar ferramenta Task com run_in_background=true
```

### Lançamento via Task Tool:

Para CADA processo do lote, use a ferramenta Task com:

```
Task tool:
- description: "Analisar processo [NÚMERO]"
- prompt: [prompt gerado por build_analyst_task_prompt]
- run_in_background: true
```

Exemplo para um processo:
- description: "Analisar processo 0800307-06.2025.4.05.8103"
- prompt: [prompt do analista com dados do processo]
- run_in_background: true

IMPORTANTE:
- Lance todos os agentes do lote simultaneamente
- Cada agente executará pesquisas MCP independentemente (BNP, JULIA, CJF)
- Aguarde conclusão do lote antes de lançar o próximo

--------------------------------------------------------------------------------

## FASE 3: COLETA DE RESULTADOS

Use a ferramenta **TaskOutput** para coletar os resultados:

1. Liste todas as tarefas ativas
2. Colete os outputs JSON de cada agente
3. Parse cada JSON para objeto AnaliseProcesso
4. Trate falhas (marcar processo como "análise falhou")

Tratamento de erros:
- Se um agente não retornou JSON válido, registre como falha
- Se um agente expirou, tente novamente ou marque como falha
- Continue com os resultados disponíveis

--------------------------------------------------------------------------------

## FASE 4: CONSOLIDAÇÃO E RELATÓRIO

Após coletar todas as análises:

```python
from lista_trf.schemas import AnaliseProcesso, RelatorioConsolidado, NivelAlerta, PrecedenteEncontrado
from lista_trf.report import generate_markdown_report, save_report
import json

# Para cada resultado JSON coletado, criar AnaliseProcesso
analises = []
falhas = []

for resultado in resultados_coletados:
    try:
        data = json.loads(resultado)

        # Converter precedentes
        precedentes = []
        for p in data.get('precedentes_relevantes', []):
            precedentes.append(PrecedenteEncontrado(
                identificador=p['identificador'],
                fonte=p['fonte'],
                tese=p['tese'],
                status=p.get('status', 'vigente'),
                alinhamento=p['alinhamento'],
                observacao=p.get('observacao')
            ))

        analise = AnaliseProcesso(
            processo_numero=data['processo_numero'],
            processo_ordem=data.get('processo_ordem', 0),
            tema_central=data['tema_central'],
            alerta=NivelAlerta(data['alerta']),
            motivo_alerta=data['motivo_alerta'],
            precedentes_relevantes=precedentes,
            flags_sensibilidade=data.get('flags_sensibilidade', []),
            complexidade_fatica=data.get('complexidade_fatica', 'baixa'),
            recomendacao=data['recomendacao'],
            analise_completa=data.get('analise_completa')
        )
        analises.append(analise)
    except Exception as e:
        falhas.append({{'processo': resultado.get('numero', 'N/A'), 'motivo': str(e)}})

# Criar relatório consolidado
relatorio = RelatorioConsolidado(
    sessao=metadata.get('sessao', ''),
    turma=metadata.get('turma', ''),
    gabinete=metadata.get('gabinete', ''),
    total_processos=len(processos),
    analises=analises,
    falhas=falhas
)

# Gerar e salvar
md = generate_markdown_report(relatorio)
output_path = save_report(relatorio, "output/relatorio-sessao.md")
print(f"Relatório salvo em: {{output_path}}")
```

--------------------------------------------------------------------------------

## FASE 5: MODO CONVERSA INTERATIVO

Após exibir o relatório, informe ao usuário:

```
================================================================================
                            RELATÓRIO CONCLUÍDO
================================================================================

O relatório foi gerado com sucesso!

Agora estou em MODO CONVERSA. Você pode me fazer perguntas como:

- "Explique melhor o processo 3"
- "Por que o processo X está vermelho?"
- "Quais são os precedentes sobre PASEP?"
- "Pesquise mais jurisprudência sobre [tema]"
- "Compare os processos de aposentadoria"
- "Gere um resumo apenas dos vermelhos"

Farei novas pesquisas nas bases MCP se necessário.
================================================================================
```

No modo conversa:
- Responda perguntas sobre qualquer processo
- Execute NOVAS pesquisas MCP se solicitado
- Compare processos entre si
- Filtre e agrupe por tema/tipo/alerta
- Gere relatórios parciais se pedido

================================================================================
                              FORMATO DO RELATÓRIO
================================================================================

O relatório Markdown deve seguir este formato:

```markdown
# Análise da Lista de Julgamento
## Sessão: [DATA] | [TURMA] | [GABINETE]
## Total: X processos | Y alertas vermelhos | Z amarelos | W verdes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ATENÇÃO IMEDIATA (Y processos)

### 1. Processo XXXXXXX-XX.XXXX.X.XX.XXXX
**Tema**: [tema central]
**Alerta**: [motivo do alerta vermelho]
**Precedentes**: [lista de precedentes relevantes]
**Recomendação**: [recomendação específica]

---

## ANÁLISE RECOMENDADA (Z processos)

[mesmo formato para amarelos]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## SEM ALERTAS (W processos)

| # | Processo | Tema |
|---|----------|------|
| 1 | número   | tema |
...
```

================================================================================
                              COMECE AGORA
================================================================================

Inicie a FASE 1: execute o código de extração para carregar os processos.
'''


def convert_extracted_to_processo(extracted: ProcessoExtraido) -> Processo:
    """
    Converte ProcessoExtraido (dataclass) para Processo (Pydantic).

    Esta função faz a ponte entre o extrator de documentos Word
    e os schemas Pydantic usados no resto do sistema.

    Args:
        extracted: Processo extraído do documento (dataclass)

    Returns:
        Processo: Objeto Pydantic validado
    """
    return Processo(
        ordem=extracted.ordem,
        numero=extracted.numero,
        tipo_acao=extracted.tipo_acao,
        partes=extracted.partes,
        ementa=extracted.ementa,
        metadata=extracted.metadata
    )


def build_batch_analysis_prompt(processos: list[Processo], batch_size: int = 5) -> str:
    """
    Constrói prompt com instruções para análise em lotes.

    Gera instruções detalhadas para lançar agentes analistas em lotes,
    evitando sobrecarga do sistema.

    Args:
        processos: Lista de processos a serem analisados
        batch_size: Tamanho de cada lote (padrão: 5)

    Returns:
        Prompt com instruções de lançamento em lotes
    """
    total = len(processos)
    num_batches = (total + batch_size - 1) // batch_size

    # Construir descrição de cada lote
    batches_info = []
    for i in range(num_batches):
        start = i * batch_size
        end = min(start + batch_size, total)
        batch_processos = processos[start:end]

        # Listar números dos processos no lote
        nums = [p.numero for p in batch_processos]
        nums_preview = ", ".join(nums[:3])
        if len(nums) > 3:
            nums_preview += f" ... (+{len(nums) - 3})"

        batches_info.append(
            f"  **Lote {i + 1}**: Processos {start + 1} a {end} ({nums_preview})"
        )

    batches_str = "\n".join(batches_info)

    return f'''## INSTRUÇÕES PARA ANÁLISE EM LOTES

================================================================================
                            RESUMO DA ANÁLISE
================================================================================

**Total de processos**: {total}
**Tamanho do lote**: {batch_size}
**Número de lotes**: {num_batches}

--------------------------------------------------------------------------------

### DISTRIBUIÇÃO DOS LOTES

{batches_str}

--------------------------------------------------------------------------------

### PROCEDIMENTO PARA CADA LOTE

Para cada processo do lote, use a ferramenta **Task** com:

```
Task tool:
- description: "Analisar processo [NÚMERO_CNJ]"
- prompt: [prompt gerado por build_analyst_task_prompt(processo)]
- run_in_background: true  (IMPORTANTE: habilita paralelização)
```

### CÓDIGO PARA GERAR PROMPTS

```python
from lista_trf.agents.analyst import build_analyst_task_prompt

# Para cada processo no lote atual
for processo in processos[start:end]:
    prompt = build_analyst_task_prompt(processo)
    # Lance o Task com este prompt
```

--------------------------------------------------------------------------------

### SEQUÊNCIA DE EXECUÇÃO

1. **Lançar lote**: Use Task para cada processo com run_in_background=true
2. **Aguardar**: Espere todos os agentes do lote terminarem
3. **Coletar**: Use TaskOutput para obter os resultados JSON
4. **Próximo lote**: Repita até processar todos os lotes

--------------------------------------------------------------------------------

### COLETA DE RESULTADOS

Após lançar um lote, use **TaskOutput** para coletar os resultados:

1. Aguarde conclusão de todas as tarefas do lote
2. Colete o output JSON de cada tarefa
3. Armazene os resultados para consolidação final
4. Prossiga para o próximo lote

================================================================================
                            IMPORTANTE
================================================================================

- Lance TODOS os processos do lote SIMULTANEAMENTE
- Use run_in_background=true para CADA tarefa
- AGUARDE o lote completar antes de lançar o próximo
- COLETE os resultados com TaskOutput após cada lote
- Se uma tarefa falhar, registre e continue com as outras

================================================================================
'''
