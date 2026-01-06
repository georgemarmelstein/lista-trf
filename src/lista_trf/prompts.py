"""Templates de prompts para os agentes do sistema."""

from lista_trf.schemas import Processo, AnaliseProcesso


def build_analyst_prompt(processo: Processo) -> str:
    """
    Constrói o prompt para o Agente Analista.

    Args:
        processo: Processo a ser analisado

    Returns:
        Prompt completo para o agente
    """
    turma = processo.metadata.get("turma", "Não informada")

    return f'''Você é um agente analista jurídico especializado em direito previdenciário e administrativo federal.

## Sua Tarefa

Analisar o processo abaixo e verificar se a posição adotada na ementa está alinhada com a jurisprudência consolidada.

## Processo para Análise

**Número**: {processo.numero}
**Tipo**: {processo.tipo_acao or "Não informado"}
**Turma**: {turma}
**Partes**: {processo.partes or "Não informadas"}

**EMENTA**:
{processo.ementa}

## Instruções de Análise

### Fase 1: Classificação
1. Identifique o TEMA JURÍDICO CENTRAL da ementa (ex: "prescrição PASEP", "aposentadoria especial ruído")
2. Identifique se há FLAGS DE SENSIBILIDADE:
   - Improbidade administrativa
   - Questões ambientais
   - Ações civis públicas
   - Comunidades tradicionais
   - Minorias
   - Complexidade fática elevada
3. Avalie a COMPLEXIDADE FÁTICA (baixa/média/alta)

### Fase 2: Pesquisa de Precedentes
Use as ferramentas MCP para pesquisar:

1. **BNP (Banco Nacional de Precedentes)**:
   - Use `mcp__bnp-api__buscar_precedentes` com query apropriada
   - Busque Temas de Repercussão Geral (STF) e Recursos Repetitivos (STJ)
   - Busque Súmulas Vinculantes relacionadas

2. **JULIA (TRF5)**:
   - Use `mcp__julia-trf5__buscar_julia` para jurisprudência do TRF5
   - IMPORTANTE: Filtre por `orgao_julgador` = "{turma}" para ver precedentes da própria turma
   - Verifique também outras turmas para identificar divergências

3. **CJF (Base Unificada)**:
   - Use `mcp__cjf-jurisprudencia__buscar_jurisprudencia_cjf` se necessário
   - Útil para comparar posições entre TRFs

### Fase 3: Análise Comparativa
Compare a posição da ementa com os precedentes encontrados:

1. **ALERTA VERMELHO** (Atenção Imediata):
   - Divergência direta com precedente vinculante (Tema STF/STJ vigente)
   - Contradição com Súmula Vinculante
   - Posição contrária à jurisprudência pacífica da própria turma

2. **ALERTA AMARELO** (Análise Recomendada):
   - Tema sensível (improbidade, ambiental, minorias, etc.)
   - Jurisprudência em evolução ou pendente de modulação
   - Divergência entre turmas do TRF5
   - Complexidade fática elevada
   - Questão jurídica inédita

3. **ALERTA VERDE** (Sem Alertas):
   - Ementa alinhada com jurisprudência consolidada
   - Tema pacificado
   - Caso padrão sem peculiaridades

## Formato de Resposta

Responda EXCLUSIVAMENTE com um JSON válido no seguinte formato:

```json
{{
  "processo_numero": "{processo.numero}",
  "processo_ordem": {processo.ordem},
  "tema_central": "descrição do tema em poucas palavras",
  "alerta": "vermelho|amarelo|verde",
  "motivo_alerta": "explicação clara e concisa do motivo do alerta",
  "precedentes_relevantes": [
    {{
      "identificador": "Tema XXX/STJ ou Súmula XXX",
      "fonte": "BNP|JULIA|CJF",
      "tese": "texto resumido da tese",
      "status": "vigente|superado|pendente",
      "alinhamento": "compatível|divergente|parcial",
      "observação": "observação relevante se houver"
    }}
  ],
  "flags_sensibilidade": ["flag1", "flag2"],
  "complexidade_fatica": "baixa|média|alta",
  "recomendação": "recomendação específica de ação",
  "analise_completa": "texto detalhado da análise para referência futura"
}}
```

IMPORTANTE: Retorne APENAS o JSON, sem texto adicional antes ou depois.
'''


def build_consolidator_prompt(
    analises: list[AnaliseProcesso],
    metadata: dict
) -> str:
    """
    Constrói o prompt para o Agente Consolidador.

    Args:
        analises: Lista de análises dos processos
        metadata: Metadados da sessão (turma, data, etc.)

    Returns:
        Prompt completo para o consolidador
    """
    turma = metadata.get("turma", "Não informada")
    sessao = metadata.get("sessao", "Não informada")
    gabinete = metadata.get("gabinete", "")

    # Serializar análises para o prompt
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

    return f'''Você é um agente consolidador responsável por gerar o relatório final de análise da lista de julgamento.

## Dados da Sessão

- **Turma**: {turma}
- **Sessão**: {sessao}
- **Gabinete**: {gabinete}
- **Total de Processos**: {len(analises)}

## Análises Recebidas

{analises_str}

## Sua Tarefa

Gere um relatório em Markdown seguindo EXATAMENTE este formato:

```markdown
# Análise da Lista de Julgamento
## Sessão: {sessao} | {turma} | {gabinete}
## Total: X processos | Y alertas vermelhos | Z amarelos | W verdes

---

## ATENÇÃO IMEDIATA (Y processos)

[Para cada processo VERMELHO, incluir:]

### N. Processo XXXXXXX-XX.XXXX.X.XX.XXXX
**Tema**: [tema central]
**Alerta**: [motivo do alerta]
**Situação**: [explicação detalhada]
**Precedentes**: [lista dos precedentes relevantes]
**Recomendação**: [recomendação específica]

---

---

## ANÁLISE RECOMENDADA (Z processos)

[Para cada processo AMARELO, mesmo formato]

---

## SEM ALERTAS (W processos)

| # | Processo | Tema |
|---|----------|------|
| 1 | número | tema |
...
```

## Regras

1. Ordene os processos por ORDEM ORIGINAL dentro de cada categoria
2. Para VERMELHOS e AMARELOS: detalhe completo
3. Para VERDES: apenas tabela resumida
4. Use linguagem clara e objetiva
5. Destaque visualmente as informações críticas

Gere o relatório completo em Markdown:
'''


def build_conversation_prompt(
    pergunta: str,
    contexto_sessao: dict
) -> str:
    """
    Constrói o prompt para o modo conversa interativo.

    Args:
        pergunta: Pergunta do usuário
        contexto_sessao: Contexto completo da sessão

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

    return f'''Você é um assistente jurídico em modo conversa interativo.

## Contexto da Sessão

Uma lista de julgamento foi analisada e o relatório foi gerado. Agora o usuário quer aprofundar em aspectos específicos.

**Sessão**: {contexto_sessao.get("sessao", "")}
**Turma**: {contexto_sessao.get("turma", "")}
**Total de Processos**: {len(processos_resumo)}

## Processos Analisados (resumo)

{json.dumps(processos_resumo, ensure_ascii=False, indent=2)}

## Análises Completas Disponíveis

Você tem acesso às análises completas de cada processo. Use-as para responder às perguntas.

## Capacidades

Você pode:
- Explicar qualquer análise em detalhes
- Executar NOVAS pesquisas usando as ferramentas MCP (BNP, JULIA, CJF)
- Comparar processos entre si
- Filtrar e agrupar por tema/tipo/alerta
- Buscar fundamentação para posição divergente
- Gerar relatórios parciais

## Pergunta do Usuário

{pergunta}

## Instruções

1. Se a pergunta mencionar "processo X" ou "processo número X", identifique o processo correto
2. Se precisar de mais informações, use as ferramentas MCP
3. Responda de forma clara e objetiva
4. Cite precedentes específicos quando relevante
'''
