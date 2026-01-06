# Sistema Agêntico para Análise de Listas de Julgamento - Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Construir sistema agêntico que analisa listas de julgamento do TRF5, pesquisa precedentes em múltiplas bases (BNP, JULIA, CJF) e gera relatório destacando incompatibilidades jurisprudenciais e casos sensíveis.

**Architecture:** Sistema baseado em Claude Code com três agentes principais: Orquestrador (coordena fluxo e distribui trabalho), Analistas (N instâncias paralelas que analisam cada processo) e Consolidador (gera relatório final). Usa ferramentas MCP já disponíveis para pesquisa de precedentes. Após relatório, entra em modo conversa interativo.

**Tech Stack:** Python 3.11+, python-docx (extração Word), Claude Code (agentes via Task tool), MCP tools (BNP, JULIA, CJF)

---

## Visão Geral das Tarefas

| # | Componente | Descrição |
|---|------------|-----------|
| 1 | Setup | Estrutura do projeto e dependências |
| 2 | Extrator | Leitura e parsing de documentos Word |
| 3 | Esquemas | Estruturas de dados (Pydantic) |
| 4 | Prompts | Templates dos agentes |
| 5 | Agente Analista | Análise individual de processos |
| 6 | Agente Orquestrador | Coordenação e paralelização |
| 7 | Agente Consolidador | Geração do relatório |
| 8 | Modo Conversa | Interface interativa pós-relatório |
| 9 | CLI | Ponto de entrada do sistema |
| 10 | Integração | Teste end-to-end |

---

## Task 1: Setup do Projeto

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/lista_trf/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`

**Step 1: Criar estrutura de diretórios**

```bash
mkdir -p src/lista_trf tests output
```

**Step 2: Criar pyproject.toml**

```toml
[project]
name = "lista-trf"
version = "0.1.0"
description = "Sistema agêntico para análise de listas de julgamento do TRF5"
requires-python = ">=3.11"
dependencies = [
    "python-docx>=1.1.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/lista_trf"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
asyncio_mode = "auto"
```

**Step 3: Criar arquivos __init__.py**

`src/__init__.py`:
```python
```

`src/lista_trf/__init__.py`:
```python
"""Sistema agêntico para análise de listas de julgamento do TRF5."""

__version__ = "0.1.0"
```

`tests/__init__.py`:
```python
```

**Step 4: Criar .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Output
output/
*.log

# OS
.DS_Store
Thumbs.db
```

**Step 5: Instalar dependências**

Run: `pip install -e ".[dev]"`
Expected: Instalação bem-sucedida

**Step 6: Verificar instalação**

Run: `python -c "import lista_trf; print(lista_trf.__version__)"`
Expected: `0.1.0`

**Step 7: Commit**

```bash
git init
git add .
git commit -m "chore: setup inicial do projeto lista-trf"
```

---

## Task 2: Extrator de Documentos Word

**Files:**
- Create: `src/lista_trf/extractor.py`
- Create: `tests/test_extractor.py`

**Step 1: Criar teste do extrator**

`tests/test_extractor.py`:
```python
"""Testes para o extrator de documentos Word."""

import pytest
from pathlib import Path
from lista_trf.extractor import extract_processes_from_docx, ProcessoExtraido


# Fixture com caminho do documento de exemplo
SAMPLE_DOC = Path(r"C:\Users\georg\lista-trf\Lista de Julgamento - GABFBD - Sessão 09.12.2025 - 4ª Turma.docx")


class TestExtractProcesses:
    """Testes de extração de processos."""

    def test_extract_returns_list(self):
        """Extração deve retornar lista de processos."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        result = extract_processes_from_docx(SAMPLE_DOC)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_extract_processo_has_required_fields(self):
        """Cada processo extraído deve ter campos obrigatórios."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        result = extract_processes_from_docx(SAMPLE_DOC)
        processo = result[0]

        assert isinstance(processo, ProcessoExtraido)
        assert processo.numero is not None
        assert processo.ementa is not None

    def test_extract_primeiro_processo_numero(self):
        """Primeiro processo deve ter número correto."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        result = extract_processes_from_docx(SAMPLE_DOC)

        assert result[0].numero == "0800307-06.2025.4.05.8103"

    def test_extract_metadata_sessao(self):
        """Deve extrair metadados da sessão."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        result = extract_processes_from_docx(SAMPLE_DOC)

        # Verifica se algum processo tem metadata
        assert result[0].metadata is not None
        assert "turma" in result[0].metadata or result[0].metadata.get("turma")
```

**Step 2: Rodar teste para verificar que falha**

Run: `pytest tests/test_extractor.py -v`
Expected: FAIL com "ModuleNotFoundError: No module named 'lista_trf.extractor'"

**Step 3: Implementar extrator**

`src/lista_trf/extractor.py`:
```python
"""Extrator de processos de documentos Word (listas de julgamento)."""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from docx import Document


@dataclass
class ProcessoExtraido:
    """Processo extraído do documento."""

    ordem: int
    numero: str
    tipo_acao: Optional[str] = None
    partes: dict = field(default_factory=dict)
    ementa: str = ""
    metadata: dict = field(default_factory=dict)


def extract_processes_from_docx(file_path: Path) -> list[ProcessoExtraido]:
    """
    Extrai processos de um documento Word de lista de julgamento.

    Args:
        file_path: Caminho para o arquivo .docx

    Returns:
        Lista de ProcessoExtraido
    """
    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    # Extrair metadados do cabeçalho
    metadata = _extract_metadata(paragraphs)

    # Identificar e extrair cada processo
    processes = _extract_processes(paragraphs, metadata)

    return processes


def _extract_metadata(paragraphs: list[str]) -> dict:
    """Extrai metadados do cabeçalho do documento."""
    metadata = {}

    for p in paragraphs[:5]:  # Cabeçalho geralmente nas primeiras linhas
        p_upper = p.upper()

        # Turma
        turma_match = re.search(r'(\d+)[ªª]?\s*TURMA', p_upper)
        if turma_match:
            metadata["turma"] = f"{turma_match.group(1)}ª Turma"

        # Sessão
        sessao_match = re.search(r'SESS[ÃA]O[^:]*:\s*(\d{2}/\d{2}/\d{4})', p_upper)
        if sessao_match:
            metadata["sessao"] = sessao_match.group(1)

        # Gabinete
        gab_match = re.search(r'GAB[^\-]*-?\s*(DES\.?\s*[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ\s]+)', p, re.IGNORECASE)
        if gab_match:
            metadata["gabinete"] = gab_match.group(1).strip()

    return metadata


def _extract_processes(paragraphs: list[str], metadata: dict) -> list[ProcessoExtraido]:
    """Extrai lista de processos do documento."""
    processes = []
    current_process = None
    current_text = []
    ordem = 0

    # Padrão para identificar início de novo processo
    # Ex: "1 - 0800307-06.2025.4.05.8103 - APELAÇÃO CÍVEL"
    process_pattern = re.compile(
        r'^(\d+)\s*-\s*(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\s*-\s*(.+)$'
    )

    # Padrão alternativo (número CNJ em linha separada)
    cnj_pattern = re.compile(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})')

    in_ementa = False

    for p in paragraphs:
        # Verificar se é início de novo processo
        match = process_pattern.match(p)

        if match:
            # Salvar processo anterior se existir
            if current_process:
                current_process.ementa = _clean_ementa('\n'.join(current_text))
                processes.append(current_process)

            # Iniciar novo processo
            ordem = int(match.group(1))
            numero = match.group(2)
            tipo_acao = match.group(3).strip()

            current_process = ProcessoExtraido(
                ordem=ordem,
                numero=numero,
                tipo_acao=tipo_acao,
                metadata=metadata.copy()
            )
            current_text = []
            in_ementa = False
            continue

        # Se estamos em um processo, acumular texto
        if current_process:
            # Detectar seção de partes
            if 'APELANTE:' in p.upper() or 'APELADO:' in p.upper():
                _extract_partes(p, current_process)

            # Detectar início da ementa
            if p.upper().strip() == 'EMENTA':
                in_ementa = True
                continue

            # Acumular texto da ementa
            if in_ementa:
                current_text.append(p)

    # Não esquecer o último processo
    if current_process:
        current_process.ementa = _clean_ementa('\n'.join(current_text))
        processes.append(current_process)

    return processes


def _extract_partes(text: str, processo: ProcessoExtraido):
    """Extrai informações das partes do processo."""
    text_upper = text.upper()

    if 'APELANTE:' in text_upper:
        match = re.search(r'APELANTE:\s*(.+?)(?=APELADO|ADVOGADO|$)', text, re.IGNORECASE)
        if match:
            processo.partes['apelante'] = match.group(1).strip()

    if 'APELADO:' in text_upper:
        match = re.search(r'APELADO:\s*(.+?)(?=ADVOGADO|$)', text, re.IGNORECASE)
        if match:
            processo.partes['apelado'] = match.group(1).strip()


def _clean_ementa(text: str) -> str:
    """Limpa e normaliza o texto da ementa."""
    # Remover linhas vazias duplicadas
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line]

    # Juntar em texto único
    return '\n'.join(lines)
```

**Step 4: Rodar testes**

Run: `pytest tests/test_extractor.py -v`
Expected: PASS (todos os testes)

**Step 5: Commit**

```bash
git add src/lista_trf/extractor.py tests/test_extractor.py
git commit -m "feat: extrator de processos de documentos Word"
```

---

## Task 3: Esquemas de Dados (Pydantic)

**Files:**
- Create: `src/lista_trf/schemas.py`
- Create: `tests/test_schemas.py`

**Step 1: Criar teste dos schemas**

`tests/test_schemas.py`:
```python
"""Testes para os esquemas de dados."""

import pytest
from lista_trf.schemas import (
    Processo,
    PrecedenteEncontrado,
    AnaliseProcesso,
    NivelAlerta,
    RelatorioConsolidado
)


class TestProcesso:
    """Testes do schema Processo."""

    def test_processo_criacao_minima(self):
        """Processo pode ser criado com campos mínimos."""
        p = Processo(
            ordem=1,
            numero="0800307-06.2025.4.05.8103",
            ementa="ADMINISTRATIVO. PASEP."
        )
        assert p.numero == "0800307-06.2025.4.05.8103"

    def test_processo_campos_opcionais(self):
        """Campos opcionais têm valores padrão."""
        p = Processo(
            ordem=1,
            numero="0800307-06.2025.4.05.8103",
            ementa="EMENTA"
        )
        assert p.tipo_acao is None
        assert p.partes == {}
        assert p.metadata == {}


class TestAnaliseProcesso:
    """Testes do schema AnaliseProcesso."""

    def test_analise_criacao(self):
        """AnaliseProcesso pode ser criada."""
        analise = AnaliseProcesso(
            processo_numero="0800307-06.2025.4.05.8103",
            tema_central="Prescrição PASEP",
            alerta=NivelAlerta.VERDE,
            motivo_alerta="Alinhado com jurisprudência",
            recomendacao="Sem necessidade de revisão"
        )
        assert analise.alerta == NivelAlerta.VERDE

    def test_nivel_alerta_valores(self):
        """NivelAlerta tem valores corretos."""
        assert NivelAlerta.VERMELHO.value == "vermelho"
        assert NivelAlerta.AMARELO.value == "amarelo"
        assert NivelAlerta.VERDE.value == "verde"


class TestRelatorioConsolidado:
    """Testes do schema RelatorioConsolidado."""

    def test_relatorio_contagem(self):
        """Relatório calcula contagens corretamente."""
        analises = [
            AnaliseProcesso(
                processo_numero="001",
                tema_central="Tema 1",
                alerta=NivelAlerta.VERMELHO,
                motivo_alerta="Divergência",
                recomendacao="Revisar"
            ),
            AnaliseProcesso(
                processo_numero="002",
                tema_central="Tema 2",
                alerta=NivelAlerta.VERDE,
                motivo_alerta="OK",
                recomendacao="Nenhuma"
            ),
        ]

        relatorio = RelatorioConsolidado(
            sessao="09/12/2025",
            turma="4ª Turma",
            gabinete="Des. Fernando Braga",
            total_processos=2,
            analises=analises
        )

        assert relatorio.total_vermelhos == 1
        assert relatorio.total_amarelos == 0
        assert relatorio.total_verdes == 1
```

**Step 2: Rodar teste para verificar que falha**

Run: `pytest tests/test_schemas.py -v`
Expected: FAIL com "ModuleNotFoundError"

**Step 3: Implementar schemas**

`src/lista_trf/schemas.py`:
```python
"""Esquemas de dados para o sistema de análise de listas."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, computed_field


class NivelAlerta(str, Enum):
    """Níveis de alerta para análise de processos."""

    VERMELHO = "vermelho"  # Atenção imediata
    AMARELO = "amarelo"    # Análise recomendada
    VERDE = "verde"        # Sem alertas


class Processo(BaseModel):
    """Processo extraído da lista de julgamento."""

    ordem: int = Field(description="Ordem do processo na lista")
    numero: str = Field(description="Número CNJ do processo")
    tipo_acao: Optional[str] = Field(default=None, description="Tipo de ação")
    partes: dict = Field(default_factory=dict, description="Partes do processo")
    ementa: str = Field(description="Texto completo da ementa")
    metadata: dict = Field(default_factory=dict, description="Metadados (turma, sessão, etc)")


class PrecedenteEncontrado(BaseModel):
    """Precedente encontrado na pesquisa."""

    identificador: str = Field(description="Ex: Tema 1150/STJ, Súmula 123")
    fonte: str = Field(description="BNP, JULIA, CJF")
    tese: str = Field(description="Texto da tese ou súmula")
    status: str = Field(default="vigente", description="vigente, superado, pendente")
    alinhamento: str = Field(description="compativel, divergente, parcial")
    observacao: Optional[str] = Field(default=None, description="Observações adicionais")


class AnaliseProcesso(BaseModel):
    """Resultado da análise de um processo."""

    processo_numero: str = Field(description="Número do processo analisado")
    processo_ordem: int = Field(default=0, description="Ordem na lista")
    tema_central: str = Field(description="Tema jurídico identificado")
    alerta: NivelAlerta = Field(description="Nível de alerta")
    motivo_alerta: str = Field(description="Explicação do alerta")
    precedentes_relevantes: list[PrecedenteEncontrado] = Field(
        default_factory=list,
        description="Precedentes encontrados"
    )
    flags_sensibilidade: list[str] = Field(
        default_factory=list,
        description="Flags: improbidade, ambiental, etc"
    )
    complexidade_fatica: str = Field(
        default="baixa",
        description="baixa, media, alta"
    )
    recomendacao: str = Field(description="Recomendação de ação")
    analise_completa: Optional[str] = Field(
        default=None,
        description="Texto completo da análise para modo conversa"
    )


class RelatorioConsolidado(BaseModel):
    """Relatório consolidado de análise da lista."""

    sessao: str = Field(description="Data da sessão")
    turma: str = Field(description="Turma julgadora")
    gabinete: str = Field(default="", description="Gabinete de origem")
    total_processos: int = Field(description="Total de processos analisados")
    analises: list[AnaliseProcesso] = Field(description="Análises individuais")
    falhas: list[dict] = Field(default_factory=list, description="Processos com falha")

    @computed_field
    @property
    def total_vermelhos(self) -> int:
        """Conta processos com alerta vermelho."""
        return sum(1 for a in self.analises if a.alerta == NivelAlerta.VERMELHO)

    @computed_field
    @property
    def total_amarelos(self) -> int:
        """Conta processos com alerta amarelo."""
        return sum(1 for a in self.analises if a.alerta == NivelAlerta.AMARELO)

    @computed_field
    @property
    def total_verdes(self) -> int:
        """Conta processos com alerta verde."""
        return sum(1 for a in self.analises if a.alerta == NivelAlerta.VERDE)

    @property
    def vermelhos(self) -> list[AnaliseProcesso]:
        """Retorna análises com alerta vermelho."""
        return [a for a in self.analises if a.alerta == NivelAlerta.VERMELHO]

    @property
    def amarelos(self) -> list[AnaliseProcesso]:
        """Retorna análises com alerta amarelo."""
        return [a for a in self.analises if a.alerta == NivelAlerta.AMARELO]

    @property
    def verdes(self) -> list[AnaliseProcesso]:
        """Retorna análises com alerta verde."""
        return [a for a in self.analises if a.alerta == NivelAlerta.VERDE]


class SessaoAnalise(BaseModel):
    """Estado completo de uma sessão de análise (para modo conversa)."""

    processos_originais: list[Processo] = Field(description="Processos extraídos")
    relatorio: RelatorioConsolidado = Field(description="Relatório gerado")
    historico_conversa: list[dict] = Field(
        default_factory=list,
        description="Histórico de perguntas/respostas"
    )
```

**Step 4: Rodar testes**

Run: `pytest tests/test_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/lista_trf/schemas.py tests/test_schemas.py
git commit -m "feat: schemas Pydantic para processos e análises"
```

---

## Task 4: Templates de Prompts dos Agentes

**Files:**
- Create: `src/lista_trf/prompts.py`
- Create: `tests/test_prompts.py`

**Step 1: Criar teste dos prompts**

`tests/test_prompts.py`:
```python
"""Testes para os templates de prompts."""

import pytest
from lista_trf.prompts import (
    build_analyst_prompt,
    build_consolidator_prompt,
    build_conversation_prompt
)
from lista_trf.schemas import Processo, AnaliseProcesso, NivelAlerta


class TestAnalystPrompt:
    """Testes do prompt do agente analista."""

    def test_prompt_contains_processo_info(self):
        """Prompt deve conter informações do processo."""
        processo = Processo(
            ordem=1,
            numero="0800307-06.2025.4.05.8103",
            tipo_acao="Apelação Cível",
            ementa="ADMINISTRATIVO. PASEP. PRESCRIÇÃO.",
            metadata={"turma": "4ª Turma"}
        )

        prompt = build_analyst_prompt(processo)

        assert "0800307-06.2025.4.05.8103" in prompt
        assert "PASEP" in prompt
        assert "4ª Turma" in prompt

    def test_prompt_contains_instructions(self):
        """Prompt deve conter instruções de análise."""
        processo = Processo(
            ordem=1,
            numero="001",
            ementa="TESTE"
        )

        prompt = build_analyst_prompt(processo)

        assert "BNP" in prompt or "precedentes" in prompt.lower()
        assert "JULIA" in prompt or "TRF5" in prompt
        assert "alerta" in prompt.lower()


class TestConsolidatorPrompt:
    """Testes do prompt do agente consolidador."""

    def test_prompt_contains_analyses(self):
        """Prompt deve conter análises para consolidar."""
        analises = [
            AnaliseProcesso(
                processo_numero="001",
                tema_central="Tema teste",
                alerta=NivelAlerta.VERMELHO,
                motivo_alerta="Divergência",
                recomendacao="Revisar"
            )
        ]

        prompt = build_consolidator_prompt(
            analises=analises,
            metadata={"turma": "4ª Turma", "sessao": "09/12/2025"}
        )

        assert "001" in prompt
        assert "vermelho" in prompt.lower() or "VERMELHO" in prompt
```

**Step 2: Rodar teste para verificar que falha**

Run: `pytest tests/test_prompts.py -v`
Expected: FAIL

**Step 3: Implementar prompts**

`src/lista_trf/prompts.py`:
```python
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
      "alinhamento": "compativel|divergente|parcial",
      "observacao": "observação relevante se houver"
    }}
  ],
  "flags_sensibilidade": ["flag1", "flag2"],
  "complexidade_fatica": "baixa|media|alta",
  "recomendacao": "recomendação específica de ação",
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ATENÇÃO IMEDIATA (Y processos)

[Para cada processo VERMELHO, incluir:]

### N. Processo XXXXXXX-XX.XXXX.X.XX.XXXX
**Tema**: [tema central]
**Alerta**: [motivo do alerta]
**Situação**: [explicação detalhada]
**Precedentes**: [lista dos precedentes relevantes]
**Recomendação**: [recomendação específica]

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ANÁLISE RECOMENDADA (Z processos)

[Para cada processo AMARELO, mesmo formato]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
        Prompt para responder à pergunta
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
```

**Step 4: Rodar testes**

Run: `pytest tests/test_prompts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/lista_trf/prompts.py tests/test_prompts.py
git commit -m "feat: templates de prompts para agentes"
```

---

## Task 5: Gerador de Relatório Markdown

**Files:**
- Create: `src/lista_trf/report.py`
- Create: `tests/test_report.py`

**Step 1: Criar teste do gerador de relatório**

`tests/test_report.py`:
```python
"""Testes para o gerador de relatório."""

import pytest
from lista_trf.report import generate_markdown_report
from lista_trf.schemas import (
    AnaliseProcesso,
    RelatorioConsolidado,
    NivelAlerta,
    PrecedenteEncontrado
)


class TestGenerateReport:
    """Testes de geração de relatório."""

    def test_report_has_header(self):
        """Relatório deve ter cabeçalho correto."""
        relatorio = RelatorioConsolidado(
            sessao="09/12/2025",
            turma="4ª Turma",
            gabinete="Des. Fernando Braga",
            total_processos=2,
            analises=[]
        )

        md = generate_markdown_report(relatorio)

        assert "09/12/2025" in md
        assert "4ª Turma" in md

    def test_report_has_sections(self):
        """Relatório deve ter seções por nível de alerta."""
        analises = [
            AnaliseProcesso(
                processo_numero="001",
                processo_ordem=1,
                tema_central="Tema vermelho",
                alerta=NivelAlerta.VERMELHO,
                motivo_alerta="Divergência",
                recomendacao="Revisar"
            ),
            AnaliseProcesso(
                processo_numero="002",
                processo_ordem=2,
                tema_central="Tema verde",
                alerta=NivelAlerta.VERDE,
                motivo_alerta="OK",
                recomendacao="Nenhuma"
            ),
        ]

        relatorio = RelatorioConsolidado(
            sessao="09/12/2025",
            turma="4ª Turma",
            total_processos=2,
            analises=analises
        )

        md = generate_markdown_report(relatorio)

        assert "ATENÇÃO IMEDIATA" in md
        assert "SEM ALERTAS" in md

    def test_report_counts_correct(self):
        """Relatório deve mostrar contagens corretas."""
        analises = [
            AnaliseProcesso(
                processo_numero="001",
                tema_central="T1",
                alerta=NivelAlerta.VERMELHO,
                motivo_alerta="M1",
                recomendacao="R1"
            ),
            AnaliseProcesso(
                processo_numero="002",
                tema_central="T2",
                alerta=NivelAlerta.AMARELO,
                motivo_alerta="M2",
                recomendacao="R2"
            ),
            AnaliseProcesso(
                processo_numero="003",
                tema_central="T3",
                alerta=NivelAlerta.VERDE,
                motivo_alerta="M3",
                recomendacao="R3"
            ),
        ]

        relatorio = RelatorioConsolidado(
            sessao="09/12/2025",
            turma="4ª Turma",
            total_processos=3,
            analises=analises
        )

        md = generate_markdown_report(relatorio)

        assert "1 alertas vermelhos" in md or "1 alerta vermelho" in md
        assert "1 amarelo" in md
        assert "1 verde" in md
```

**Step 2: Rodar teste para verificar que falha**

Run: `pytest tests/test_report.py -v`
Expected: FAIL

**Step 3: Implementar gerador de relatório**

`src/lista_trf/report.py`:
```python
"""Gerador de relatório Markdown."""

from lista_trf.schemas import RelatorioConsolidado, AnaliseProcesso, NivelAlerta


def generate_markdown_report(relatorio: RelatorioConsolidado) -> str:
    """
    Gera relatório em formato Markdown.

    Args:
        relatorio: Relatório consolidado com análises

    Returns:
        String com relatório em Markdown
    """
    lines = []

    # Header
    lines.append("# Análise da Lista de Julgamento")
    lines.append(f"## Sessão: {relatorio.sessao} | {relatorio.turma} | {relatorio.gabinete}")

    # Contagens
    v = relatorio.total_vermelhos
    a = relatorio.total_amarelos
    g = relatorio.total_verdes

    vermelho_str = f"{v} alerta vermelho" if v == 1 else f"{v} alertas vermelhos"
    amarelo_str = f"{a} amarelo" if a == 1 else f"{a} amarelos"
    verde_str = f"{g} verde" if g == 1 else f"{g} verdes"

    lines.append(f"## Total: {relatorio.total_processos} processos | {vermelho_str} | {amarelo_str} | {verde_str}")
    lines.append("")
    lines.append("━" * 60)
    lines.append("")

    # Seção Vermelhos
    vermelhos = relatorio.vermelhos
    lines.append(f"## ATENÇÃO IMEDIATA ({len(vermelhos)} processos)")
    lines.append("")

    if vermelhos:
        for i, analise in enumerate(sorted(vermelhos, key=lambda x: x.processo_ordem), 1):
            lines.extend(_format_detailed_analysis(i, analise))
    else:
        lines.append("*Nenhum processo com alerta vermelho.*")
        lines.append("")

    lines.append("━" * 60)
    lines.append("")

    # Seção Amarelos
    amarelos = relatorio.amarelos
    lines.append(f"## ANÁLISE RECOMENDADA ({len(amarelos)} processos)")
    lines.append("")

    if amarelos:
        for i, analise in enumerate(sorted(amarelos, key=lambda x: x.processo_ordem), 1):
            lines.extend(_format_detailed_analysis(i, analise))
    else:
        lines.append("*Nenhum processo com alerta amarelo.*")
        lines.append("")

    lines.append("━" * 60)
    lines.append("")

    # Seção Verdes
    verdes = relatorio.verdes
    lines.append(f"## SEM ALERTAS ({len(verdes)} processos)")
    lines.append("")

    if verdes:
        lines.append("| # | Processo | Tema |")
        lines.append("|---|----------|------|")
        for analise in sorted(verdes, key=lambda x: x.processo_ordem):
            lines.append(f"| {analise.processo_ordem} | {analise.processo_numero} | {analise.tema_central} |")
    else:
        lines.append("*Nenhum processo sem alertas.*")

    lines.append("")

    # Falhas se houver
    if relatorio.falhas:
        lines.append("━" * 60)
        lines.append("")
        lines.append(f"## FALHAS DE ANÁLISE ({len(relatorio.falhas)} processos)")
        lines.append("")
        for falha in relatorio.falhas:
            lines.append(f"- **{falha.get('processo', 'N/A')}**: {falha.get('motivo', 'Erro desconhecido')}")
        lines.append("")

    return "\n".join(lines)


def _format_detailed_analysis(index: int, analise: AnaliseProcesso) -> list[str]:
    """Formata análise detalhada para processos vermelho/amarelo."""
    lines = []

    lines.append(f"### {index}. Processo {analise.processo_numero}")
    lines.append(f"**Tema**: {analise.tema_central}")
    lines.append(f"**Alerta**: {analise.motivo_alerta}")

    if analise.flags_sensibilidade:
        flags_str = ", ".join(analise.flags_sensibilidade)
        lines.append(f"**Flags**: {flags_str}")

    if analise.complexidade_fatica != "baixa":
        lines.append(f"**Complexidade Fática**: {analise.complexidade_fatica}")

    # Precedentes
    if analise.precedentes_relevantes:
        lines.append("**Precedentes**:")
        for p in analise.precedentes_relevantes:
            status = f" ({p.status})" if p.status != "vigente" else ""
            alinhamento_icon = {
                "compativel": "✓",
                "divergente": "✗",
                "parcial": "~"
            }.get(p.alinhamento, "?")
            lines.append(f"- {alinhamento_icon} {p.identificador}{status}: {p.tese[:100]}...")

    lines.append(f"**Recomendação**: {analise.recomendacao}")
    lines.append("")
    lines.append("---")
    lines.append("")

    return lines


def save_report(relatorio: RelatorioConsolidado, output_path: str) -> str:
    """
    Gera e salva relatório em arquivo.

    Args:
        relatorio: Relatório consolidado
        output_path: Caminho para salvar

    Returns:
        Caminho do arquivo salvo
    """
    from pathlib import Path

    md_content = generate_markdown_report(relatorio)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md_content, encoding="utf-8")

    return str(path)
```

**Step 4: Rodar testes**

Run: `pytest tests/test_report.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/lista_trf/report.py tests/test_report.py
git commit -m "feat: gerador de relatório Markdown"
```

---

## Task 6: Agente Analista (Core)

**Files:**
- Create: `src/lista_trf/agents/analyst.py`
- Create: `src/lista_trf/agents/__init__.py`

**Step 1: Criar estrutura de diretórios**

```bash
mkdir -p src/lista_trf/agents
```

**Step 2: Criar __init__.py**

`src/lista_trf/agents/__init__.py`:
```python
"""Agentes do sistema de análise."""

from lista_trf.agents.analyst import ANALYST_AGENT_PROMPT

__all__ = ["ANALYST_AGENT_PROMPT"]
```

**Step 3: Implementar prompt do agente analista**

`src/lista_trf/agents/analyst.py`:
```python
"""Agente Analista - analisa um processo individual."""

from lista_trf.schemas import Processo


def build_analyst_task_prompt(processo: Processo) -> str:
    """
    Constrói o prompt completo para o agente analista.

    Este prompt será usado com a ferramenta Task do Claude Code
    para lançar um subagente que analisa um único processo.

    Args:
        processo: Processo a ser analisado

    Returns:
        Prompt para o subagente
    """
    turma = processo.metadata.get("turma", "Não informada")

    return f'''Analise o processo jurídico abaixo e verifique compatibilidade com jurisprudência.

## PROCESSO

- **Número**: {processo.numero}
- **Ordem na lista**: {processo.ordem}
- **Tipo**: {processo.tipo_acao or "Não informado"}
- **Turma**: {turma}
- **Partes**: {processo.partes or "Não informadas"}

**EMENTA COMPLETA**:
```
{processo.ementa}
```

## INSTRUÇÕES

### 1. CLASSIFICAÇÃO (analise a ementa)

Identifique:
- Tema jurídico central (ex: "prescrição PASEP", "aposentadoria especial")
- Tipo de questão (processual, mérito, preliminar)
- Flags de sensibilidade: improbidade, ambiental, minorias, comunidades tradicionais, ACP
- Complexidade fática (baixa/média/alta)

### 2. PESQUISA DE PRECEDENTES

Execute pesquisas nas três bases usando as ferramentas MCP:

**A) BNP - Banco Nacional de Precedentes**
```
Use: mcp__bnp-api__buscar_precedentes
- Formule query com termos técnicos do tema
- Busque Temas STF (Repercussão Geral) e STJ (Repetitivos)
- Busque Súmulas Vinculantes relacionadas
```

**B) JULIA - Jurisprudência TRF5**
```
Use: mcp__julia-trf5__buscar_julia
- Pesquise jurisprudência do TRF5
- FILTRE por orgao_julgador="{turma}" para precedentes da própria turma
- Pesquise também sem filtro para ver outras turmas
```

**C) CJF - Base Unificada (se necessário)**
```
Use: mcp__cjf-jurisprudencia__buscar_jurisprudencia_cjf
- Para comparar posições entre tribunais
- Para temas não encontrados nas outras bases
```

### 3. ANÁLISE COMPARATIVA

Compare a posição da ementa com precedentes encontrados:

**VERMELHO** (Atenção Imediata):
- Divergência com precedente vinculante vigente
- Contradição com Súmula Vinculante
- Contrário à jurisprudência pacífica da própria turma

**AMARELO** (Análise Recomendada):
- Tema sensível (improbidade, ambiental, minorias)
- Jurisprudência em evolução
- Divergência entre turmas
- Questão inédita
- Alta complexidade fática

**VERDE** (Sem Alertas):
- Alinhado com jurisprudência consolidada
- Tema pacificado
- Caso padrão

### 4. RESPOSTA

Retorne APENAS um JSON válido:

```json
{{
  "processo_numero": "{processo.numero}",
  "processo_ordem": {processo.ordem},
  "tema_central": "tema em poucas palavras",
  "alerta": "vermelho|amarelo|verde",
  "motivo_alerta": "explicação concisa",
  "precedentes_relevantes": [
    {{
      "identificador": "Tema XXX/STJ",
      "fonte": "BNP|JULIA|CJF",
      "tese": "resumo da tese",
      "status": "vigente|superado|pendente",
      "alinhamento": "compativel|divergente|parcial",
      "observacao": "se houver"
    }}
  ],
  "flags_sensibilidade": ["lista", "de", "flags"],
  "complexidade_fatica": "baixa|media|alta",
  "recomendacao": "recomendação de ação",
  "analise_completa": "análise detalhada para referência"
}}
```

IMPORTANTE:
- Faça as pesquisas ANTES de determinar o alerta
- Retorne APENAS o JSON, sem texto antes ou depois
- Se não encontrar precedentes, indique como tema inédito (amarelo)
'''


# Prompt base para referência
ANALYST_AGENT_PROMPT = '''Você é um agente analista jurídico especializado.
Sua função é analisar processos e verificar compatibilidade com jurisprudência.
Use as ferramentas MCP disponíveis para pesquisar precedentes.'''
```

**Step 4: Commit**

```bash
git add src/lista_trf/agents/
git commit -m "feat: agente analista com prompt para subagent"
```

---

## Task 7: Agente Orquestrador

**Files:**
- Create: `src/lista_trf/agents/orchestrator.py`
- Modify: `src/lista_trf/agents/__init__.py`

**Step 1: Implementar orquestrador**

`src/lista_trf/agents/orchestrator.py`:
```python
"""Agente Orquestrador - coordena o fluxo de análise."""

from pathlib import Path
from lista_trf.schemas import Processo, AnaliseProcesso, RelatorioConsolidado
from lista_trf.extractor import extract_processes_from_docx, ProcessoExtraido
from lista_trf.agents.analyst import build_analyst_task_prompt


def build_orchestrator_prompt(file_path: str) -> str:
    """
    Constrói o prompt principal do orquestrador.

    Este é o prompt que guia todo o fluxo de análise.

    Args:
        file_path: Caminho do documento a analisar

    Returns:
        Prompt completo para o orquestrador
    """
    return f'''Você é o Agente Orquestrador do sistema de análise de listas de julgamento do TRF5.

## SUA MISSÃO

Coordenar a análise completa da lista de julgamento, gerando um relatório que destaque:
1. Processos com incompatibilidades jurisprudenciais (VERMELHO)
2. Processos que merecem análise especial (AMARELO)
3. Processos sem alertas (VERDE)

## DOCUMENTO A ANALISAR

Caminho: {file_path}

## FLUXO DE EXECUÇÃO

### FASE 1: EXTRAÇÃO

1. Use Python para ler o documento Word e extrair os processos
2. Para cada processo, extraia: número, tipo de ação, partes, ementa completa
3. Extraia também os metadados: turma, sessão, gabinete

Código para extração:
```python
from lista_trf.extractor import extract_processes_from_docx
from pathlib import Path

processos = extract_processes_from_docx(Path(r"{file_path}"))
print(f"Extraídos {{len(processos)}} processos")
```

### FASE 2: ANÁLISE PARALELA

Para cada processo extraído, lance um subagente analista usando a ferramenta Task:

```
Task tool com:
- subagent_type: "general-purpose"
- description: "Analisar processo [NÚMERO]"
- prompt: [prompt do analista com dados do processo]
- run_in_background: true (para paralelizar)
```

IMPORTANTE:
- Lance em lotes de 5-10 agentes para não sobrecarregar
- Use run_in_background=true para paralelizar
- Depois use TaskOutput para coletar resultados

### FASE 3: COLETA DE RESULTADOS

1. Aguarde todos os agentes terminarem
2. Colete os JSONs de análise de cada um
3. Trate falhas (marcar como "análise falhou")

### FASE 4: CONSOLIDAÇÃO

1. Agrupe análises por nível de alerta
2. Gere o relatório Markdown usando:

```python
from lista_trf.schemas import AnaliseProcesso, RelatorioConsolidado, NivelAlerta
from lista_trf.report import generate_markdown_report, save_report

# Criar objetos AnaliseProcesso a partir dos JSONs coletados
analises = [...]

# Criar relatório
relatorio = RelatorioConsolidado(
    sessao="DATA",
    turma="TURMA",
    gabinete="GABINETE",
    total_processos=len(analises),
    analises=analises
)

# Gerar e salvar
md = generate_markdown_report(relatorio)
save_report(relatorio, "output/YYYY-MM-DD-sessao.md")
```

### FASE 5: MODO CONVERSA

Após gerar o relatório:
1. Exiba o relatório para o usuário
2. Informe que está em modo conversa
3. Responda perguntas sobre processos específicos
4. Execute novas pesquisas se solicitado

## FORMATO DO RELATÓRIO

O relatório deve seguir este formato:

```markdown
# Análise da Lista de Julgamento
## Sessão: [DATA] | [TURMA] | [GABINETE]
## Total: X processos | Y alertas vermelhos | Z amarelos | W verdes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ATENÇÃO IMEDIATA (Y processos)

### 1. Processo XXXXXXX-XX.XXXX.X.XX.XXXX
**Tema**: [tema]
**Alerta**: [motivo]
**Precedentes**: [lista]
**Recomendação**: [recomendação]

---

## ANÁLISE RECOMENDADA (Z processos)
[mesmo formato]

## SEM ALERTAS (W processos)
| # | Processo | Tema |
|---|----------|------|
...
```

## COMECE AGORA

Inicie a Fase 1: extraia os processos do documento.
'''


def convert_extracted_to_processo(extracted: ProcessoExtraido) -> Processo:
    """Converte ProcessoExtraido para Processo (Pydantic)."""
    from lista_trf.schemas import Processo

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
    Constrói prompt para análise em lote.

    Args:
        processos: Lista de processos a analisar
        batch_size: Tamanho de cada lote

    Returns:
        Instruções para lançar análises em lote
    """
    total = len(processos)
    num_batches = (total + batch_size - 1) // batch_size

    batches_info = []
    for i in range(num_batches):
        start = i * batch_size
        end = min(start + batch_size, total)
        batch_processos = processos[start:end]
        nums = [p.numero for p in batch_processos]
        batches_info.append(f"Lote {i+1}: processos {start+1}-{end} ({', '.join(nums[:3])}...)")

    return f'''## ANÁLISE EM LOTES

Total de processos: {total}
Tamanho do lote: {batch_size}
Número de lotes: {num_batches}

Lotes:
{chr(10).join(batches_info)}

Para cada processo, use a ferramenta Task com:
- subagent_type: "general-purpose"
- run_in_background: true
- prompt: [prompt do analista específico para o processo]

Lance um lote, aguarde conclusão, lance o próximo.
'''
```

**Step 2: Atualizar __init__.py**

`src/lista_trf/agents/__init__.py`:
```python
"""Agentes do sistema de análise."""

from lista_trf.agents.analyst import ANALYST_AGENT_PROMPT, build_analyst_task_prompt
from lista_trf.agents.orchestrator import (
    build_orchestrator_prompt,
    convert_extracted_to_processo,
    build_batch_analysis_prompt
)

__all__ = [
    "ANALYST_AGENT_PROMPT",
    "build_analyst_task_prompt",
    "build_orchestrator_prompt",
    "convert_extracted_to_processo",
    "build_batch_analysis_prompt"
]
```

**Step 3: Commit**

```bash
git add src/lista_trf/agents/
git commit -m "feat: agente orquestrador com coordenação de lotes"
```

---

## Task 8: Script Principal (CLI)

**Files:**
- Create: `src/lista_trf/main.py`
- Create: `analyze_list.py` (entry point)

**Step 1: Criar módulo principal**

`src/lista_trf/main.py`:
```python
"""Módulo principal - ponto de entrada do sistema."""

from pathlib import Path
from lista_trf.extractor import extract_processes_from_docx
from lista_trf.agents.orchestrator import convert_extracted_to_processo
from lista_trf.agents.analyst import build_analyst_task_prompt


def prepare_analysis(file_path: str) -> dict:
    """
    Prepara análise extraindo processos do documento.

    Args:
        file_path: Caminho do documento Word

    Returns:
        Dicionário com dados preparados para análise
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    if not path.suffix.lower() == '.docx':
        raise ValueError(f"Formato não suportado: {path.suffix}. Use .docx")

    # Extrair processos
    extracted = extract_processes_from_docx(path)

    # Converter para schema Pydantic
    processos = [convert_extracted_to_processo(e) for e in extracted]

    # Extrair metadados
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
    Gera prompts para todos os processos.

    Args:
        processos: Lista de Processo

    Returns:
        Lista de dicts com número e prompt
    """
    prompts = []
    for p in processos:
        prompts.append({
            "numero": p.numero,
            "ordem": p.ordem,
            "prompt": build_analyst_task_prompt(p)
        })
    return prompts


# Prompt master para iniciar análise no Claude Code
MASTER_PROMPT = '''## Sistema de Análise de Listas de Julgamento - TRF5

Para analisar uma lista de julgamento, execute:

```python
from lista_trf.main import prepare_analysis, generate_analyst_prompts

# 1. Preparar análise
data = prepare_analysis(r"CAMINHO_DO_ARQUIVO.docx")
print(f"Processos encontrados: {data['total_processos']}")
print(f"Turma: {data['metadata'].get('turma')}")
print(f"Sessão: {data['metadata'].get('sessao')}")

# 2. Gerar prompts dos analistas
prompts = generate_analyst_prompts(data['processos'])
```

Depois, para cada processo, lance um subagente com a ferramenta Task:
- Use subagent_type="general-purpose"
- Use run_in_background=true para paralelizar
- Colete resultados com TaskOutput

Após coletar todas as análises, gere o relatório:

```python
from lista_trf.report import generate_markdown_report, save_report
from lista_trf.schemas import RelatorioConsolidado, AnaliseProcesso, NivelAlerta

# Montar relatório (analises = lista de AnaliseProcesso)
relatorio = RelatorioConsolidado(
    sessao=data['metadata'].get('sessao', ''),
    turma=data['metadata'].get('turma', ''),
    gabinete=data['metadata'].get('gabinete', ''),
    total_processos=len(analises),
    analises=analises
)

# Salvar
output_path = save_report(relatorio, "output/relatorio.md")
print(f"Relatório salvo em: {output_path}")
```
'''
```

**Step 2: Criar script de entrada**

`analyze_list.py`:
```python
#!/usr/bin/env python3
"""
Script de entrada para análise de listas de julgamento.

Uso:
    python analyze_list.py "caminho/para/lista.docx"

Ou no Claude Code:
    claude "analisa lista: caminho/para/lista.docx"
"""

import sys
from pathlib import Path


def main():
    """Ponto de entrada principal."""
    if len(sys.argv) < 2:
        print("Uso: python analyze_list.py <caminho_do_arquivo.docx>")
        print("\nOu no Claude Code:")
        print('  claude "analisa lista: caminho/para/lista.docx"')
        sys.exit(1)

    file_path = sys.argv[1]

    # Importar após verificar argumentos (mais rápido se erro)
    from lista_trf.main import prepare_analysis, MASTER_PROMPT

    try:
        data = prepare_analysis(file_path)

        print(f"\n{'='*60}")
        print("LISTA DE JULGAMENTO CARREGADA")
        print(f"{'='*60}")
        print(f"Arquivo: {data['file_path']}")
        print(f"Processos: {data['total_processos']}")
        print(f"Turma: {data['metadata'].get('turma', 'N/A')}")
        print(f"Sessão: {data['metadata'].get('sessao', 'N/A')}")
        print(f"Gabinete: {data['metadata'].get('gabinete', 'N/A')}")
        print(f"{'='*60}\n")

        print("Para continuar a análise no Claude Code, execute:")
        print(f'\n  claude "analisa a lista em: {file_path}"\n')

    except FileNotFoundError as e:
        print(f"Erro: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Erro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 3: Testar script**

Run: `python analyze_list.py "C:\Users\georg\lista-trf\Lista de Julgamento - GABFBD - Sessão 09.12.2025 - 4ª Turma.docx"`
Expected: Exibir informações da lista carregada

**Step 4: Commit**

```bash
git add src/lista_trf/main.py analyze_list.py
git commit -m "feat: script principal e CLI de entrada"
```

---

## Task 9: Instruções para Claude Code

**Files:**
- Create: `CLAUDE.md` (instruções do projeto)

**Step 1: Criar CLAUDE.md com instruções**

`CLAUDE.md`:
```markdown
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
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: instruções do projeto para Claude Code"
```

---

## Task 10: Teste de Integração

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Criar teste de integração**

`tests/test_integration.py`:
```python
"""Testes de integração do sistema."""

import pytest
from pathlib import Path

from lista_trf.main import prepare_analysis, generate_analyst_prompts
from lista_trf.schemas import AnaliseProcesso, RelatorioConsolidado, NivelAlerta
from lista_trf.report import generate_markdown_report


SAMPLE_DOC = Path(r"C:\Users\georg\lista-trf\Lista de Julgamento - GABFBD - Sessão 09.12.2025 - 4ª Turma.docx")


class TestIntegration:
    """Testes de integração end-to-end."""

    def test_full_extraction_flow(self):
        """Fluxo completo de extração funciona."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        # Preparar
        data = prepare_analysis(str(SAMPLE_DOC))

        # Verificar
        assert data['total_processos'] > 0
        assert len(data['processos']) > 0
        assert 'turma' in data['metadata']

    def test_generate_prompts_for_all(self):
        """Gera prompts para todos os processos."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        data = prepare_analysis(str(SAMPLE_DOC))
        prompts = generate_analyst_prompts(data['processos'])

        assert len(prompts) == data['total_processos']
        assert all('prompt' in p for p in prompts)
        assert all('numero' in p for p in prompts)

    def test_report_generation_with_mock_analyses(self):
        """Geração de relatório com análises mock."""
        # Criar análises mock
        analises = [
            AnaliseProcesso(
                processo_numero="0800307-06.2025.4.05.8103",
                processo_ordem=1,
                tema_central="Prescrição PASEP",
                alerta=NivelAlerta.VERDE,
                motivo_alerta="Alinhado com Tema 1150/STJ",
                recomendacao="Sem necessidade de revisão"
            ),
            AnaliseProcesso(
                processo_numero="0007508-25.2015.4.05.8300",
                processo_ordem=2,
                tema_central="Honorários em embargos",
                alerta=NivelAlerta.AMARELO,
                motivo_alerta="Tema com divergência entre turmas",
                flags_sensibilidade=["divergência interna"],
                recomendacao="Verificar posição da turma"
            ),
            AnaliseProcesso(
                processo_numero="0803133-36.2024.4.05.8201",
                processo_ordem=3,
                tema_central="Licença-prêmio",
                alerta=NivelAlerta.VERMELHO,
                motivo_alerta="Diverge do Tema 1086/STJ na base de cálculo",
                recomendacao="Revisar fundamentação"
            ),
        ]

        # Criar relatório
        relatorio = RelatorioConsolidado(
            sessao="09/12/2025",
            turma="4ª Turma",
            gabinete="Des. Fernando Braga",
            total_processos=3,
            analises=analises
        )

        # Gerar markdown
        md = generate_markdown_report(relatorio)

        # Verificar estrutura
        assert "09/12/2025" in md
        assert "4ª Turma" in md
        assert "ATENÇÃO IMEDIATA" in md
        assert "0803133-36.2024.4.05.8201" in md  # Vermelho
        assert "ANÁLISE RECOMENDADA" in md
        assert "0007508-25.2015.4.05.8300" in md  # Amarelo
        assert "SEM ALERTAS" in md
        assert "Prescrição PASEP" in md  # Verde na tabela

    def test_report_counts_are_correct(self):
        """Contagens do relatório estão corretas."""
        analises = [
            AnaliseProcesso(
                processo_numero=f"00{i}",
                tema_central=f"Tema {i}",
                alerta=NivelAlerta.VERMELHO if i < 2 else (NivelAlerta.AMARELO if i < 5 else NivelAlerta.VERDE),
                motivo_alerta="Motivo",
                recomendacao="Rec"
            )
            for i in range(10)
        ]

        relatorio = RelatorioConsolidado(
            sessao="01/01/2026",
            turma="1ª Turma",
            total_processos=10,
            analises=analises
        )

        assert relatorio.total_vermelhos == 2
        assert relatorio.total_amarelos == 3
        assert relatorio.total_verdes == 5
```

**Step 2: Rodar testes de integração**

Run: `pytest tests/test_integration.py -v`
Expected: PASS

**Step 3: Rodar todos os testes**

Run: `pytest tests/ -v`
Expected: Todos os testes passam

**Step 4: Commit final**

```bash
git add tests/test_integration.py
git commit -m "test: testes de integração do sistema"
```

---

## Resumo dos Commits

| # | Commit | Descrição |
|---|--------|-----------|
| 1 | `chore: setup inicial` | Estrutura do projeto |
| 2 | `feat: extrator` | Leitura de documentos Word |
| 3 | `feat: schemas` | Modelos Pydantic |
| 4 | `feat: prompts` | Templates de prompts |
| 5 | `feat: report` | Gerador de relatório |
| 6 | `feat: analyst` | Agente analista |
| 7 | `feat: orchestrator` | Orquestrador |
| 8 | `feat: main/CLI` | Script principal |
| 9 | `docs: CLAUDE.md` | Instruções |
| 10 | `test: integração` | Testes E2E |

---

## Verificação Final

Após completar todas as tarefas:

```bash
# Rodar todos os testes
pytest tests/ -v

# Testar extração
python analyze_list.py "C:\Users\georg\lista-trf\Lista de Julgamento - GABFBD - Sessão 09.12.2025 - 4ª Turma.docx"

# Verificar estrutura
tree src/
```

O sistema está pronto para uso no Claude Code.
