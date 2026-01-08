# Lista TRF - Analisador de Listas de Julgamento

Sistema para analise de listas de julgamento do TRF5, com interface web para gerenciamento e integracao com Claude Code para analise automatizada de precedentes.

## Visao Geral

O sistema oferece duas formas de uso:

1. **Interface Web (app/)** - Kanban visual para importar, organizar e revisar processos
2. **Sistema Agentico (src/)** - Analise automatizada via Claude Code com pesquisa de precedentes

```
                    ┌─────────────────────────────────────┐
                    │         LISTA DE JULGAMENTO         │
                    │           (DOCX/PDF/TXT)            │
                    └─────────────────┬───────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │                                               │
              ▼                                               ▼
┌─────────────────────────────┐             ┌─────────────────────────────┐
│     INTERFACE WEB (app/)    │             │  SISTEMA AGENTICO (src/)    │
│                             │             │                             │
│  - Importar lista           │             │  - Analise automatizada     │
│  - Kanban visual            │             │  - Pesquisa BNP/JULIA/CJF   │
│  - Drag & drop              │             │  - Classificacao de risco   │
│  - Gerar relatorio DOCX     │             │  - Relatorio consolidado    │
└─────────────────────────────┘             └─────────────────────────────┘
              │                                               │
              └───────────────────────┬───────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │           processos/                │
                    │  01-a-analisar/                     │
                    │  02-de-acordo/                      │
                    │  03-destacar/                       │
                    └─────────────────────────────────────┘
```

## Inicio Rapido

### Opcao 1: Interface Web

```bash
# Windows - duplo clique ou execute:
iniciar.bat

# Ou manualmente:
pip install -r requirements.txt
uvicorn app.main:app --port 5002

# Acesse: http://127.0.0.1:5002
```

### Opcao 2: Claude Code (Analise Automatizada)

```bash
# Na pasta do projeto, execute:
claude "analisa lista: caminho/para/lista.docx"
```

## Estrutura do Projeto

```
lista-trf/
├── app/                    # Interface Web (FastAPI)
│   ├── main.py            # Servidor e endpoints
│   ├── config.py          # Configuracoes
│   ├── file_manager.py    # Gerenciamento de arquivos
│   ├── parser.py          # Parser de listas
│   └── docx_generator.py  # Gerador de relatorios Word
│
├── src/lista_trf/         # Sistema Agentico (Claude Code)
│   ├── extractor.py       # Extracao de documentos
│   ├── schemas.py         # Modelos Pydantic
│   ├── prompts.py         # Templates de prompts
│   ├── report.py          # Geracao de relatorio
│   ├── main.py            # Modulo principal
│   └── agents/            # Agentes
│       ├── analyst.py     # Agente analista
│       └── orchestrator.py# Orquestrador
│
├── static/                # Frontend
│   ├── index.html         # Interface Kanban
│   ├── style.css          # Estilos
│   └── app.js             # JavaScript
│
├── processos/             # Dados dos processos
│   ├── 01-a-analisar/     # Processos pendentes
│   ├── 02-de-acordo/      # Processos aprovados
│   └── 03-destacar/       # Processos para destaque
│
├── output/                # Relatorios gerados
├── listas/                # Listas importadas
├── arquivados/            # Processos arquivados
│
├── iniciar.bat            # Script para iniciar (Windows)
├── requirements.txt       # Dependencias Python
├── CLAUDE.md              # Instrucoes para Claude Code
└── README.md              # Este arquivo
```

## Interface Web

### Funcionalidades

| Funcao | Descricao |
|--------|-----------|
| **Importar** | Upload de DOCX/PDF/TXT ou colar texto |
| **Kanban** | Arrastar processos entre colunas |
| **Preview** | Visualizar ementa e analise lado a lado |
| **Risco** | Classificar como verde/amarelo/vermelho |
| **Busca** | Filtrar por numero ou conteudo |
| **Relatorio** | Gerar documento Word comparativo |
| **Arquivar** | Mover todos para pasta de arquivo |

### Estados do Fluxo

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ A Analisar  │───▶│  De Acordo  │    │  Destacar   │
│             │    │             │    │             │
│ Processos   │    │ Sem alertas │    │ Divergentes │
│ pendentes   │    │ aprovados   │    │ ou duvidosos│
└─────────────┘    └─────────────┘    └─────────────┘
```

### API Endpoints

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/` | Pagina principal |
| GET | `/api/processos` | Lista todos os processos |
| GET | `/api/processo/{estado}/{numero}` | Detalhes de um processo |
| POST | `/api/mover` | Move processo entre estados |
| POST | `/api/risco` | Atualiza nivel de risco |
| POST | `/api/analise` | Salva analise do processo |
| POST | `/api/importar/arquivo` | Importa arquivo de lista |
| POST | `/api/importar/texto` | Importa texto colado |
| GET | `/api/estatisticas` | Estatisticas gerais |
| GET | `/api/relatorio` | Gera relatorio DOCX |
| POST | `/api/arquivar` | Arquiva todos os processos |

## Sistema Agentico (Claude Code)

### Ferramentas MCP Disponiveis

| Ferramenta | Base | Uso |
|------------|------|-----|
| `mcp__bnp-api__buscar_precedentes` | BNP | Temas vinculantes STF/STJ |
| `mcp__julia-trf5__buscar_julia` | JULIA | Jurisprudencia TRF5 |
| `mcp__cjf-jurisprudencia__buscar_jurisprudencia_cjf` | CJF | Base unificada |

### Niveis de Alerta

| Nivel | Significado | Criterio |
|-------|-------------|----------|
| **VERMELHO** | Atencao Imediata | Divergencia com precedente vinculante |
| **AMARELO** | Analise Recomendada | Tema sensivel ou jurisprudencia em evolucao |
| **VERDE** | Sem Alertas | Alinhado com jurisprudencia consolidada |

### Fluxo de Analise Automatizada

```
1. Claude extrai processos do documento
2. Para cada processo, lanca subagente analista
3. Subagentes pesquisam precedentes (BNP, JULIA, CJF)
4. Comparam ementa com jurisprudencia
5. Classificam risco (verde/amarelo/vermelho)
6. Geram relatorio consolidado
7. Entram em modo conversa interativo
```

## Estrutura de um Processo

```
processos/01-a-analisar/0800307-06.2025.4.05.8103/
├── ementa.md      # Texto da ementa original
├── analise.md     # Analise gerada (opcional)
└── meta.json      # Metadados do processo
```

### meta.json

```json
{
  "numero": "0800307-06.2025.4.05.8103",
  "tipo": "APELACAO CIVEL",
  "tema": "ADMINISTRATIVO. PASEP. PRESCRICAO.",
  "tema_vinculante": "Tema 1066/STF",
  "risco": "verde",
  "ordem": 1
}
```

## Requisitos

- Python 3.11+
- Dependencias: `pip install -r requirements.txt`
  - FastAPI
  - uvicorn
  - python-docx
  - pydantic
  - PyMuPDF (para PDF)

## Licenca

Uso interno - TRF5
