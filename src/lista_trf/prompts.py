"""Templates de prompts para os agentes do sistema."""

from lista_trf.schemas import Processo, AnaliseProcesso


def build_analyst_prompt(processo: Processo) -> str:
    """
    Constroi o prompt para o Agente Analista.

    Args:
        processo: Processo a ser analisado

    Returns:
        Prompt completo para o agente
    """
    turma = processo.metadata.get("turma", "Nao informada")

    return f'''Voce e um agente analista juridico especializado em direito previdenciario e administrativo federal.

## Sua Tarefa

Analisar o processo abaixo e verificar se a posicao adotada na ementa esta alinhada com a jurisprudencia consolidada.

## Processo para Analise

**Numero**: {processo.numero}
**Tipo**: {processo.tipo_acao or "Nao informado"}
**Turma**: {turma}
**Partes**: {processo.partes or "Nao informadas"}

**EMENTA**:
{processo.ementa}

## Instrucoes de Analise

### Fase 1: Classificacao
1. Identifique o TEMA JURIDICO CENTRAL da ementa (ex: "prescricao PASEP", "aposentadoria especial ruido")
2. Identifique se ha FLAGS DE SENSIBILIDADE:
   - Improbidade administrativa
   - Questoes ambientais
   - Acoes civis publicas
   - Comunidades tradicionais
   - Minorias
   - Complexidade fatica elevada
3. Avalie a COMPLEXIDADE FATICA (baixa/media/alta)

### Fase 2: Pesquisa de Precedentes
Use as ferramentas MCP para pesquisar:

1. **BNP (Banco Nacional de Precedentes)**:
   - Use `mcp__bnp-api__buscar_precedentes` com query apropriada
   - Busque Temas de Repercussao Geral (STF) e Recursos Repetitivos (STJ)
   - Busque Sumulas Vinculantes relacionadas

2. **JULIA (TRF5)**:
   - Use `mcp__julia-trf5__buscar_julia` para jurisprudencia do TRF5
   - IMPORTANTE: Filtre por `orgao_julgador` = "{turma}" para ver precedentes da propria turma
   - Verifique tambem outras turmas para identificar divergencias

3. **CJF (Base Unificada)**:
   - Use `mcp__cjf-jurisprudencia__buscar_jurisprudencia_cjf` se necessario
   - Util para comparar posicoes entre TRFs

### Fase 3: Analise Comparativa
Compare a posicao da ementa com os precedentes encontrados:

1. **ALERTA VERMELHO** (Atencao Imediata):
   - Divergencia direta com precedente vinculante (Tema STF/STJ vigente)
   - Contradicao com Sumula Vinculante
   - Posicao contraria a jurisprudencia pacifica da propria turma

2. **ALERTA AMARELO** (Analise Recomendada):
   - Tema sensivel (improbidade, ambiental, minorias, etc.)
   - Jurisprudencia em evolucao ou pendente de modulacao
   - Divergencia entre turmas do TRF5
   - Complexidade fatica elevada
   - Questao juridica inedita

3. **ALERTA VERDE** (Sem Alertas):
   - Ementa alinhada com jurisprudencia consolidada
   - Tema pacificado
   - Caso padrao sem peculiaridades

## Formato de Resposta

Responda EXCLUSIVAMENTE com um JSON valido no seguinte formato:

```json
{{
  "processo_numero": "{processo.numero}",
  "processo_ordem": {processo.ordem},
  "tema_central": "descricao do tema em poucas palavras",
  "alerta": "vermelho|amarelo|verde",
  "motivo_alerta": "explicacao clara e concisa do motivo do alerta",
  "precedentes_relevantes": [
    {{
      "identificador": "Tema XXX/STJ ou Sumula XXX",
      "fonte": "BNP|JULIA|CJF",
      "tese": "texto resumido da tese",
      "status": "vigente|superado|pendente",
      "alinhamento": "compativel|divergente|parcial",
      "observacao": "observacao relevante se houver"
    }}
  ],
  "flags_sensibilidade": ["flag1", "flag2"],
  "complexidade_fatica": "baixa|media|alta",
  "recomendacao": "recomendacao especifica de acao",
  "analise_completa": "texto detalhado da analise para referencia futura"
}}
```

IMPORTANTE: Retorne APENAS o JSON, sem texto adicional antes ou depois.
'''


def build_consolidator_prompt(
    analises: list[AnaliseProcesso],
    metadata: dict
) -> str:
    """
    Constroi o prompt para o Agente Consolidador.

    Args:
        analises: Lista de analises dos processos
        metadata: Metadados da sessao (turma, data, etc.)

    Returns:
        Prompt completo para o consolidador
    """
    turma = metadata.get("turma", "Nao informada")
    sessao = metadata.get("sessao", "Nao informada")
    gabinete = metadata.get("gabinete", "")

    # Serializar analises para o prompt
    analises_json = []
    for a in analises:
        analises_json.append({
            "processo_numero": a.processo_numero,
            "processo_ordem": a.processo_ordem,
            "tema_central": a.tema_central,
            "alerta": a.alerta.value,
            "motivo_alerta": a.motivo_alerta,
            "precedentes": [p.model_dump() for p in a.precedentes_relevantes],
            "flags": a.flags_sensibilidade,
            "recomendacao": a.recomendacao
        })

    import json
    analises_str = json.dumps(analises_json, ensure_ascii=False, indent=2)

    return f'''Voce e um agente consolidador responsavel por gerar o relatorio final de analise da lista de julgamento.

## Dados da Sessao

- **Turma**: {turma}
- **Sessao**: {sessao}
- **Gabinete**: {gabinete}
- **Total de Processos**: {len(analises)}

## Analises Recebidas

{analises_str}

## Sua Tarefa

Gere um relatorio em Markdown seguindo EXATAMENTE este formato:

```markdown
# Analise da Lista de Julgamento
## Sessao: {sessao} | {turma} | {gabinete}
## Total: X processos | Y alertas vermelhos | Z amarelos | W verdes

---

## ATENCAO IMEDIATA (Y processos)

[Para cada processo VERMELHO, incluir:]

### N. Processo XXXXXXX-XX.XXXX.X.XX.XXXX
**Tema**: [tema central]
**Alerta**: [motivo do alerta]
**Situacao**: [explicacao detalhada]
**Precedentes**: [lista dos precedentes relevantes]
**Recomendacao**: [recomendacao especifica]

---

---

## ANALISE RECOMENDADA (Z processos)

[Para cada processo AMARELO, mesmo formato]

---

## SEM ALERTAS (W processos)

| # | Processo | Tema |
|---|----------|------|
| 1 | numero | tema |
...
```

## Regras

1. Ordene os processos por ORDEM ORIGINAL dentro de cada categoria
2. Para VERMELHOS e AMARELOS: detalhe completo
3. Para VERDES: apenas tabela resumida
4. Use linguagem clara e objetiva
5. Destaque visualmente as informacoes criticas

Gere o relatorio completo em Markdown:
'''


def build_conversation_prompt(
    pergunta: str,
    contexto_sessao: dict
) -> str:
    """
    Constroi o prompt para o modo conversa interativo.

    Args:
        pergunta: Pergunta do usuario
        contexto_sessao: Contexto completo da sessao

    Returns:
        Prompt para responder a pergunta
    """
    import json

    processos_resumo = []
    for p in contexto_sessao.get("processos", []):
        processos_resumo.append({
            "ordem": p.get("ordem"),
            "numero": p.get("numero"),
            "tema": p.get("tema_central", ""),
            "alerta": p.get("alerta", "")
        })

    return f'''Voce e um assistente juridico em modo conversa interativo.

## Contexto da Sessao

Uma lista de julgamento foi analisada e o relatorio foi gerado. Agora o usuario quer aprofundar em aspectos especificos.

**Sessao**: {contexto_sessao.get("sessao", "")}
**Turma**: {contexto_sessao.get("turma", "")}
**Total de Processos**: {len(processos_resumo)}

## Processos Analisados (resumo)

{json.dumps(processos_resumo, ensure_ascii=False, indent=2)}

## Analises Completas Disponiveis

Voce tem acesso as analises completas de cada processo. Use-as para responder as perguntas.

## Capacidades

Voce pode:
- Explicar qualquer analise em detalhes
- Executar NOVAS pesquisas usando as ferramentas MCP (BNP, JULIA, CJF)
- Comparar processos entre si
- Filtrar e agrupar por tema/tipo/alerta
- Buscar fundamentacao para posicao divergente
- Gerar relatorios parciais

## Pergunta do Usuario

{pergunta}

## Instrucoes

1. Se a pergunta mencionar "processo X" ou "processo numero X", identifique o processo correto
2. Se precisar de mais informacoes, use as ferramentas MCP
3. Responda de forma clara e objetiva
4. Cite precedentes especificos quando relevante
'''
