# Sistema de Analise de Listas de Julgamento - TRF5

## Visao Geral

Sistema com dois componentes principais:

1. **Interface Web (app/)** - Kanban visual para gerenciamento de processos
2. **Sistema Agentico (src/)** - Analise automatizada via Claude Code

### Iniciar Interface Web

```bash
# Windows:
iniciar.bat

# Ou:
uvicorn app.main:app --port 5002
# Acesse: http://127.0.0.1:5002
```

## Como Usar - Analise Automatizada

### Comando Principal

Quando o usuario pedir para analisar uma lista:

```
analisa lista: <caminho_do_arquivo.docx>
```

### Fluxo de Analise

1. **Extrair processos**:
```python
from lista_trf.main import prepare_analysis, generate_analyst_prompts

data = prepare_analysis(r"caminho/arquivo.docx")
prompts = generate_analyst_prompts(data['processos'])
```

2. **Analisar em paralelo**: Para cada processo, lance subagente com Task tool:
   - `subagent_type`: "general-purpose"
   - `run_in_background`: true
   - `prompt`: prompt especifico do processo

3. **Coletar resultados**: Use TaskOutput para obter analises

4. **Gerar relatorio**:
```python
from lista_trf.report import save_report
from lista_trf.schemas import RelatorioConsolidado

relatorio = RelatorioConsolidado(...)
save_report(relatorio, "output/relatorio.md")
```

5. **Modo conversa**: Apos relatorio, responder perguntas do usuario

### Importante: Arquivos Temporarios

**NAO criar arquivos temporarios na raiz do projeto.** Os prompts devem ser:
- Mantidos em memoria (variaveis Python)
- Passados diretamente aos subagentes via parametro `prompt`
- Se necessario salvar, usar pasta `temp/` ou sistema temporario do OS

## Ferramentas MCP Disponiveis

### BNP (Banco Nacional de Precedentes)
- `mcp__bnp-api__buscar_precedentes`: Busca temas vinculantes
- Sintaxe: `+termo -excluir "frase exata"`
- Tipos: RG (Repercussao Geral), RR (Repetitivos), SV (Sumula Vinculante)

### JULIA (TRF5)
- `mcp__julia-trf5__buscar_julia`: Jurisprudencia TRF5
- `mcp__julia-trf5__relatorio_segundo_grau`: Acordaos com ementas
- Sintaxe: `termo e outro ou (alternativa)`
- Operadores (minusculo): `e`, `ou`, `nao`, `prox`, `adj`
- Filtros: `orgao_julgador`, `relator`

### CJF (Base Unificada)
- `mcp__cjf-jurisprudencia__buscar_jurisprudencia_cjf`: STF, STJ, TRFs
- Sintaxe: `termo E outro OU (alt)[EMEN]`
- Operadores (MAIUSCULO): `E`, `OU`, `NAO`, `ADJ`, `PROX`, `COM`, `MESMO`
- Campos: `[EMEN]`, `[REL]`, `[TRIB]`, `[ORGA]`, `[INDE]`

## Niveis de Alerta

| Nivel | Cor | Criterio |
|-------|-----|----------|
| **VERMELHO** | Atencao Imediata | Divergencia com precedente vinculante |
| **AMARELO** | Analise Recomendada | Tema sensivel, jurisprudencia em evolucao |
| **VERDE** | Sem Alertas | Alinhado com jurisprudencia consolidada |

## Estrutura do Projeto

```
lista-trf/
├── app/                    # Interface Web (FastAPI)
│   ├── main.py            # Servidor e endpoints API
│   ├── config.py          # Configuracoes (ESTADOS, PATHS)
│   ├── file_manager.py    # CRUD de processos
│   ├── parser.py          # Parser de listas (DOCX/PDF/TXT)
│   └── docx_generator.py  # Gerador de relatorios Word
│
├── src/lista_trf/         # Sistema Agentico
│   ├── extractor.py       # Extracao de documentos Word
│   ├── schemas.py         # Modelos Pydantic
│   ├── prompts.py         # Templates de prompts
│   ├── report.py          # Geracao de relatorio Markdown
│   ├── main.py            # Modulo principal
│   └── agents/
│       ├── analyst.py     # Agente analista (prompt)
│       └── orchestrator.py # Orquestrador (coordenacao)
│
├── static/                # Frontend HTML/CSS/JS
│   ├── index.html         # Interface Kanban
│   ├── style.css          # Estilos (tema claro/escuro)
│   └── app.js             # Logica do frontend
│
├── processos/             # Dados dos processos
│   ├── 01-a-analisar/     # Processos pendentes de analise
│   ├── 02-de-acordo/      # Processos aprovados
│   └── 03-destacar/       # Processos para destaque
│
├── output/                # Relatorios gerados (.md, .docx)
├── listas/                # Arquivos de listas importadas
├── arquivados/            # Processos arquivados
│
├── iniciar.bat            # Script Windows para iniciar servidor
├── requirements.txt       # Dependencias Python
├── analyze_list.py        # Entry point CLI
└── CLAUDE.md              # Este arquivo
```

## Estrutura de um Processo

Cada processo e uma pasta em `processos/{estado}/{numero}/`:

```
processos/01-a-analisar/0800307-06.2025.4.05.8103/
├── ementa.md      # Texto da ementa original
├── analise.md     # Analise comparativa (se existir)
└── meta.json      # Metadados
```

### meta.json

```json
{
  "numero": "0800307-06.2025.4.05.8103",
  "tipo": "APELACAO CIVEL",
  "tema": "ADMINISTRATIVO. PASEP.",
  "tema_vinculante": "Tema 1066/STF",
  "risco": "verde",
  "ordem": 1
}
```

## API da Interface Web

| Metodo | Endpoint | Uso |
|--------|----------|-----|
| GET | `/api/processos` | Listar todos |
| GET | `/api/processo/{estado}/{numero}` | Detalhes |
| POST | `/api/mover` | Mover entre estados |
| POST | `/api/risco` | Atualizar risco |
| POST | `/api/analise` | Salvar analise |
| POST | `/api/importar/arquivo` | Upload de lista |
| GET | `/api/relatorio` | Gerar DOCX |

## Dicas para Analise

1. **Identificar tema vinculante primeiro**: Se o processo menciona "Tema XXX", busque diretamente no BNP
2. **Filtrar por turma**: Use `orgao_julgador` no JULIA para ver precedentes da mesma turma
3. **Verificar divergencias**: Compare posicao entre turmas do TRF5
4. **Temas sensiveis**: Improbidade, ambiental, minorias sempre amarelo minimo
