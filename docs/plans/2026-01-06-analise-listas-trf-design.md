# Design: Sistema Agêntico para Análise de Listas de Julgamento

**Data**: 2026-01-06
**Projeto**: lista-trf
**Status**: Aprovado para implementação

---

## 1. Visão Geral

### 1.1 Problema

Gabinetes do TRF5 recebem semanalmente listas de julgamento com 50-100 processos de outros gabinetes. Cada processo contém uma ementa que propõe uma decisão. Atualmente, a análise de compatibilidade dessas ementas com a jurisprudência consolidada é manual e demorada.

### 1.2 Solução

Sistema agêntico que analisa automaticamente cada processo da lista, pesquisa precedentes em múltiplas bases (BNP, TRF5/JULIA, CJF) e gera relatório consolidado destacando:

1. **Incompatibilidades jurisprudenciais**: quando a ementa diverge de precedentes vinculantes ou jurisprudência consolidada
2. **Casos sensíveis/complexos**: processos que merecem análise especial por sua natureza ou complexidade

### 1.3 Características Principais

- **100% agêntico**: todo processamento usa LLM para interpretar e analisar (sem regex ou heurísticas)
- **Paralelizado**: múltiplos agentes analisam processos simultaneamente
- **Interativo**: após relatório, permite aprofundar em casos específicos via conversa

---

## 2. Arquitetura Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                     ENTRADA                                      │
│            Documento Word/PDF (Lista de Julgamento)              │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AGENTE ORQUESTRADOR                            │
│         Extrai processos → Distribui → Coleta resultados         │
└───────┬─────────┬─────────┬─────────┬─────────┬─────────────────┘
        │         │         │         │         │
        ▼         ▼         ▼         ▼         ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│ Agente    │ │ Agente    │ │ Agente    │ │ Agente    │  ...
│ Analista  │ │ Analista  │ │ Analista  │ │ Analista  │
│ Proc. 1   │ │ Proc. 2   │ │ Proc. 3   │ │ Proc. 4   │
└─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
      │             │             │             │
      └──────────────┴──────────────┴─────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AGENTE CONSOLIDADOR                            │
│        Recebe análises → Gera relatório visual unificado         │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SAÍDA                                     │
│              Relatório Markdown + Modo Conversa Ativo            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Componentes

| Componente | Responsabilidade |
|------------|------------------|
| **Agente Orquestrador** | Coordena fluxo, extrai processos, distribui trabalho, coleta resultados |
| **Agentes Analistas** | Analisam cada processo individualmente (N instâncias em paralelo) |
| **Agente Consolidador** | Unifica análises em relatório visual priorizado |
| **Modo Conversa** | Interface interativa para aprofundar em casos específicos |

---

## 3. Agente Orquestrador

### 3.1 Responsabilidades

O Agente Orquestrador é o ponto de entrada do sistema e coordena todo o fluxo de forma agêntica.

### 3.2 Fases de Operação

#### Fase 1: Ingestão do Documento

1. Recebe caminho do arquivo (Word/PDF)
2. Lê e interpreta a estrutura do documento
3. Segmenta em processos individuais
4. Estrutura cada processo em formato padronizado

**Estrutura de processo extraído**:
```json
{
  "ordem": 1,
  "numero": "0800307-06.2025.4.05.8103",
  "tipo_acao": "Apelação Cível",
  "partes": {
    "apelante": "Francisca Rodrigues Cardoso",
    "apelado": "União Federal, Banco do Brasil"
  },
  "ementa_completa": "ADMINISTRATIVO. PASEP. PRESCRIÇÃO...",
  "metadata": {
    "turma": "4ª Turma",
    "gabinete": "Des. Fernando Braga",
    "sessao": "09/12/2025"
  }
}
```

#### Fase 2: Distribuição Paralela

1. Decide quantos agentes lançar por lote (5-10 simultâneos)
2. Prioriza processos que parecem mais complexos
3. Balanceia carga (ementas longas vs curtas)
4. Lança agentes analistas em paralelo usando a ferramenta Task

#### Fase 3: Coleta e Tratamento de Falhas

1. Monitora progresso de cada agente
2. Trata falhas:
   - **API indisponível**: relança com backoff ou marca para análise manual
   - **Ementa ambígua**: inclui como "análise inconclusiva"
   - **Tema inédito**: sinaliza como caso especial
3. Coleta todas as análises concluídas
4. Passa ao Agente Consolidador

---

## 4. Agente Analista

### 4.1 Responsabilidades

Cada Agente Analista recebe um único processo e executa análise completa de forma autônoma.

### 4.2 Fases de Análise

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   FASE 1      │     │   FASE 2      │     │   FASE 3      │
│  Classificar  │────▶│   Pesquisar   │────▶│   Comparar    │
└───────────────┘     └───────────────┘     └───────────────┘
```

#### Fase 1: Classificação (Agêntica)

O agente lê a ementa e compreende:
- Tema jurídico central (ex: "prescrição PASEP", "licença-prêmio")
- Tipo de ação e natureza do pedido
- Partes envolvidas e contexto
- Flags de sensibilidade (improbidade, ambiental, minorias, etc.)
- Nível de complexidade fática

#### Fase 2: Pesquisa de Precedentes

Chamadas paralelas às APIs MCP:

| Ferramenta | Base | Objetivo |
|------------|------|----------|
| `mcp__bnp-api__buscar_precedentes` | BNP | Temas vinculantes STF/STJ, Súmulas |
| `mcp__julia-trf5__buscar_julia` | JULIA | Jurisprudência TRF5 + filtro pela turma |
| `mcp__cjf-jurisprudencia__buscar_jurisprudencia_cjf` | CJF | Base unificada (STF, STJ, TRFs) |

O agente formula as queries de pesquisa baseado no seu entendimento do caso.

#### Fase 3: Análise Comparativa (Agêntica)

O agente raciocina sobre os resultados:
1. Compara tese da ementa com precedentes encontrados
2. Identifica alinhamento, divergência ou lacuna
3. Avalia hierarquia de precedentes:
   - Precedentes vinculantes (Temas STF/STJ, Súmulas Vinculantes)
   - Precedentes da própria turma
   - Jurisprudência majoritária do TRF5
   - Divergências entre turmas
4. Atribui nível de alerta e justificativa

### 4.3 Output do Agente Analista

```json
{
  "processo": "0800307-06.2025.4.05.8103",
  "tema_central": "Prescrição PASEP - termo inicial",
  "alerta": "verde|amarelo|vermelho",
  "motivo_alerta": "Descrição da incompatibilidade ou peculiaridade",
  "precedentes_relevantes": [
    {
      "identificador": "Tema 1150/STJ",
      "tese": "...",
      "status": "vigente",
      "alinhamento": "compatível|divergente|parcial"
    }
  ],
  "flags_sensibilidade": ["improbidade", "ambiental", ...],
  "complexidade_fatica": "baixa|média|alta",
  "recomendacao": "Texto com recomendação específica"
}
```

---

## 5. Agente Consolidador

### 5.1 Responsabilidades

Recebe todas as análises individuais e gera relatório visual unificado.

### 5.2 Processo de Consolidação

1. **Agrupa** processos por nível de alerta (vermelho → amarelo → verde)
2. **Prioriza** dentro de cada grupo por relevância/urgência
3. **Gera narrativa** explicativa para cada alerta
4. **Monta relatório** visual estruturado

### 5.3 Critérios de Alerta

#### Alerta Vermelho (Atenção Imediata)
- Divergência direta com precedente vinculante (Tema STF/STJ em vigor)
- Contradição com súmula vinculante
- Posição contrária à jurisprudência pacífica da própria turma

#### Alerta Amarelo (Análise Recomendada)
- Tema sensível (improbidade, ambiental, minorias, comunidades tradicionais)
- Jurisprudência em evolução (tema pendente de modulação)
- Divergência entre turmas do TRF5
- Complexidade fática elevada
- Questão jurídica inédita ou pouco explorada

#### Alerta Verde (Sem Alertas)
- Ementa alinhada com jurisprudência consolidada
- Tema pacificado
- Caso padrão sem peculiaridades

---

## 6. Formato do Relatório

```markdown
# Análise da Lista de Julgamento
## Sessão: 09/12/2025 | 4ª Turma | GAB. Des. Fernando Braga
## Total: 87 processos | 3 alertas vermelhos | 8 amarelos | 76 verdes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ATENÇÃO IMEDIATA (3 processos)

### 1. Processo 0801234-56.2024.4.05.8100
**Tema**: Aposentadoria especial - agente nocivo ruído
**Alerta**: Divergência com Tema 1083/STJ
**Situação**: A ementa aplica limite de 85dB, mas o Tema 1083
fixou 90dB para período anterior a 2003.
**Precedentes encontrados**: [lista]
**Recomendação**: Verificar período de exposição do autor

---

### 2. Processo ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ANÁLISE RECOMENDADA (8 processos)

### 1. Processo 0807777-88.2024.4.05.8300
**Tema**: Improbidade administrativa - prescrição intercorrente
**Alerta**: Tema sensível + jurisprudência em evolução
**Situação**: Tema 1199/STF ainda pendente de modulação
**Recomendação**: Acompanhar evolução do precedente

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## SEM ALERTAS (76 processos)

| # | Processo | Tema |
|---|----------|------|
| 1 | 0800307-06.2025.4.05.8103 | PASEP - prescrição |
| 2 | 0007508-25.2015.4.05.8300 | Embargos - honorários |
| ... | ... | ... |
```

---

## 7. Modo Conversa Interativo

### 7.1 Contexto Preservado

Após geração do relatório, o sistema mantém em memória:
- Lista original (todos os processos estruturados)
- Todas as análises individuais dos agentes
- Precedentes encontrados para cada processo
- Relatório gerado
- Metadados (turma, sessão, gabinete)

### 7.2 Tipos de Interação

| Tipo | Exemplo de Pergunta |
|------|---------------------|
| **Aprofundar processo** | "Me explica melhor o problema do processo 3" |
| **Comparar processos** | "Os processos 5 e 6 parecem iguais, qual a diferença?" |
| **Pesquisa adicional** | "Busca mais jurisprudência da 3ª Turma sobre licença-prêmio" |
| **Fundamentação divergente** | "Se eu divergir no processo 7, quais precedentes posso usar?" |
| **Análise temática** | "Quantos processos tratam de prescrição?" |
| **Exportar/Refinar** | "Gera resumo só dos processos de improbidade" |

### 7.3 Capacidades

**Pode fazer**:
- Explicar qualquer análise em mais detalhes
- Executar novas pesquisas (BNP, JULIA, CJF)
- Comparar processos entre si
- Filtrar e agrupar por tema/tipo/alerta
- Buscar fundamentação para posição divergente
- Gerar relatórios parciais/customizados
- Responder dúvidas sobre precedentes específicos
- Atualizar análise com informação nova

**Limitações**:
- Não acessa o processo completo (apenas ementa da lista)
- Não modifica documentos externos
- Não tem acesso ao PJe ou sistemas internos do TRF

---

## 8. Ferramentas MCP Utilizadas

### 8.1 Pesquisa de Precedentes

| Ferramenta | Sintaxe | Uso |
|------------|---------|-----|
| `mcp__bnp-api__buscar_precedentes` | `+termo -excluir "frase exata"` | Temas vinculantes, RG, RR, Súmulas |
| `mcp__bnp-api__gerar_relatorio_precedentes` | Mesma sintaxe | Relatório formatado |

### 8.2 Jurisprudência TRF5 (JULIA)

| Ferramenta | Sintaxe | Uso |
|------------|---------|-----|
| `mcp__julia-trf5__buscar_julia` | `termo e outro ou (alternativa)` | Busca geral |
| `mcp__julia-trf5__relatorio_segundo_grau` | Mesma sintaxe + filtros | Acórdãos com ementas |
| `mcp__julia-trf5__relatorio_primeiro_grau` | Mesma sintaxe | Sentenças por seção |

**Filtros úteis**: `orgao_julgador` (turma), `relator`, `tipos_documento`

### 8.3 Jurisprudência Unificada (CJF)

| Ferramenta | Sintaxe | Uso |
|------------|---------|-----|
| `mcp__cjf-jurisprudencia__buscar_jurisprudencia_cjf` | `termo E outro OU (alt)[EMEN]` | Base completa |
| `mcp__cjf-jurisprudencia__gerar_relatorio_cjf` | Mesma sintaxe | Relatório formatado |

**Operadores**: `E`, `OU`, `NAO`, `ADJ[n]`, `PROX[n]`, `COM`, `MESMO`
**Campos**: `[EMEN]`, `[REL]`, `[TRIB]`, `[ORGA]`, `[INDE]`

---

## 9. Fluxo de Execução

### 9.1 Comando de Execução

```bash
# Uso básico
claude "analisa lista: caminho/para/documento.docx"

# O sistema irá:
# 1. Extrair processos do documento
# 2. Analisar cada um em paralelo
# 3. Gerar relatório
# 4. Entrar em modo conversa
```

### 9.2 Sequência de Operações

```
1. Usuário fornece documento
         │
         ▼
2. Orquestrador extrai processos (python-docx ou similar)
         │
         ▼
3. Orquestrador lança Agentes Analistas em lotes paralelos
         │
         ▼
4. Cada Agente Analista:
   a. Classifica o processo (agêntico)
   b. Pesquisa precedentes (BNP, JULIA, CJF em paralelo)
   c. Compara e atribui alerta (agêntico)
   d. Retorna análise estruturada
         │
         ▼
5. Orquestrador coleta todas as análises
         │
         ▼
6. Consolidador gera relatório priorizado
         │
         ▼
7. Sistema exibe relatório e entra em modo conversa
         │
         ▼
8. Usuário interage até encerrar sessão
```

---

## 10. Considerações de Implementação

### 10.1 Performance

- **Lotes de 5-10 agentes** para não sobrecarregar APIs
- **Timeout por agente**: 60 segundos (configurável)
- **Retry automático**: até 2 tentativas em caso de falha de API

### 10.2 Tratamento de Erros

| Situação | Tratamento |
|----------|------------|
| API timeout | Retry com backoff exponencial |
| Ementa muito curta | Sinaliza como "análise limitada" |
| Tema sem precedentes | Sinaliza como "tema inédito" (amarelo) |
| Documento malformado | Erro com orientação ao usuário |

### 10.3 Armazenamento

- Relatório salvo em `output/YYYY-MM-DD-sessao-turma.md`
- Log de análises em `output/YYYY-MM-DD-sessao-turma.json` (opcional)

---

## 11. Evolução Futura

### 11.1 Possíveis Melhorias

- **Cache de precedentes**: temas recorrentes pré-indexados
- **Histórico de sessões**: comparar listas ao longo do tempo
- **Integração PJe**: acesso ao processo completo (requer autorização)
- **Alertas automáticos**: notificação quando há mudança de entendimento

### 11.2 Fora do Escopo Inicial

- Geração automática de votos
- Modificação de documentos do gabinete
- Acesso a sistemas internos do TRF

---

## 12. Resumo

| Aspecto | Descrição |
|---------|-----------|
| **Input** | Documento Word/PDF com lista de julgamento |
| **Output** | Relatório Markdown + modo conversa |
| **Volume** | 50-100 processos por lista |
| **Frequência** | Semanal, 2-3 dias antes da sessão |
| **Arquitetura** | Agêntica, paralela, interativa |
| **Ferramentas** | BNP, JULIA/TRF5, CJF via MCP |
