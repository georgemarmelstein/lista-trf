"""
Configuracoes do sistema Lista TRF.
"""
from pathlib import Path

# Caminho base do projeto
PROJECT_ROOT = Path(__file__).parent.parent

# Caminho base onde estao as pastas de processos
BASE_PATH = PROJECT_ROOT / "processos"

# Pasta para listas importadas
LISTAS_PATH = PROJECT_ROOT / "listas"

# Pasta para processos arquivados
ARQUIVADOS_PATH = PROJECT_ROOT / "arquivados"

# Estados do fluxo (nome da pasta)
ESTADOS = {
    "a-analisar": "01-a-analisar",
    "de-acordo": "02-de-acordo",
    "destacar": "03-destacar",
}

# Ordem dos estados para exibicao
ORDEM_ESTADOS = ["a-analisar", "de-acordo", "destacar"]

# Sufixos dos arquivos exibidos no preview
ARQUIVOS_PREVIEW = ["ementa.md", "analise.md"]

# Titulos das colunas para exibicao
TITULOS_COLUNAS = {
    "a-analisar": "A Analisar",
    "de-acordo": "De Acordo",
    "destacar": "Destacar",
}
